# 100_process_maxar.py
#
# Sample Usage:
# python 100_process_maxar.py \
#    --input "/data/gis/raster_base/Alaska/AKVegMap/EVWHS/navy_north_slope/unzipped/050300601010_01" \
#    --output "/data/gis/raster_base/Alaska/AKVegMap/EVWHS/navy_north_slope/processed_output" \
#    --dem "/data/gis/gis_base/DEM/ifsar/alaska_ifsar_dsm_20200925.tif" \
#    --keep-temp \
#    --epsg 3338

import os
import glob
import logging
import subprocess
import argparse
import re
import shlex
import datetime
import math
import traceback
import shutil
import json

# --- CONFIGURATION ---
GEOID_PATH = "/opt/otb/OTB-9.1.1-Linux/share/otb/geoid/egm96.grd" 
RAM_MB = 64000
THREADS = 16

# CALIBRATION & MASKING SETTINGS
DO_TOA = True           

# Get the directory where the current script is located.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ENVIRONMENTS & PATHS
OMNIMASK_ENV_NAME = "omni" 
OMNIMASK_SCRIPT = os.path.join(SCRIPT_DIR, "110_process_maxar_omni.py")
OMNIMASK_MODEL = os.path.join(SCRIPT_DIR, "models", "omnimask_weights.pt")

# SCALING
REFLECTANCE_SCALE = 10000 
OUTPUT_PIXEL_TYPE = "uint16" 

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_primary_file(folder_path):
    """
    Finds the primary metadata file (.XML or .IMD) in a Maxar folder.
    OTB uses this to automatically discover sensor info and image data.
    """
    # Prioritize the XML file as it's the modern standard for Maxar metadata
    xml_files = glob.glob(os.path.join(folder_path, "*.XML"))
    if xml_files:
        return xml_files[0]
    # Fallback to IMD for older products
    imd_files = glob.glob(os.path.join(folder_path, "*.IMD"))
    if imd_files:
        return imd_files[0]
    # Last resort: return the NTF file, though calibration may fail
    return get_image_file(folder_path)

def get_image_file(folder_path):
    """Finds only the .NTF image file in a Maxar folder."""
    ntf_files = glob.glob(os.path.join(folder_path, "*.NTF"))
    return ntf_files[0] if ntf_files else None

def calculate_earth_sun_distance(year, month, day):
    """
    Calculates the Earth-Sun distance in AU for a given date.
    This is an approximation but sufficient for radiometric correction.
    Source: https://physics.stackexchange.com/questions/177949/earth-sun-distance-on-a-given-day-of-the-year
    """
    doy = datetime.date(year, month, day).timetuple().tm_yday
    # The argument of cos is in radians. The formula uses day number (doy).
    # d = 1 - 0.01672 * cos( (2*pi/365.25) * (doy - 4) )
    # 2*pi/365.25 is approx 0.017202
    distance_au = 1 - 0.01672 * math.cos(0.017202 * (doy - 4))
    logging.info(f"Calculated Earth-Sun distance for {year}-{month}-{day} (DOY {doy}): {distance_au:.5f} AU")
    return distance_au

def parse_wv3_metadata(xml_path, band_keys=None):
    """
    Parses a WorldView-3 XML metadata file to extract calibration parameters
    required by OTB's OpticalCalibration application. This version uses a
    robust, pure-Python regex approach to handle XML variations (like
    namespaces) and avoid environment-specific library issues.
    """
    logging.info(f"Parsing metadata from {os.path.basename(xml_path)} using robust regex")

    with open(xml_path, 'r', encoding='utf-8-sig') as f:
        xml_content = f.read()

    if not xml_content:
        raise ValueError(f"XML file is empty or could not be read: {xml_path}")

    def get_value(tag, content):
        """Uses a robust regex to find a tag and extract its value."""
        # This pattern handles case-insensitivity, optional namespace prefixes (e.g., <ps:tag>),
        # attributes within the opening tag, and multi-line values.
        pattern = re.compile(rf'<(?:\w+:)?{tag}[^>]*>(.*?)</(?:\w+:)?{tag}>', re.IGNORECASE | re.DOTALL)
        match = pattern.search(content)
        if match:
            return match.group(1).strip()
        return None
    
    # Find general acquisition info
    sun_elev_text = get_value('meanSunEl', xml_content)
    solar_dist_text = get_value('earthSunDist', xml_content)
    acq_time_text = get_value('firstLineTime', xml_content)
    sat_id_text = get_value('satId', xml_content)
    catalog_id_text = get_value('CATID', xml_content)
    
    # Extract reference coordinates for UTM zone calculation
    ul_lon = get_value('ULLON', xml_content)
    ul_lat = get_value('ULLAT', xml_content)
    if ul_lon and ul_lat:
        ref_lon = float(ul_lon)
        ref_lat = float(ul_lat)
    else:
        ref_lon, ref_lat = None, None
    
    # Check for absolutely essential tags
    if any(val is None for val in [sun_elev_text, acq_time_text]):
        raise ValueError(f"Could not find one or more essential metadata tags (e.g., meanSunEl, firstLineTime) in {xml_path}")
    
    # Parse date and time from "YYYY-MM-DDTHH:MM:SS.ssssssZ" format
    date_part, time_part = acq_time_text.split('T')
    year, month, day = map(int, date_part.split('-'))
    time_parts = time_part.replace('Z', '').split(':')
    hour = int(float(time_parts[0]))
    minute = int(float(time_parts[1]))

    # If solar distance wasn't in the XML, calculate it from the date.
    if solar_dist_text is None:
        logging.warning("'earthSunDist' tag not found in XML. Calculating from date.")
        solar_distance = calculate_earth_sun_distance(year, month, day)
    else:
        solar_distance = float(solar_dist_text)

    # Define the expected band order for WorldView-3
    if band_keys is None:
        band_keys = ['BAND_C', 'BAND_B', 'BAND_G', 'BAND_Y', 'BAND_R', 'BAND_RE', 'BAND_N', 'BAND_N2']
    
    gains_and_biases = []
    solar_irradiances = []

    for band_key in band_keys:
        # Handle alternate naming for NIR1 (BAND_N vs BAND_N1)
        current_band_key = band_key
        # Check for band key existence case-insensitively
        if band_key.lower() == 'band_n' and not re.search(rf'<{band_key}>', xml_content, re.IGNORECASE):
            current_band_key = 'BAND_N1'

        # Use regex to find the band block and then the values within it.
        band_block = get_value(current_band_key, xml_content)
        if band_block is None:
            raise ValueError(f"Could not find metadata block for {band_key} (or {current_band_key}) in {xml_path}")

        # Get absCalFactor, which is mandatory
        abs_cal_factor_str = get_value('absCalFactor', band_block)
        if not abs_cal_factor_str:
            raise ValueError(f"Missing required 'absCalFactor' tag for {current_band_key} in {xml_path}")
        abs_cal_factor = float(abs_cal_factor_str)

        # Get solarIrradiance, but fall back to standard values if missing
        solar_irradiance_str = get_value('solarIrradiance', band_block)
        if solar_irradiance_str:
            solar_irradiance = float(solar_irradiance_str)
        else:
            logging.warning(f"'solarIrradiance' tag not found for {current_band_key}. Using standard value.")
            # Standard WV-3 top-of-atmosphere solar irradiance values (W/m^2/μm)
            # Source: DigitalGlobe Radiometric Use of WorldView-3 Imagery
            wv3_solar_irradiance = {
                'BAND_P': 1580.8140,
                'BAND_C': 1758.2229,
                'BAND_B': 1971.8116,
                'BAND_G': 1856.4104,
                'BAND_Y': 1738.4791,
                'BAND_R': 1559.4555,
                'BAND_RE': 1342.0695,
                'BAND_N': 1069.7302,   # NIR1
                'BAND_N1': 1069.7302,  # Alias for NIR1
                'BAND_N2': 861.2866    # NIR2
            }
            if current_band_key not in wv3_solar_irradiance:
                raise ValueError(f"Cannot find standard solar irradiance for unknown band '{current_band_key}'")
            solar_irradiance = wv3_solar_irradiance[current_band_key]
        
        # For Maxar data, gain is the absCalFactor and bias is 0
        gains_and_biases.extend([abs_cal_factor, 0.0])
        solar_irradiances.append(solar_irradiance)

    # Extract only the gains, as biases are zero for this data
    gains = [val for i, val in enumerate(gains_and_biases) if i % 2 == 0]

    return {
        "sun_elevation": float(sun_elev_text),
        "solar_distance": solar_distance,
        "gains": gains,
        "solar_irradiances": solar_irradiances,
        "acq_time": acq_time_text,
        "sensor": sat_id_text,
        "catalog_id": catalog_id_text,
        "ref_lon": ref_lon,
        "ref_lat": ref_lat
    }

def get_reference_coords(meta_path):
    """
    Parses metadata (XML or IMD) to find Upper Left Longitude/Latitude.
    Returns (lon, lat) or (None, None).
    """
    if not meta_path or not os.path.exists(meta_path):
        return None, None
    
    try:
        with open(meta_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            content = f.read()
        
        def find_val(patterns):
            for pat in patterns:
                m = re.search(pat, content, re.IGNORECASE | re.DOTALL)
                if m: return float(m.group(1))
            return None

        # Longitude patterns
        lon = find_val([
            r'<(?:\w+:)?(?:ULLON|UpperLeftLongitude)[^>]*>(.*?)</(?:\w+:)?(?:ULLON|UpperLeftLongitude)>', # XML
            r'(?:ULLon|upperLeftLongitude)\s*=\s*([\d\.\-]+)' # IMD
        ])
        
        # Latitude patterns
        lat = find_val([
            r'<(?:\w+:)?(?:ULLAT|UpperLeftLatitude)[^>]*>(.*?)</(?:\w+:)?(?:ULLAT|UpperLeftLatitude)>', # XML
            r'(?:ULLat|upperLeftLatitude)\s*=\s*([\d\.\-]+)' # IMD
        ])
        
        if lon is not None and lat is not None:
            return lon, lat
            
    except Exception as e:
        logging.warning(f"Failed to parse coords from {meta_path}: {e}")
        
    return None, None

def get_average_gsd(meta_path):
    """
    Parses the metadata file (XML or IMD) to find the mean Ground Sample Distance (GSD).
    Returns the average of Row and Column GSD in meters.
    """
    if not meta_path or not os.path.exists(meta_path):
        return None
    
    try:
        with open(meta_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            content = f.read()
        
        # Helper to find float value by regex
        def find_val(pattern):
            m = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            return float(m.group(1)) if m else None

        # Try XML tags (e.g., <MEANROWGSD>0.31</MEANROWGSD> or <ROWGSD>0.31</ROWGSD>)
        row_gsd = find_val(r'<(?:\w+:)?(?:MEAN)?ROWGSD[^>]*>(.*?)</(?:\w+:)?(?:MEAN)?ROWGSD>')
        col_gsd = find_val(r'<(?:\w+:)?(?:MEAN)?COLGSD[^>]*>(.*?)</(?:\w+:)?(?:MEAN)?COLGSD>')
        
        if row_gsd and col_gsd:
            return (row_gsd + col_gsd) / 2.0
            
        # Try IMD keys (e.g., meanProductGSD = 0.31 or meanRowGSD = 0.31)
        row_gsd = find_val(r'(?:mean)?RowGSD\s*=\s*([\d\.]+(?:e[+-]?\d+)?)')
        col_gsd = find_val(r'(?:mean)?ColGSD\s*=\s*([\d\.]+(?:e[+-]?\d+)?)')
        
        if row_gsd and col_gsd:
            return (row_gsd + col_gsd) / 2.0
            
    except Exception as e:
        logging.warning(f"Failed to parse GSD from {meta_path}: {e}")
        
    return None

def run_omnimask(image_path, output_dir, prefix):
    """Executes omnimask as a subprocess using 'conda run'."""
    if not os.path.exists(OMNIMASK_SCRIPT):
        logging.error(f"Omnimask script not found: {OMNIMASK_SCRIPT}")
        return
    
    mask_path = os.path.join(output_dir, f"{prefix}_mask.tif")
    logging.info(f"Running omnimask on {prefix} using env '{OMNIMASK_ENV_NAME}'...")
    
    try:
        cmd = [
            "conda", "run", "-n", OMNIMASK_ENV_NAME, "--no-capture-output",
            "python", OMNIMASK_SCRIPT, 
            "--input", image_path, 
            "--output", mask_path,
            "--model", OMNIMASK_MODEL
        ]
        subprocess.run(cmd, check=True)
        logging.info(f"Mask created successfully: {mask_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Omnimask failed for {prefix} with exit code {e.returncode}")
    except FileNotFoundError:
        logging.error("Conda command not found. Ensure conda is in your PATH.")

def process_bundle(input_dir, dem_path, output_dir, ram, enable_masking, keep_temp, threads, target_epsg=None):
    """Orchestrates the processing of a Maxar bundle."""
    import pyotb

    # --- Pre-flight Checks ---
    if not os.path.isdir(input_dir):
        logging.error(f"Input directory not found: {input_dir}")
        return
    if not os.path.exists(dem_path):
        logging.error(f"DEM file missing at: {dem_path}")
        return
    if not os.path.exists(GEOID_PATH):
        logging.error(f"Geoid file missing at: {GEOID_PATH}. Please run Step 2b of setup_env.md")
        return
    
    os.makedirs(output_dir, exist_ok=True)

    # --- Discover Image Bundles ---
    subfolders = [f for f in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, f))]
    prefixes = sorted(list(set(f.replace("_MUL", "").replace("_PAN", "") for f in subfolders if "_MUL" in f or "_PAN" in f)))

    # --- Pre-scan to group bundles by Strip (Catalog ID) ---
    # Map: catalog_id -> list of (prefix, datetime, sensor)
    catalog_groups = {}
    
    for prefix in prefixes:
        mul_meta_file = get_primary_file(os.path.join(input_dir, f"{prefix}_MUL"))
        if mul_meta_file and mul_meta_file.upper().endswith('.XML'):
            try:
                meta = parse_wv3_metadata(mul_meta_file)
                acq_time_str = meta["acq_time"]
                clean_time = acq_time_str.replace('Z', '')
                time_fmt = "%Y-%m-%dT%H:%M:%S.%f" if '.' in clean_time else "%Y-%m-%dT%H:%M:%S"
                dt_obj = datetime.datetime.strptime(clean_time, time_fmt)
                
                cat_id = meta.get("catalog_id")
                if not cat_id or str(cat_id).lower() == "none":
                    cat_id = "UNK_CATALOG"
                sensor = meta.get("sensor") or "UNK"
                
                if cat_id not in catalog_groups:
                    catalog_groups[cat_id] = []
                catalog_groups[cat_id].append((prefix, dt_obj, sensor))
            except Exception:
                continue

    # Determine output folder for each prefix based on its group's earliest time
    prefix_output_map = {}
    for cat_id, items in catalog_groups.items():
        # Find earliest time in this strip/group
        earliest_dt = min(item[1] for item in items)
        common_sensor = items[0][2]
        
        folder_name = f"{earliest_dt.strftime('%Y%m%d_%H%M%S')}_{common_sensor}"
        full_group_dir = os.path.join(output_dir, folder_name)
        os.makedirs(full_group_dir, exist_ok=True)
        logging.info(f"Group {cat_id}: mapped {len(items)} bundles to {folder_name}")
        
        for prefix, _, _ in items:
            prefix_output_map[prefix] = full_group_dir

    # Sort prefixes to ensure bundles destined for the same folder are processed contiguously
    # This allows us to maintain a single open log file for the group.
    prefixes.sort(key=lambda p: prefix_output_map.get(p, p))

    current_log_handler = None
    current_log_dir = None
    logger = logging.getLogger()

    for prefix in prefixes:
        pan_meta_file = get_primary_file(os.path.join(input_dir, f"{prefix}_PAN"))
        pan_image_file = get_image_file(os.path.join(input_dir, f"{prefix}_PAN"))
        mul_meta_file = get_primary_file(os.path.join(input_dir, f"{prefix}_MUL"))
        mul_image_file = get_image_file(os.path.join(input_dir, f"{prefix}_MUL"))
        
        if not pan_meta_file or not mul_image_file or not mul_meta_file or not mul_meta_file.upper().endswith('.XML'):
            logging.warning(f"Skipping {prefix}: PAN/MUL image or required MUL .XML metadata file is missing.")
            continue

        temp_calib_file = None
        temp_pan_calib_file = None
        temp_ortho_file = None

        try:
            # 1. Parse metadata for naming and calibration
            logging.info(f"Parsing metadata for {prefix}...")
            calib_params = parse_wv3_metadata(mul_meta_file)

            if prefix in prefix_output_map:
                bundle_output_dir = prefix_output_map[prefix]
            else:
                # Fallback: Construct output folder name per bundle
                acq_time_str = calib_params["acq_time"]
                sensor = calib_params.get("sensor") or "UNK"
                cat_id = calib_params.get("catalog_id")
                if not cat_id or str(cat_id).lower() == "none":
                    cat_id = "UNK_CATALOG"
                clean_time = acq_time_str.replace('Z', '')
                time_fmt = "%Y-%m-%dT%H:%M:%S.%f" if '.' in clean_time else "%Y-%m-%dT%H:%M:%S"
                dt_obj = datetime.datetime.strptime(clean_time, time_fmt)
                
                folder_name = f"{dt_obj.strftime('%Y%m%d_%H%M%S')}_{sensor}"
                bundle_output_dir = os.path.join(output_dir, folder_name)
                os.makedirs(bundle_output_dir, exist_ok=True)
            
            # --- LOGGING SWITCH ---
            # If we have switched output directories (e.g. new strip), switch the log file.
            if bundle_output_dir != current_log_dir:
                if current_log_handler:
                    logger.removeHandler(current_log_handler)
                    current_log_handler.close()
                
                processing_start_ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                log_filename = f"{os.path.basename(bundle_output_dir)}_processing_log_{processing_start_ts}.txt"
                log_path = os.path.join(bundle_output_dir, log_filename)
                
                current_log_handler = logging.FileHandler(log_path)
                current_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
                logger.addHandler(current_log_handler)
                current_log_dir = bundle_output_dir
                logging.info(f"Log file active: {log_path}")

            output_file = os.path.join(bundle_output_dir, f"{prefix}_TOA_10k.tif")
            temp_calib_file = os.path.join(bundle_output_dir, f"{prefix}_temp_calib.tif")
            temp_pan_calib_file = os.path.join(bundle_output_dir, f"{prefix}_temp_pan_calib.tif")
            logging.info(f"Processing Bundle: {prefix} -> {os.path.basename(bundle_output_dir)}")

            # --- Copy Metadata Files & Write Info ---
            metadata_exts = ('.XML', '.IMD', '.TIL', '.RPB', '.TXT')
            files_to_copy = set()
            
            def collect_meta(src_path):
                if not src_path: return
                d = os.path.dirname(src_path)
                for f in os.listdir(d):
                    if f.upper().endswith(metadata_exts):
                        files_to_copy.add(os.path.join(d, f))

            collect_meta(mul_meta_file)
            collect_meta(pan_meta_file)

            # Create source_metadata subdir
            meta_subdir = os.path.join(bundle_output_dir, "source_metadata")
            os.makedirs(meta_subdir, exist_ok=True)

            for src in files_to_copy:
                try:
                    shutil.copy2(src, meta_subdir)
                except Exception as e:
                    logging.warning(f"Failed to copy metadata file {src}: {e}")

            info_data = {
                "processing_timestamp": datetime.datetime.now().isoformat(),
                "prefix": prefix,
                "sensor": calib_params.get("sensor"),
                "catalog_id": calib_params.get("catalog_id"),
                "acq_time": calib_params.get("acq_time"),
                "sun_elevation": calib_params.get("sun_elevation"),
                "inputs": {
                    "pan": pan_image_file,
                    "mul": mul_image_file,
                    "dem": dem_path
                },
                "parameters": {
                    "toa": DO_TOA,
                    "ram": ram,
                    "masking": enable_masking
                }
            }
            
            with open(os.path.join(bundle_output_dir, f"{prefix}_processing_metadata.json"), 'w') as f:
                json.dump(info_data, f, indent=4)

            if DO_TOA:
                # --- 1a. Calibrate PAN to TOA ---
                logging.info("Step 1a: Calibrating PAN image to TOA reflectance...")
                pan_calib_params = parse_wv3_metadata(pan_meta_file, band_keys=['BAND_P'])
                
                pan_sun_elev_rad = math.radians(pan_calib_params["sun_elevation"])
                pan_d2 = pan_calib_params["solar_distance"] ** 2
                pan_gain = pan_calib_params["gains"][0]
                pan_esun = pan_calib_params["solar_irradiances"][0]
                
                pan_refl_factor = (math.pi * pan_d2 * pan_gain) / (pan_esun * math.sin(pan_sun_elev_rad))
                
                pan_calib_app = pyotb.BandMathX({
                    "il": [pan_image_file],
                    "exp": f"im1 * {pan_refl_factor}",
                    "ram": ram
                })
                pan_calib_app.write(temp_pan_calib_file, pixel_type="float")
                
                if keep_temp:
                    logging.info(f"Building pyramids and stats for temp pan calib: {os.path.basename(temp_pan_calib_file)}")
                    subprocess.run(["gdaladdo", "-r", "nearest", temp_pan_calib_file, "4", "8", "16", "32"], check=False)
                    subprocess.run(["gdalinfo", "-approx_stats", temp_pan_calib_file], check=False, stdout=subprocess.DEVNULL)
                
                input_pan_for_fusion = temp_pan_calib_file

                # --- 1b. Calibrate MUL to TOA ---
                logging.info("Step 1b: Manually calculating TOA reflectance with BandMathX...")
                # TOA Reflectance formula: (pi * L * d^2) / (ESUN * sin(sun_elev))
                # where L (radiance) = DN * gain.
                sun_elev_rad = math.radians(calib_params["sun_elevation"])
                d2 = calib_params["solar_distance"] ** 2
                gains = calib_params["gains"]
                esuns = calib_params["solar_irradiances"]

                expressions = []
                # WorldView-3 has 8 multispectral bands
                for i in range(8):
                    band_num = i + 1
                    # Pre-calculate the constant factor for each band to simplify the BandMath expression
                    # Full formula: (DN * gain * pi * d^2) / (ESUN * sin(sun_elev_rad))
                    reflectance_factor = (math.pi * d2 * gains[i]) / (esuns[i] * math.sin(sun_elev_rad))
                    expressions.append(f"im1b{band_num} * {reflectance_factor}")

                calib_app = pyotb.BandMathX({
                    "il": [mul_image_file],
                    "exp": ";".join(expressions),
                    "ram": ram
                })
                # Use float to preserve 0-1 TOA reflectance values before scaling
                calib_app.write(temp_calib_file, pixel_type="float")

                # If keeping temp, generate stats/ovrs immediately so they are available for inspection
                if keep_temp:
                    logging.info(f"Building pyramids and stats for temp calib: {os.path.basename(temp_calib_file)}")
                    subprocess.run(["gdaladdo", "-r", "nearest", temp_calib_file, "4", "8", "16", "32"], check=False)
                    subprocess.run(["gdalinfo", "-approx_stats", temp_calib_file], check=False, stdout=subprocess.DEVNULL)

                input_ms_for_ortho = temp_calib_file
            else:
                input_ms_for_ortho = mul_image_file
                input_pan_for_fusion = pan_image_file

            # Determine target GSD from PAN metadata
            pan_gsd = get_average_gsd(pan_meta_file)
            
            if not pan_gsd and pan_meta_file and pan_meta_file.upper().endswith(".XML"):
                imd_files = glob.glob(os.path.join(os.path.dirname(pan_meta_file), "*.IMD"))
                if imd_files:
                    logging.info(f"GSD not found in XML, trying IMD: {imd_files[0]}")
                    pan_gsd = get_average_gsd(imd_files[0])

            if not pan_gsd:
                logging.warning(f"Could not determine GSD from {pan_meta_file}. Defaulting to 0.5m.")
                pan_gsd = 0.5
            logging.info(f"Using GSD: {pan_gsd:.4f} meters for orthorectification.")

            # 2. PANSHARPENING (Sensor Geometry)
            logging.info("Step 2: Pansharpening (Sensor Geometry)...")
            pxs = pyotb.BundleToPerfectSensor({
                "inp": input_pan_for_fusion,
                "inxs": input_ms_for_ortho,
                "elev.dem": dem_path,
                "elev.geoid": GEOID_PATH,
                "elev.default": 0,
                "method": "bayes",
                "ram": ram
            })

            # Prepare OrthoRectification parameters
            ortho_params = {
                "io.in": pxs,
                "elev.dem": dem_path,
                "elev.geoid": GEOID_PATH,
                "elev.default": 0,
                "interpolator": "bco",
                "outputs.spacingx": pan_gsd,
                "outputs.spacingy": -pan_gsd,
                "outputs.default": 0,
                "opt.ram": ram
            }
            
            if target_epsg:
                logging.info(f"Step 3: Orthorectifying to EPSG:{target_epsg}...")
                ortho_params["map"] = "epsg"
                ortho_params["map.epsg.code"] = target_epsg
            else:
                # Calculate UTM parameters
                ref_lon = calib_params.get("ref_lon")
                ref_lat = calib_params.get("ref_lat")
                
                if ref_lon is None or ref_lat is None:
                    logging.info("Coords not found in MUL XML, checking PAN metadata...")
                    ref_lon, ref_lat = get_reference_coords(pan_meta_file)
                    
                    if ref_lon is None and pan_meta_file and pan_meta_file.upper().endswith(".XML"):
                        imd_files = glob.glob(os.path.join(os.path.dirname(pan_meta_file), "*.IMD"))
                        if imd_files:
                            logging.info(f"Coords not found in XML, trying IMD: {imd_files[0]}")
                            ref_lon, ref_lat = get_reference_coords(imd_files[0])

                if ref_lon is None or ref_lat is None:
                    raise ValueError(f"Could not determine reference coordinates for {prefix}. Cannot calculate UTM zone.")

                utm_zone = int((ref_lon + 180) / 6) + 1
                is_north = (ref_lat >= 0)
                
                logging.info(f"Step 3: Orthorectifying to UTM Zone {utm_zone}...")
                ortho_params["map"] = "utm"
                ortho_params["map.utm.zone"] = utm_zone
                ortho_params["map.utm.northhem"] = is_north
            
            ortho = pyotb.OrthoRectification(ortho_params)

            # 4. SCALE THE RESULT (if calibration was done)
            if DO_TOA:
                logging.info(f"Scaling output by {REFLECTANCE_SCALE}...")
                final_node = pyotb.BandMathX({
                    "il": [ortho],
                    "exp": f"im1 * {REFLECTANCE_SCALE}",
                    "ram": ram
                })
            else:
                final_node = ortho

            # 5. WRITE INTERMEDIATE TILED TIFF
            logging.info("Step 4: Writing intermediate Tiled GeoTIFF...")
            temp_ortho_file = os.path.join(bundle_output_dir, f"{prefix}_temp_ortho.tif")
            # Use valid GDAL GTiff creation options for efficient writing
            tif_opts = "?&gdal:co:TILED=YES&gdal:co:COMPRESS=DEFLATE&gdal:co:PREDICTOR=2&gdal:co:BIGTIFF=YES&gdal:co:BLOCKXSIZE=512&gdal:co:BLOCKYSIZE=512"
            final_node.write(temp_ortho_file + tif_opts, pixel_type=OUTPUT_PIXEL_TYPE)
            logging.info(f"Wrote intermediate image: {temp_ortho_file}")

            # Remove stale statistics metadata propagated from the float input
            # This prevents the uint16 output from reporting 0-1 range stats
            if shutil.which("gdal_edit.py"):
                logging.info("Unsetting stale statistics metadata...")
                subprocess.run(["gdal_edit.py", "-unsetstats", temp_ortho_file], check=False, stdout=subprocess.DEVNULL)

            # If keeping temp, generate stats/ovrs immediately
            if keep_temp:
                logging.info(f"Building pyramids and stats for temp ortho: {os.path.basename(temp_ortho_file)}")
                subprocess.run(["gdaladdo", "-r", "nearest", temp_ortho_file, "4", "8", "16", "32"], check=False)
                subprocess.run(["gdalinfo", "-approx_stats", temp_ortho_file], check=False, stdout=subprocess.DEVNULL)

            # 6. CONVERT TO COG
            logging.info("Step 5: Converting to Cloud-Optimized GeoTIFF (with average overviews)...")
            cmd = [
                "gdal_translate", temp_ortho_file, output_file,
                "-stats", # Force recalculation of statistics for the final COG
                "-a_nodata", "0",
                "-of", "COG",
                "-co", "COMPRESS=DEFLATE",
                "-co", "PREDICTOR=2",
                "-co", "BIGTIFF=YES",
                "-co", "BLOCKSIZE=512",
                "-co", "OVERVIEW_RESAMPLING=AVERAGE",
                "-co", f"NUM_THREADS={threads}"
            ]
            subprocess.run(cmd, check=True)
            logging.info(f"Wrote COG: {output_file}")

            # Calculate stats for final COG
            logging.info("Calculating statistics for final COG...")
            subprocess.run(["gdalinfo", "-stats", output_file], check=False, stdout=subprocess.DEVNULL)

            # 7. RUN OMNIMASK POST-PROCESS
            if enable_masking:
                run_omnimask(output_file, bundle_output_dir, prefix)

        except Exception as e:
            logging.error(f"Error processing {prefix}: {str(e)}\n{traceback.format_exc()}")
        finally:
            # 6. CLEAN UP temporary files
            if not keep_temp:
                temp_files = [f for f in [temp_calib_file, temp_pan_calib_file, temp_ortho_file] if f and os.path.exists(f)]
                for f in temp_files:
                    os.remove(f)
                    logging.info(f"Cleaned up: {f}")
    
    # Cleanup logger at end of processing
    if current_log_handler:
        logger.removeHandler(current_log_handler)
        current_log_handler.close()

def main():
    """Parses arguments and initiates processing."""
    parser = argparse.ArgumentParser(description="Process Maxar imagery using Orfeo ToolBox.")
    parser.add_argument("--input", required=True, help="Path to the base directory containing Maxar subfolders (e.g., *_PAN, *_MUL).")
    parser.add_argument("--output", required=True, help="Path to the directory for processed output files.")
    parser.add_argument("--dem", required=True, help="Path to the DEM file for orthorectification.")
    parser.add_argument("--ram", type=int, default=RAM_MB, help=f"RAM to allocate in MB (default: {RAM_MB}).")
    parser.add_argument("--threads", type=int, default=THREADS, help=f"Number of OTB threads to use (default: {THREADS}).")
    parser.add_argument("--enable-masking", action="store_true", help="Enable cloud/shadow masking with Omnimask.")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary files after processing (default: delete).")
    parser.add_argument("--epsg", type=int, help="Target EPSG code (e.g. 3338) to override automatic UTM zone calculation.")
    
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.output, exist_ok=True)

    # Set OTB default RAM hint to ensure implicit applications also respect the limit
    os.environ["OTB_MAX_RAM_HINT"] = str(args.ram)
    os.environ["OTB_MAX_NUMBER_OF_THREADS"] = str(args.threads)
    os.environ["ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS"] = str(args.threads)

    process_bundle(args.input, args.dem, args.output, args.ram, args.enable_masking, args.keep_temp, args.threads, args.epsg)

if __name__ == "__main__":
    main()