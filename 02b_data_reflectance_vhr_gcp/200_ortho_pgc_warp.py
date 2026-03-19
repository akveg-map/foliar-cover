# Snap Raster Instructions:
# All outputs at 10m or finer that divide into 10 should be aligned to a snap raster compatible with transform_10m.
# Compatible means keep all the terms of transform_10m except for term 1 and 5 (10 and -10).
# 20m and 30m outputs should be aligned to transform_20m and transform_30m respectively.
#
# Template CRS Transforms (GEE Style):
# transform_10m = [10, 0, 5, 0, -10, 5]
# transform_20m = [20, 0, 10, 0, -20, 10]
# transform_30m = [30, 0, 15, 0, -30, 15]

import os
import glob
import subprocess
import shutil
import argparse
from pathlib import Path
import re
from datetime import datetime
import sys
import json
import math
from osgeo import gdal, osr

# Add imagery_utils to path
utils_path = '/imagery_utils'

if os.path.exists(utils_path):
    if utils_path not in sys.path:
        sys.path.append(utils_path)

try:
    from lib import utils
except ImportError:
    utils = None

"""
200_ortho_pgc_warp.py

Description:
    Orthorectifies Maxar NTF/TIF imagery using gdalwarp with RPCs and a reference DEM.
    Critically, it copies the source metadata (XML/IMD) to the output filename
    so that downstream TOA calibration scripts can find the coefficients.
    
    This replaces the complex pgc_ortho.py wrapper with a direct gdalwarp call
    that mimics the PGC geometric approach.

Usage Example:
    python 200_ortho_pgc_warp.py \
        --input "/data/gis/raster_base/Alaska/AKVegMap/EVWHS/navy_north_slope/unzipped/050300601010_01" \
        --output "/data/gis/raster_base/Alaska/AKVegMap/EVWHS/navy_north_slope/processed_output/01_ortho" \
        --dem "/data/gis/gis_base/DEM/ifsar/wgs1984_ellipsoid_height/alaska_ifsar_dsm_20200925_plus_us_noaa_g2009.tif" \
        --epsg 3338 \
        --threads 20 \
        --overwrite
"""

def find_metadata_file(image_path):
    """
    Finds the associated XML or IMD file for a given image.
    Prioritizes XML, then IMD.
    """
    base = os.path.splitext(image_path)[0]
    # Check for .xml, .XML, .imd, .IMD
    # Also handle the case where image is .NTF but metadata is .XML
    for ext in ['.xml', '.XML', '.imd', '.IMD']:
        if os.path.exists(base + ext):
            return base + ext
    return None

def get_metadata_info(image_path):
    """
    Extracts Catalog ID, Sensor, and Timestamp from metadata.
    Returns (catid, sensor, timestamp_str) or (None, None, None).
    """
    meta_path = find_metadata_file(image_path)
    if not meta_path: return None, None, None
    
    catid = None
    sensor = None
    timestamp = None
    
    # Try using utils if available
    if utils:
        try:
            tree = utils.get_dg_metadata_as_xml(meta_path)
            for elem in tree.iter():
                tag = elem.tag.upper()
                if 'CATID' in tag and elem.text:
                    catid = elem.text
                elif 'SATID' in tag and elem.text:
                    sensor = elem.text
                elif ('EARLIESTACQTIME' in tag or 'FIRSTLINETIME' in tag) and elem.text and not timestamp:
                    # Format: 2022-08-03T21:36:41.000000Z
                    try:
                        dt = datetime.strptime(elem.text.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                        timestamp = dt.strftime("%Y%m%d%H%M%S")
                    except: pass
        except: pass
    
    # Fallback regex
    if not catid or not sensor or not timestamp:
      try:
        with open(meta_path, 'r', errors='ignore') as f:
            c = f.read()
            if not catid:
                m = re.search(r'<CATID>([A-F0-9]+)</CATID>', c, re.IGNORECASE)
                if m: catid = m.group(1)
                else:
                    m = re.search(r'Catalog ID:\s*(\S+)', c, re.IGNORECASE)
                    if m: catid = m.group(1)
            
            if not sensor:
                m = re.search(r'<SATID>(\S+)</SATID>', c, re.IGNORECASE)
                if m: sensor = m.group(1)
            
            if not timestamp:
                m = re.search(r'<(?:EARLIESTACQTIME|FIRSTLINETIME)>(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', c, re.IGNORECASE)
                if m:
                    dt = datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")
                    timestamp = dt.strftime("%Y%m%d%H%M%S")
      except: pass
      
    return catid, sensor, timestamp

def run_cmd_filter_stderr(cmd, ignore_keywords):
    """
    Runs a command, allowing stdout to pass through (for progress bars),
    but filtering stderr lines that contain all ignore_keywords.
    """
    try:
        # stdout=None inherits stdout (terminal), so progress bars work.
        # stderr=PIPE allows us to read and filter errors.
        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True)
        
        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break
            if line:
                if all(k in line for k in ignore_keywords):
                    continue
                sys.stderr.write(line)
                sys.stderr.flush()
        return process.returncode
    except Exception as e:
        sys.stderr.write(f"Error executing command: {e}\n")
        return 1

def add_overviews_and_stats(filepath, threads=1):
    """
    Adds internal overviews and calculates approximate stats for quick visualization.
    """
    print(f"  Adding overviews and stats for {os.path.basename(filepath)}...")
    
    # 1. Overviews (Internal, fast levels only)
    # 2, 4, 8, 16 is usually enough for quick checking. 
    # Use -r average for better visual quality or nearest for speed.
    cmd = [
            "gdaladdo", 
            "-r", "nearest", 
            "--config", "COMPRESS_OVERVIEW", "DEFLATE",
            "--config", "PREDICTOR_OVERVIEW", "2",
            "--config", "GDAL_NUM_THREADS", str(threads),
            "-ro", # open read-only (though actually we are modifying it, this flag sometimes safer with separate .ovr, but we want internal if possible. gdaladdo defaults to internal if GTiff)
            filepath, 
            "8", "16", "32", "64"
        ]
    if run_cmd_filter_stderr(cmd, ["Bad value", "ExtraSamples"]) != 0:
        print("    Warning: Error creating overviews (check logs).")

    # 2. Approximate Stats
    # gdalinfo -stats uses -approx_stats logic often by default on large files unless -mm is used, 
    # but explicit -stats triggers calculation.
    # Note: gdalinfo prints to stdout, we just want the side effect of the PAM .aux.xml being created/updated
    try:
        subprocess.call(["gdalinfo", "-approx_stats", "-hist", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        print("    Error calculating stats.")

def get_snap_origin(res):
    """
    Returns (origin_x, origin_y) based on resolution rules.
    """
    # 10m or finer that divide into 10 -> transform_10m (5, 5)
    # Check if 10 is divisible by res (e.g. 10 / 0.5 = 20.0)
    if res <= 10 and abs((10 / res) - round(10 / res)) < 1e-6:
        return 5.0, 5.0
    elif abs(res - 20.0) < 1e-6:
        return 10.0, 10.0
    elif abs(res - 30.0) < 1e-6:
        return 15.0, 15.0
    else:
        # Default to 0,0 for others
        return 0.0, 0.0

def calculate_snapped_extent(input_files, epsg, res, dem_path):
    """
    Calculates the output extent snapped to the grid defined by resolution and origin rules.
    Iterates through inputs to determine the union extent, then snaps.
    """
    try:
        xmin_union = float('inf')
        ymin_union = float('inf')
        xmax_union = float('-inf')
        ymax_union = float('-inf')

        warp_options = gdal.WarpOptions(
            format='VRT',
            dstSRS=f'EPSG:{epsg}',
            rpc=True,
            transformerOptions=[f'RPC_DEM={dem_path}'],
            xRes=res,
            yRes=res
        )
        
        # Process each file individually to get its warped extent
        # This avoids the "gdalwarp -of VRT just takes into account the first source dataset" warning
        for f in input_files:
            ds = gdal.Warp('', f, options=warp_options)
            if not ds:
                continue
                
            gt = ds.GetGeoTransform()
            # gt = [xmin, xres, 0, ymax, 0, -yres]
            
            width = ds.RasterXSize
            height = ds.RasterYSize
            
            xmin = gt[0]
            ymax = gt[3]
            xmax = xmin + width * gt[1]
            ymin = ymax + height * gt[5] # gt[5] is negative
            
            # Update union
            if xmin < xmin_union: xmin_union = xmin
            if ymin < ymin_union: ymin_union = ymin
            if xmax > xmax_union: xmax_union = xmax
            if ymax > ymax_union: ymax_union = ymax
            
            ds = None # Close dataset

        if xmin_union == float('inf'):
            return None
        
        origin_x, origin_y = get_snap_origin(res)
        
        # Snap outwards
        xmin_snap = origin_x + math.floor((xmin_union - origin_x) / res) * res
        ymax_snap = origin_y + math.ceil((ymax_union - origin_y) / res) * res
        xmax_snap = origin_x + math.ceil((xmax_union - origin_x) / res) * res
        ymin_snap = origin_y + math.floor((ymin_union - origin_y) / res) * res
        
        return (xmin_snap, ymin_snap, xmax_snap, ymax_snap)
    except Exception as e:
        print(f"Warning: Could not calculate snapped extent: {e}")
        return None

def run_ortho(input_files, output_file, dem_path, epsg=None, resolution=None, resampling="cubic", overwrite=False, threads=16):
    """
    Runs gdalwarp to orthorectify the image.
    """
    if isinstance(input_files, str):
        input_files = [input_files]
    
    # 1. Construct gdalwarp command
    # -rpc: Use RPCs from input
    # -to RPC_DEM=...: The critical PGC flag to use the DEM for RPC correction
    # -dstnodata 0: Ensure background is 0
    # -co COMPRESS=DEFLATE: Better compression for final archive
    # -co PREDICTOR=2: Horizontal differencing (good for imagery)
    # -co BIGTIFF=IF_NEEDED: Prevent 4GB limit errors
    # -multi: Enable multithreaded I/O
    # -wo NUM_THREADS=...: Use specified cores for warping
    # -wm 2048: Use 2GB of RAM for warping buffer
    
    cmd = [
        "gdalwarp",
        "-rpc", 
        "-nomd",
        "-to", f"RPC_DEM={dem_path}",
        "-dstnodata", "0",
        "-multi",
        "-wo", f"NUM_THREADS={threads}",
        "-wm", "2048",
        "-co", "COMPRESS=DEFLATE",
        "-co", "PREDICTOR=2",
        "-co", "BIGTIFF=YES",
        "-co", "TILED=YES",
        "-co", f"NUM_THREADS={threads}",
        "-co", "PHOTOMETRIC=MINISBLACK",
        "-r", resampling,
    ] + input_files + [
        output_file
    ]

    # Add Target SRS if provided (e.g. EPSG:3338)
    if epsg:
        cmd.extend(["-t_srs", f"EPSG:{epsg}"])

    # Add resolution override if provided (e.g., ensure MS is 2m, Pan is 0.5m)
    if resolution:
        cmd.extend(["-tr", str(resolution), str(resolution)])

    # Calculate and add snapped extent if EPSG and resolution are available
    if epsg and resolution:
        extent = calculate_snapped_extent(input_files, epsg, resolution, dem_path)
        if extent:
            cmd.extend(["-te", str(extent[0]), str(extent[1]), str(extent[2]), str(extent[3])])

    # Pass overwrite flag to gdalwarp
    if overwrite:
        cmd.append("-overwrite")

    print(f"Running: {' '.join(cmd[:10])} ... ({len(input_files)} inputs)")
    
    if run_cmd_filter_stderr(cmd, ["Bad value", "ExtraSamples"]) == 0:
        return True
    else:
        print(f"Error orthorectifying {output_file}")
        return False

def format_resolution(res):
    """Formats resolution in meters to DDpddm (e.g. 0.5 -> 00p50m)."""
    if res is None: return "native"
    val = float(res)
    int_part = int(val)
    frac_part = int(round((val - int_part) * 100))
    return f"{int_part:02d}p{frac_part:02d}m"

def get_resolution_from_file(filepath):
    """Estimates resolution from file using gdalinfo if not provided."""
    try:
        out = subprocess.check_output(["gdalinfo", filepath], text=True)
        m = re.search(r'Pixel Size = \(([\d\.]+)', out)
        if m: return float(m.group(1))
    except: pass
    return 0.0

def main():
    parser = argparse.ArgumentParser(description="Orthorectify Maxar Imagery (PGC Style)")
    parser.add_argument("--input", required=True, help="Input folder containing NTF/TIF files")
    parser.add_argument("--output", required=True, help="Output folder for Orthos")
    parser.add_argument("--dem", required=True, help="Path to the DEM (Mosaic or VRT)")
    parser.add_argument("--epsg", help="Target EPSG code (e.g. 3338). Defaults to WGS84 if not set.", default=None)
    parser.add_argument("--threads", type=int, default=16, help="Number of threads to use for gdalwarp. Default is 16.")
    parser.add_argument("--res-pan", type=float, help="Output resolution for PAN images (meters)")
    parser.add_argument("--res-ms", type=float, help="Output resolution for MS images (meters)")
    parser.add_argument("--resampling", default="cubic", help="Resampling method (nearest, bilinear, cubic, cubicspline, lanczos, average). Default: cubic")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Find images (recursive)
    extensions = ["*.ntf", "*.NTF", "*.tif", "*.TIF"]
    images = []
    for ext in extensions:
        images.extend(list(Path(args.input).rglob(ext)))

    print(f"Found {len(images)} images to process.")

    # Group images by Strip (CATID) and Band Type
    groups = {}
    for img_path in images:
        img_path = str(img_path)
        
        # Skip existing orthos, overviews, or intermediate files
        if "ortho" in img_path or "ovr" in img_path or "aux" in img_path:
            continue
            
        filename = os.path.basename(img_path)
        lower_name = filename.lower()
        
        # Determine Band Type
        if "pan" in lower_name or "-p" in lower_name:
            band_type = "pan"
        elif "ms" in lower_name or "-m" in lower_name:
            band_type = "ms"
        else:
            band_type = "unknown"
            
        # Determine Strip ID (CATID)
        catid, sensor, ts = get_metadata_info(img_path)
        if not catid:
            # Fallback to filename prefix (stripping part number)
            # e.g. 22AUG..._P001.NTF -> 22AUG...
            catid = re.sub(r'_[PM]\d{3}.*$', '', os.path.splitext(filename)[0], flags=re.IGNORECASE)
            
        # Group by CATID and Band Type (ignore timestamp variations within strip)
        key = (catid, sensor, band_type)
        if key not in groups: groups[key] = []
        groups[key].append(img_path)
        
    print(f"Grouped into {len(groups)} strips.")

    for (catid, sensor, band_type), img_list in groups.items():
        # Sort to ensure deterministic order (e.g. P001, P002)
        img_list.sort()
        
        # Use first image for naming reference
        first_img = img_list[0]
        filename = os.path.basename(first_img)
        
        # Determine output filename suffix based on type
        original_stem = re.sub(r'_[PM]\d{3}(?=_|$)', '', os.path.splitext(filename)[0], flags=re.IGNORECASE)
        original_stem = re.sub(r'_R\d+C\d+(?=_|$)', '', original_stem, flags=re.IGNORECASE)
        
        # Re-extract timestamp from first image to ensure consistency for the whole mosaic
        _, _, ts = get_metadata_info(first_img)
        if ts and len(ts) == 14:
            ts_fmt = f"{ts[:8]}_{ts[8:]}"
        else:
            ts_fmt = "00000000_000000"
        
        sensor_str = sensor if sensor else "Unknown"
        catid_str = catid if catid else "Unknown"
        
        # Determine Type and Resolution
        if band_type == "pan":
             type_str = "P"
             res_val = args.res_pan
        elif band_type == "ms":
             type_str = "MS"
             res_val = args.res_ms
        else:
             type_str = "Unknown"
             res_val = None

        # If resolution not provided, try to guess from first image
        if res_val is None:
            res_val = get_resolution_from_file(first_img)
        
        res_str = format_resolution(res_val)
        
        # Construct Name: {Type}_{Product}_{Resolution}_{DateTime}_{Sensor}_{CatID}.tif
        out_name = f"{type_str}_Ortho_{res_str}_{ts_fmt}_{sensor_str}_{catid_str}.tif"

        out_path = os.path.join(args.output, out_name)

        # Skip if exists
        if os.path.exists(out_path) and not args.overwrite:
            print(f"Skipping {out_name}, already exists.")
            continue

        # ORTHO
        # Pass explicit resolution if we have it (args), otherwise None (native)
        # Note: res_val might be derived from file for naming, but we only pass to gdalwarp if it was an arg override
        warp_res = args.res_pan if band_type == "pan" else args.res_ms
        
        success = run_ortho(img_list, out_path, args.dem, epsg=args.epsg, resolution=warp_res, resampling=args.resampling, overwrite=args.overwrite, threads=args.threads)

        # COPY METADATA
        if success:
            # Use metadata from first image
            meta_src = find_metadata_file(first_img)
            if meta_src:
                meta_ext = os.path.splitext(meta_src)[1]
                meta_dst = os.path.splitext(out_path)[0] + meta_ext
                shutil.copy2(meta_src, meta_dst)
                print(f"Copied metadata to {meta_dst}")
            else:
                print(f"WARNING: No XML/IMD found for {filename}. TOA step will fail for this image.")
            
            # ADD OVERVIEWS AND STATS
            add_overviews_and_stats(out_path, threads=args.threads)
            
            # WRITE SIDECAR JSON FILE
            try:
                json_path = os.path.splitext(out_path)[0] + "_meta.json"
                meta_data = {
                    "original_stem": original_stem,
                    "input_files": [os.path.basename(i) for i in img_list]
                }
                with open(json_path, "w") as f:
                    json.dump(meta_data, f, indent=4)
            except Exception as e:
                print(f"Warning: Could not save metadata json: {e}")

if __name__ == "__main__":
    main()