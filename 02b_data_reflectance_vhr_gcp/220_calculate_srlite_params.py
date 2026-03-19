import os
import glob
import re
import argparse
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.enums import Resampling as RioResampling
import time
import subprocess
import sys
import json

# Try importing sklearn for robust regression
try:
    from sklearn.linear_model import RANSACRegressor, LinearRegression
    from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error, explained_variance_score
except ImportError:
    print("Error: scikit-learn is required. Please install it (pip install scikit-learn).")
    sys.exit(1)

"""
204_calculate_srlite_params.py

Description:
    Step 3 of VHR Workflow (SRLite Calibration).
    Calculates linear regression parameters (slope/offset) to calibrate 
    VHR TOA imagery to match Landsat CCDC Surface Reflectance.
    
    It performs the following:
    1. Matches VHR TOA files with CCDC exports (from Step 203).
    2. Downsamples VHR to 30m to match CCDC grid.
    3. Applies masks:
       - Water (from CCDC water_occurrence)
       - NIR Difference (Change detection/Snow/Cloud check)
       - Cloud (Optional, if external masks provided)
    4. Runs Robust Linear Regression (RANSAC) for B, G, R, N bands.
    5. Outputs a CSV of calibration coefficients.
    
    Regression Methods (--reg-method):
    - rma: Robust Reduced Major Axis (default). Uses RANSAC to find inliers, then fits RMA.
    - ransac: Robust Ordinary Least Squares. Uses RANSAC.
    - ols: Ordinary Least Squares (non-robust).

Usage:
    python 204_calculate_srlite_params.py \
        --vhr-dir "/path/to/02_ortho_toa" \
        --ccdc-dir "/path/to/ccdc_exports" \
        --output-dir "/path/to/04_srlite"
"""

def parse_date_from_filename(filename):
    """Extracts YYYYMMDD_HHMMSS from filename."""
    # Matches 22AUG03213641 or ccdc_20220803_213641
    
    # 1. Try PGC/Full Timestamp (YYYYMMDDHHMMSS)
    match_full = re.search(r'(\d{14})', filename)
    if match_full:
        ts = match_full.group(1)
        return f"{ts[:8]}_{ts[8:]}"

    # Try standard VHR pattern first
    match = re.search(r'(\d{2})([A-Z]{3})(\d{2})(\d{2})(\d{2})(\d{2})', filename, re.IGNORECASE)
    if match:
        yy, mmm, dd, hh, mm, ss = match.groups()
        year = int("20" + yy)
        month_map = {
            'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
        }
        month = month_map.get(mmm.upper())
        if month:
            return f"{year:04d}{month:02d}{dd}_{hh}{mm}{ss}"
            
    # Try CCDC pattern (ccdc_20220803_213641)
    match = re.search(r'(\d{8})_(\d{6})', filename)
    if match:
        return f"{match.group(1)}_{match.group(2)}"
        
    return None

def get_band_indices(filepath):
    """Determine band indices for B, G, R, N based on file type."""
    # Simple heuristic based on band count
    with rasterio.open(filepath) as src:
        count = src.count
        
    # 4-band MS or PS: B, G, R, N
    if count == 4:
        return {'blue': 1, 'green': 2, 'red': 3, 'nir': 4}
    # 8-band MS: C, B, G, Y, R, RE, N, N2
    elif count == 8:
        return {'blue': 2, 'green': 3, 'red': 5, 'nir': 7}
    # 3-band RGB (PS): B, G, R
    elif count == 3:
        return {'blue': 1, 'green': 2, 'red': 3, 'nir': None}
    
    return {}

def process_pair(vhr_path, ccdc_path, intermediate_dir, cloud_path=None, snow_raster=None, reg_method="rma", threads=1):
    """
    Runs regression for a single VHR-CCDC pair.
    """
    results = {}
    
    with rasterio.open(ccdc_path) as ccdc_src:
        # CCDC Bands: 1=Blue, 2=Green, 3=Red, 4=NIR, 5=Water
        # (Based on 203 script export order)
        
        # Read CCDC Data (Target)
        # Scale: CCDC export in 203 was multiplied by 10000 and int16.
        # We read as float for regression.
        ccdc_blue = ccdc_src.read(1).astype(np.float32)
        ccdc_green = ccdc_src.read(2).astype(np.float32)
        ccdc_red = ccdc_src.read(3).astype(np.float32)
        ccdc_nir = ccdc_src.read(4).astype(np.float32)
        water_occ = ccdc_src.read(5)
        
        ccdc_bounds = ccdc_src.bounds
        ccdc_width = ccdc_src.width
        ccdc_height = ccdc_src.height
        ccdc_crs = ccdc_src.crs
        profile = ccdc_src.profile
        
        # Mask Nodata (65535 in CCDC export)
        valid_mask = (ccdc_blue != 65535) & (ccdc_green != 65535)

        # Clamp CCDC to 0-10000 (Reflectance 0-1.0) for regression stability
        ccdc_blue = np.clip(ccdc_blue, 0, 10000)
        ccdc_green = np.clip(ccdc_green, 0, 10000)
        ccdc_red = np.clip(ccdc_red, 0, 10000)
        ccdc_nir = np.clip(ccdc_nir, 0, 10000)

    # Generate downsampled VHR file (30m)
    vhr_name = os.path.basename(vhr_path)
    downsampled_name = os.path.splitext(vhr_name)[0] + "_30m.tif"
    downsampled_path = os.path.join(intermediate_dir, downsampled_name)
    
    if not os.path.exists(downsampled_path):
        # Use gdalwarp to resample and align VHR to CCDC grid
        # We use gdalwarp instead of gdal_translate to ensure exact extent alignment (-te)
        cmd = [
            "gdalwarp",
            "-t_srs", ccdc_crs.to_string(),
            "-te", str(ccdc_bounds.left), str(ccdc_bounds.bottom), str(ccdc_bounds.right), str(ccdc_bounds.top),
            "-ts", str(ccdc_width), str(ccdc_height),
            "-r", "average",
            "-srcnodata", "65535",
            "-dstnodata", "0",
            "-ot", "Float32",
            "-co", "COMPRESS=DEFLATE",
            "-co", "PREDICTOR=2",
            "-co", f"NUM_THREADS={threads}",
            "-multi",
            "-wo", f"NUM_THREADS={threads}",
            vhr_path,
            downsampled_path
        ]
        try:
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            print(f"  Error downsampling VHR: {e}")
            return None

    # Read Resampled VHR (Predictor)
    vhr_indices = get_band_indices(vhr_path)
    if not vhr_indices:
        print(f"  Warning: Could not determine band mapping for {os.path.basename(vhr_path)}")
        return None

    with rasterio.open(downsampled_path) as vhr_src:
        vhr_blue = vhr_src.read(vhr_indices['blue'])
        vhr_green = vhr_src.read(vhr_indices['green'])
        vhr_red = vhr_src.read(vhr_indices['red'])
        
        vhr_nir = None
        if vhr_indices['nir']:
            vhr_nir = vhr_src.read(vhr_indices['nir'])

    # --- MASKING ---
    
    # 1. Valid Data Mask (VHR not 0 or nodata)
    # Assuming 0 is nodata or background
    valid_mask &= (vhr_blue > 0) & (vhr_green > 0)
    
    # 2. Water Mask (from CCDC)
    # JS: water_occurrence <= 50
    water_mask = (water_occ <= 50)
    valid_mask &= water_mask
    
    # 3. NIR Difference Mask (Change/Snow/Cloud)
    # JS: abs(nir - nir_ccdc) <= 500 (scaled 10000) -> 0.05 reflectance
    # If NIR is available
    if vhr_nir is not None:
        nir_diff = np.abs(vhr_nir - ccdc_nir)
        # Threshold 1000 (0.1) is safer for general use, JS used 500 or 1000
        nir_diff_mask = (nir_diff <= 1000) 
        valid_mask &= nir_diff_mask
        
    # 4. Cloud Mask (External)
    if cloud_path and os.path.exists(cloud_path):
        # Assuming cloud mask is 0=Clear, 1=Cloud
        # Need to resample cloud mask to 30m using Nearest Neighbor (categorical)
        with rasterio.open(cloud_path) as csrc:
            cloud_30m = np.zeros((profile['height'], profile['width']), dtype=np.uint8)
            reproject(
                source=rasterio.band(csrc, 1),
                destination=cloud_30m,
                src_transform=csrc.transform,
                src_crs=csrc.crs,
                dst_transform=profile['transform'],
                dst_crs=profile['crs'],
                resampling=RioResampling.nearest
            )
            valid_mask &= (cloud_30m == 0)

    # Apply Mask
    # Flatten arrays
    pixels_valid = valid_mask.flatten()
    
    if np.sum(pixels_valid) < 100:
        print("  Warning: Not enough valid pixels after masking.")
        return None

    def run_regression(x_img, y_img, name):
        X = x_img.flatten()[pixels_valid].reshape(-1, 1)
        y = y_img.flatten()[pixels_valid]
        
        try:
            slope = 1.0
            intercept = 0.0
            inlier_mask = None
            y_pred = None
            X_in = None
            y_in = None

            if reg_method == 'ols':
                # Simple OLS (Non-robust)
                lr = LinearRegression()
                lr.fit(X, y)
                slope = float(lr.coef_[0])
                intercept = float(lr.intercept_)
                inlier_mask = np.ones(len(y), dtype=bool)
                X_in = X.flatten()
                y_in = y
                y_pred = lr.predict(X)
            else:
                # Robust Methods (RANSAC based)
                # RANSAC is good for outlier rejection
                ransac = RANSACRegressor(LinearRegression(), min_samples=0.5, residual_threshold=500)
                ransac.fit(X, y)
                inlier_mask = ransac.inlier_mask_
                X_in = X[inlier_mask].flatten()
                y_in = y[inlier_mask]
                
                if reg_method == 'rma':
                    # Robust RMA (Reduced Major Axis on Inliers)
                    std_x = np.std(X_in)
                    std_y = np.std(y_in)
                    mean_x = np.mean(X_in)
                    mean_y = np.mean(y_in)
                    
                    if std_x == 0:
                        slope = 0.0
                    else:
                        slope = std_y / std_x
                        # RMA slope sign matches correlation
                        if np.corrcoef(X_in, y_in)[0, 1] < 0:
                            slope = -slope
                    
                    intercept = mean_y - slope * mean_x
                    y_pred = X_in * slope + intercept
                    
                else: # ransac (Robust OLS)
                    slope = float(ransac.estimator_.coef_[0])
                    intercept = float(ransac.estimator_.intercept_)
                    y_pred = ransac.predict(X[inlier_mask])
            
            # Calculate metrics on inliers
            metrics = {
                "count": int(len(y)),
                "inlier_count": int(np.sum(inlier_mask)),
                "inlier_ratio": float(np.sum(inlier_mask) / len(y)),
                "r2": float(r2_score(y_in, y_pred)),
                "mae": float(mean_absolute_error(y_in, y_pred)),
                "rmse": float(np.sqrt(mean_squared_error(y_in, y_pred))),
                "mbe": float(np.mean(y_pred - y_in)),
                "explained_variance": float(explained_variance_score(y_in, y_pred)),
                "pearson": float(np.corrcoef(X_in, y_in)[0, 1])
            }
            
            return float(slope), float(intercept), metrics
        except Exception as e:
            print(f"    Regression failed for {name}: {e}")
            return 1.0, 0.0, {}

    # Run for each band
    b_slope, b_off, b_met = run_regression(vhr_blue, ccdc_blue, "Blue")
    g_slope, g_off, g_met = run_regression(vhr_green, ccdc_green, "Green")
    r_slope, r_off, r_met = run_regression(vhr_red, ccdc_red, "Red")
    
    results = {
        'blue_scale': b_slope, 'blue_offset': b_off,
        'green_scale': g_slope, 'green_offset': g_off,
        'red_scale': r_slope, 'red_offset': r_off,
    }
    
    diagnostics = {
        "blue": b_met,
        "green": g_met,
        "red": r_met
    }
    
    if vhr_nir is not None:
        n_slope, n_off, n_met = run_regression(vhr_nir, ccdc_nir, "NIR")
        results['nir_scale'] = n_slope
        results['nir_offset'] = n_off
        diagnostics['nir'] = n_met
    else:
        results['nir_scale'] = 1.0
        results['nir_offset'] = 0.0
        diagnostics['nir'] = {}
        
    return results, diagnostics

def check_and_download_ccdc(dstr, ccdc_dir, bucket, prefix, wait_timeout=0):
    """
    Checks GCS for the expected CCDC file and downloads it if found.
    """
    filename = f"ccdc_{dstr}.tif"
    local_path = os.path.join(ccdc_dir, filename)
    gs_path = f"gs://{bucket}/{prefix}/{filename}"
    
    if os.path.exists(local_path):
        return local_path

    print(f"  CCDC file not found locally. Checking GCS: {gs_path}")
    
    start_time = time.time()
    while True:
        try:
            subprocess.check_call(["gsutil", "cp", gs_path, local_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  Found on GCS. Downloaded to {local_path}...")
            return local_path
        except subprocess.CalledProcessError:
            elapsed = time.time() - start_time
            if elapsed >= wait_timeout:
                print(f"  Failed to download from {gs_path} (Timeout after {elapsed:.0f}s)")
                return None
            
            print(f"  Waiting for CCDC export... ({elapsed:.0f}/{wait_timeout}s)")
            time.sleep(30) # Poll every 30s

def main():
    parser = argparse.ArgumentParser(description="Calculate SRLite Calibration Parameters")
    parser.add_argument("--vhr-dir", required=True, nargs='+', help="Directory(ies) containing VHR TOA files (MS and PS)")
    parser.add_argument("--ccdc-dir", required=True, help="Directory containing CCDC export TIFs")
    parser.add_argument("--bucket", help="GCS Bucket to check for missing CCDC files")
    parser.add_argument("--prefix", help="GCS Prefix to check for missing CCDC files")
    parser.add_argument("--cloud-dir", help="Directory containing Cloud Masks (optional)")
    parser.add_argument("--output-dir", required=True, help="Output directory for param files")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing param files")
    parser.add_argument("--reg-method", default="rma", choices=["rma", "ransac", "ols"], help="Regression method (default: rma)")
    parser.add_argument("--intermediate-dir", help="Directory for intermediate downsampled VHR files")
    parser.add_argument("--threads", type=int, default=1, help="Number of threads for warping")
    parser.add_argument("--wait-timeout", type=int, default=0, help="Seconds to wait for CCDC file on GCS (default: 0)")
    args = parser.parse_args()

    # 1. Index CCDC files by date string
    ccdc_files = {}
    for f in glob.glob(os.path.join(args.ccdc_dir, "*.tif")):
        # Expected format: gcp_ccdc_YYYYMMDD_HHMMSS.tif or ccdc_YYYYMMDD_HHMMSS.tif
        dstr = parse_date_from_filename(os.path.basename(f))
        if dstr:
            ccdc_files[dstr] = f
            
    print(f"Indexed {len(ccdc_files)} CCDC files.")

    os.makedirs(args.output_dir, exist_ok=True)

    if not args.intermediate_dir:
        # Default to sibling of output_dir: .../220_srlite_input
        args.intermediate_dir = os.path.join(os.path.dirname(args.output_dir.rstrip(os.sep)), "220_srlite_input")
    
    os.makedirs(args.intermediate_dir, exist_ok=True)

    # 2. Find VHR files
    vhr_files = []
    for d in args.vhr_dir:
        for ext in ["*.tif", "*.TIF"]:
            vhr_files.extend(glob.glob(os.path.join(d, ext)))
        
    # Filter for TOA files (Exclude Pan/P_TOA)
    vhr_files = [f for f in vhr_files if "_toa" in f.lower() or "_TOA_" in f]
    vhr_files = [f for f in vhr_files if not (os.path.basename(f).startswith("P_TOA") or "_pan" in os.path.basename(f).lower())]
    print(f"Found {len(vhr_files)} VHR TOA files.")

    for vhr_path in vhr_files:
        filename = os.path.basename(vhr_path)
        dstr = parse_date_from_filename(filename)
        
        # Construct output filename early to check existence
        if "_TOA_" in filename:
            out_stem = filename.replace("_TOA_", "_SRLite_")
        else:
            out_stem = filename.replace("_toa.tif", "_srlite.tif")
        
        out_stem = os.path.splitext(out_stem)[0]
        param_filename = f"{out_stem}_params.json"
        param_path = os.path.join(args.output_dir, param_filename)
        
        if os.path.exists(param_path) and not args.overwrite:
            print(f"Skipping {filename}: Params exist ({param_filename})")
            continue
        
        ccdc_path = None
        if dstr and dstr in ccdc_files:
            ccdc_path = ccdc_files[dstr]
        elif dstr and args.bucket and args.prefix:
            # Try to download from GCS
            downloaded_path = check_and_download_ccdc(dstr, args.ccdc_dir, args.bucket, args.prefix, wait_timeout=args.wait_timeout)
            if downloaded_path:
                ccdc_files[dstr] = downloaded_path
                ccdc_path = downloaded_path
        
        if not ccdc_path:
             print(f"Skipping {filename}: No matching CCDC file found for date {dstr}")
             continue
        
        # Determine Cloud Mask Path
        cloud_path = None
        if args.cloud_dir:
            # Assume naming convention: filename_cloud.tif or similar
            # Or replace _toa.tif with _cloud.tif
            base = filename.replace("_toa.tif", "").replace("_ortho_ms", "").replace("_ortho_ps", "")
            # Try a few patterns
            candidates = [
                os.path.join(args.cloud_dir, filename.replace("_TOA_", "_Cloud_")),
                os.path.join(args.cloud_dir, filename.replace("_toa", "_cloud")),
                os.path.join(args.cloud_dir, base + "_cloud.tif"),
                os.path.join(args.cloud_dir, filename.replace(".tif", "_cloud.tif"))
            ]
            for c in candidates:
                if os.path.exists(c):
                    cloud_path = c
                    break
        
        print(f"Processing {filename}...")
        print(f"  Match: {os.path.basename(ccdc_path)}")
        
        try:
            result = process_pair(vhr_path, ccdc_path, args.intermediate_dir, cloud_path, reg_method=args.reg_method, threads=args.threads)
            
            if result:
                params, metrics = result
                
                # Save individual param file (JSON)
                with open(param_path, 'w') as f:
                    json.dump(params, f, indent=4)
                
                # Save metrics file (JSON)
                metrics_filename = f"{out_stem}_metrics.json"
                metrics_path = os.path.join(args.output_dir, metrics_filename)
                with open(metrics_path, 'w') as f:
                    json.dump(metrics, f, indent=4)
                
                # Print quick stats
                print(f"  > Blue: {params['blue_scale']:.3f}x + {params['blue_offset']:.1f}")
                print(f"  > Red:  {params['red_scale']:.3f}x + {params['red_offset']:.1f}")
                print(f"  Saved params to {param_filename}")
                
        except Exception as e:
            print(f"  Error processing pair: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()