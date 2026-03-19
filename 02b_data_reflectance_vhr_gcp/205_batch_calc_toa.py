import os
import glob
import math
import argparse
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds as window_from_bounds
import subprocess
import sys
import re

# Add imagery_utils to path
# In the container, we clone to /imagery_utils
utils_path = '/imagery_utils'

if os.path.exists(utils_path):
    if utils_path not in sys.path:
        sys.path.append(utils_path)
else:
    # Fallback try relative path if run from different location
    utils_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../imagery_utils"))
    if os.path.exists(utils_path) and utils_path not in sys.path:
         sys.path.append(utils_path)

try:
    from lib import ortho_functions as ortho
    from lib import utils
except ImportError:
    print(f"Error: Could not import 'lib.ortho_functions' or 'lib.utils' from {utils_path}.")
    print("Please ensure imagery_utils is available and dependencies (scipy, lxml) are installed.")
    sys.exit(1)

"""
205_batch_calc_toa.py

Description:
    Step 2 of VHR Workflow.
    Converts Orthorectified DN imagery (Pan and MS) to TOA Reflectance.
    
    This runs BEFORE pansharpening to ensure spectral calibration is applied 
    to the raw data channels.
    
    Logic:
    - Uses imagery_utils_abr_10000 library for calibration logic.
    - Detects if image is PAN (1 band), MS-4 (4 bands), or MS-8 (8 bands).
    - Parses Metadata (XML) for calibration factors.
    - Applies Solar Irradiance and Sun Angle corrections (Reflectance Stretch).
    - Scales output to 0-10,000 (UInt16).

    Usage Example:
        python 205_batch_calc_toa.py \
            --input "/path/to/01_ortho" \
            --output "/path/to/01_ortho_toa" \
            --overwrite
"""

def get_band_map(band_count):
    """Returns the band name mapping based on band count."""
    if band_count == 1:
        return {0: "PAN"}
    elif band_count == 4:
        return {0: "BLUE", 1: "GREEN", 2: "RED", 3: "NIR"}
    elif band_count == 8:
        return {
            0: "COASTAL", 1: "BLUE", 2: "GREEN", 3: "YELLOW",
            4: "RED", 5: "REDEDGE", 6: "NIR", 7: "NIR2"
        }
    else:
        return {}

def map_band_to_utils_key(band_name):
    """Maps akveg-vhr band names to imagery_utils keys."""
    mapping = {
        "PAN": "BAND_P",
        "COASTAL": "BAND_C",
        "BLUE": "BAND_B",
        "GREEN": "BAND_G",
        "YELLOW": "BAND_Y",
        "RED": "BAND_R",
        "REDEDGE": "BAND_RE",
        "NIR": "BAND_N",
        "NIR1": "BAND_N", # Handle alias
        "NIR2": "BAND_N2"
    }
    return mapping.get(band_name)

def add_overviews_and_stats(filepath, threads=1):
    """
    Adds internal overviews and calculates approximate stats for quick visualization.
    """
    print(f"  Adding overviews and stats for {os.path.basename(filepath)}...")
    
    try:
        # Internal Overviews
        subprocess.check_call([
            "gdaladdo", 
            "-r", "nearest", 
            "--config", "COMPRESS_OVERVIEW", "DEFLATE",
            "--config", "PREDICTOR_OVERVIEW", "2",
            "--config", "GDAL_NUM_THREADS", str(threads),
            filepath, 
            "8", "16", "32", "64"
        ])
        
        # Stats
        subprocess.check_call(
            ["gdalinfo", "-approx_stats", "-hist", filepath], 
            stdout=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"    Warning: Could not add overviews/stats: {e}")

def calculate_toa(dn_path, xml_path, out_path, res_pan=None, res_ms=None, resampling=Resampling.bilinear):
    print(f"Calibrating: {os.path.basename(dn_path)}")
    
    # 1. Determine Vendor and Parse Metadata using utils
    # imagery_utils relies on specific file extensions or checking content.
    # We will try to detect vendor from XML content or filename.
    
    calib_dict = None
    vendor = None
    
    try:
        # Check if it's likely DigitalGlobe/Maxar
        # utils.get_dg_metadata_as_xml works for standard Maxar XMLs
        # We can try parsing it.
        etree = None
        
        # Determine vendor/sensor (simplified check)
        # In a robust implementation, we might want to check root tag of XML
        with open(xml_path, 'r', errors='ignore') as f:
            header = f.read(1024)
            
        if "<isd>" in header or "<imd>" in header or "<IMD>" in header or "BAND_P" in header:
             # Likely DG/Maxar
             vendor = "DG"
        elif "pbom" in header or "pvl" in header or "BEGIN_GROUP" in header:
             # Likely GeoEye or Ikonos
             if "IKONOS" in header or "IK01" in header:
                 vendor = "IK"
             else:
                 vendor = "GE"
        else:
            # Fallback/Default to DG if unknown, or let the parsers fail
            vendor = "DG"

        if vendor == "DG":
            try:
                etree = utils.get_dg_metadata_as_xml(xml_path)
                calib_dict = ortho.get_dg_calib_dict(etree, stretch='rf')
            except Exception as e:
                print(f"  DG Parsing failed, trying GE/IK: {e}")
                vendor = None # Reset to try others
        
        if not calib_dict and (vendor == "GE" or vendor is None):
            try:
                etree = utils.get_ge_metadata_as_xml(xml_path)
                calib_dict = ortho.get_ge_calib_dict(etree, stretch='rf')
            except Exception as e:
                if vendor == "GE": print(f"  GE Parsing failed: {e}")
        
        if not calib_dict and (vendor == "IK" or vendor is None):
             try:
                etree = utils.get_ik_metadata_as_xml(xml_path)
                # IK needs regex for filename matching usually, see ortho_functions
                # Construct a dummy regex if needed or pass None if allowed (it might fail)
                # ortho.get_ik_calib_dict needs 'regex'. 
                # Let's try to find a matching regex from utils.IK_patterns
                regex = None
                srcfn = os.path.basename(dn_path)
                for pattern in utils.IK_patterns:
                    if re.search(pattern, srcfn, re.IGNORECASE):
                        regex = pattern
                        break
                if not regex:
                    # Fallback regex?
                    regex = utils.RAW_IK 
                
                calib_dict = ortho.get_ik_calib_dict(etree, xml_path, regex, stretch='rf')
             except Exception as e:
                if vendor == "IK": print(f"  IK Parsing failed: {e}")

        if not calib_dict:
            print(f"  Error: Could not determine calibration factors from {xml_path}")
            return False

    except Exception as e:
        print(f"  Failed to parse Metadata {xml_path}: {e}")
        return False
        
    with rasterio.open(dn_path) as src:
        profile = src.profile.copy()
        profile.update(dtype='uint16', nodata=65535, compress='deflate', predict=2, bigtiff='YES')
        
        # Sanitize profile
        for key in ['photometric', 'interleave', 'alpha', 'extra_samples']:
            profile.pop(key, None)
        
        # Determine target resolution
        target_res = None
        do_resample = False
        if src.count == 1 and res_pan:
            target_res = res_pan
        elif src.count >= 4 and res_ms:
            target_res = res_ms
            
        if target_res:
            scale = src.res[0] / target_res
            # Only resample if difference is significant (>1%)
            if abs(scale - 1.0) > 0.01:
                do_resample = True
                new_width = int(src.width * scale)
                new_height = int(src.height * scale)
                new_transform = src.transform * src.transform.scale(
                    (src.width / new_width), (src.height / new_height))
                profile.update(width=new_width, height=new_height, transform=new_transform)
        
        # Ensure tiled output for efficient writing
        profile.update(tiled=True, blockxsize=512, blockysize=512)

        band_map = get_band_map(src.count)
        
        # Pre-calculate calibration coefficients and validate
        band_coeffs = {}
        missing_calib = False
        for i in range(1, src.count + 1):
            band_name = band_map.get(i - 1, "UNKNOWN")
            utils_key = map_band_to_utils_key(band_name)
            
            if utils_key and utils_key in calib_dict:
                band_coeffs[i] = calib_dict[utils_key]
            else:
                print(f"  Error: Band {i} ({band_name} -> {utils_key}) calibration not found in metadata.")
                missing_calib = True
        
        if missing_calib:
            print(f"  Skipping {os.path.basename(dn_path)} due to missing calibration data.")
            return False
        
        with rasterio.open(out_path, 'w', **profile) as dst:
            # 1. Set Descriptions
            descriptions = []
            for i in range(1, src.count + 1):
                band_idx = i - 1
                band_name = band_map.get(band_idx, "UNKNOWN")
                desc = band_name.lower()
                descriptions.append(desc)
            dst.descriptions = tuple(descriptions)

            # 3. Process in Windows
            for _, window in dst.block_windows(1):
                # Determine source window
                if do_resample:
                    # Map destination window back to source coordinates
                    bounds = rasterio.windows.bounds(window, dst.transform)
                    src_window = window_from_bounds(*bounds, transform=src.transform)
                else:
                    src_window = window

                for i in range(1, src.count + 1):
                    slope, intercept = band_coeffs[i]

                    # Read DN (Windowed)
                    if do_resample:
                        dn = src.read(i, window=src_window, out_shape=(window.height, window.width), resampling=resampling).astype('float32')
                    else:
                        dn = src.read(i, window=src_window).astype('float32')

                    valid_mask = dn > 0
                    rho = dn * slope + intercept
                    rho_scaled = np.clip(rho * 10000, 0, 65534).astype('uint16')
                    rho_scaled[~valid_mask] = 65535

                    dst.write(rho_scaled, i, window=window)
                
    print(f"  Saved TOA: {os.path.basename(out_path)}")
    return True

def format_resolution(res):
    """Formats resolution in meters to DDpddm."""
    if res is None: return None
    val = float(res)
    int_part = int(val)
    frac_part = int(round((val - int_part) * 100))
    return f"{int_part:02d}p{frac_part:02d}m"

def main():
    parser = argparse.ArgumentParser(description="Step 2: Batch Calculate TOA Reflectance (0-10000)")
    parser.add_argument("--input", required=True, help="Folder containing Ortho DN files (MS and Pan)")
    parser.add_argument("--output", required=True, help="Output folder")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    parser.add_argument("--res-pan", type=float, help="Override output resolution for PAN (meters)")
    parser.add_argument("--res-ms", type=float, help="Override output resolution for MS (meters)")
    parser.add_argument("--resampling", default="bilinear", help="Resampling method (nearest, bilinear, cubic, cubic_spline, lanczos, average). Default: bilinear")
    parser.add_argument("--threads", type=int, default=1, help="Number of threads for overviews (default: 1)")
    args = parser.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    # Process both Pan and MS
    search_patterns = ["*_Ortho_*.tif", "*_ortho_ms.tif", "*_ortho_pan.tif", "*_ortho.tif"]
    images = []
    for p in search_patterns:
        images.extend(glob.glob(os.path.join(args.input, p)))
    
    # Deduplicate
    images = list(set(images))

    # Resolve resampling enum
    try:
        res_enum = getattr(Resampling, args.resampling)
    except AttributeError:
        print(f"Warning: Invalid resampling '{args.resampling}'. Defaulting to bilinear.")
        res_enum = Resampling.bilinear
    
    if not images:
        print("No ortho files found to calibrate.")
        return

    for img_path in images:
        # Skip intermediate overviews
        if ".ovr" in img_path: continue

        # Naming: _ortho_ms.tif -> _ortho_ms_toa.tif
        # New Naming: MS_Ortho_02p00m_... -> MS_TOA_02p00m_...
        base_name = os.path.basename(img_path)
        
        if "_Ortho_" in base_name:
            out_name = base_name.replace("_Ortho_", "_TOA_")
            # Update resolution string if we are resampling
            target_res = args.res_pan if "P_Ortho" in base_name or "P_TOA" in out_name else args.res_ms
            if target_res:
                # Regex to replace DDpddm
                new_res_str = format_resolution(target_res)
                out_name = re.sub(r'\d{2}p\d{2}m', new_res_str, out_name)
        elif "_ortho_" in base_name:
            out_name = base_name.replace(".tif", "_toa.tif")
        else:
            out_name = os.path.splitext(base_name)[0] + "_toa.tif"
            
        out_path = os.path.join(args.output, out_name)
        
        if os.path.exists(out_path) and not args.overwrite:
            print(f"Skipping {out_name}, exists.")
            continue
            
        # Find Metadata (should be named like input due to step 200)
        xml_path = None
        base = os.path.splitext(img_path)[0]
        for ext in ['.xml', '.XML', '.imd', '.IMD']:
            if os.path.exists(base + ext):
                xml_path = base + ext
                break
        
        if not xml_path:
            print(f"Skipping {base_name}: Metadata not found.")
            continue
            
        success = calculate_toa(img_path, xml_path, out_path, args.res_pan, args.res_ms, resampling=res_enum)
        
        # Copy metadata forward (optional, but good practice)
        if success:
            dst_meta = os.path.splitext(out_path)[0] + os.path.splitext(xml_path)[1]
            try:
                import shutil
                shutil.copy2(xml_path, dst_meta)
            except: pass
            
            # ADD OVERVIEWS AND STATS
            add_overviews_and_stats(out_path, threads=args.threads)

if __name__ == "__main__":
    main()