import os
import glob
import argparse
import pandas as pd
import numpy as np
import rasterio
import sys
import json
import subprocess

"""
225_apply_srlite.py

Description:
    Step 4 of VHR Workflow (SRLite Application).
    Applies the linear calibration parameters calculated in Step 220 to 
    VHR TOA imagery (both MS and Pansharpened).
    
    Outputs:
        - Calibrated 4-band (Blue, Green, Red, NIR) imagery (*_srlite.tif).
        - Data type: UInt16 (0-65535), typically scaled 0-10000 for reflectance.

Usage:
    python 225_apply_srlite.py \
        --input-dir "/path/to/02_ortho_toa" "/path/to/03_pansharpen" \
        --params-dir "/path/to/04_srlite" \
        --output-dir "/path/to/04_srlite"
"""

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
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Stats
        subprocess.check_call(["gdalinfo", "-approx_stats", "-hist", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"    Warning: Could not add overviews/stats: {e}")

def apply_correction(src_path, dst_path, row, threads=1):
    with rasterio.open(src_path) as src:
        # Determine bands to read/write (Standardize to B, G, R, N)
        if src.count == 4:
            bands = [1, 2, 3, 4] # B, G, R, N
        elif src.count == 8:
            bands = [2, 3, 5, 7] # B, G, R, N (WorldView 8-band mapping)
        else:
            print(f"  Skipping {os.path.basename(src_path)}: Band count {src.count} not supported (must be 4 or 8).")
            return False

        profile = src.profile.copy()
        profile.update(
            count=4,
            dtype='uint16',
            nodata=65535,
            compress='deflate',
            predict=2,
            bigtiff='YES',
            tiled=True,
            blockxsize=512,
            blockysize=512,
            num_threads=threads
        )
        
        # Sanitize profile
        for k in ['extra_samples', 'photometric']:
            profile.pop(k, None)

        with rasterio.open(dst_path, 'w', **profile) as dst:
            # Set Band Descriptions
            dst.descriptions = ("blue", "green", "red", "nir")
            
            # Band names corresponding to CSV columns
            band_names = ['blue', 'green', 'red', 'nir']
            
            # Pre-calculate scales and offsets for broadcasting
            # Shape: (4, 1, 1)
            scales = np.array([row[f'{b}_scale'] for b in band_names], dtype=np.float32).reshape(4, 1, 1)
            offsets = np.array([row[f'{b}_offset'] for b in band_names], dtype=np.float32).reshape(4, 1, 1)
            
            # Process in windows to reduce memory usage
            for _, window in dst.block_windows(1):
                # Read all required bands at once
                # data shape: (4, height, width)
                data = src.read(bands, window=window)
                
                # Create mask (65535 is nodata from TOA step)
                mask = (data != 65535)
                
                if not np.any(mask):
                    dst.write(data, window=window)
                    continue
                
                # Apply Linear Correction: Corrected = TOA * scale + offset
                # Cast to float for calculation
                res = data.astype(np.float32) * scales + offsets
                
                # Clip to valid UInt16 range (reserved 65535 for nodata)
                res = np.clip(res, 0, 65534)
                res_u16 = res.astype(np.uint16)
                
                # Re-apply mask
                res_u16[~mask] = 65535
                
                dst.write(res_u16, window=window)
                
    return True

def get_invariant_suffix(filename):
    """
    Extracts the invariant part of the filename (Date, Sensor, CatID) 
    to match MS parameters with PS images.
    """
    # New Naming: {Type}_{Product}_{Resolution}_{Date}_{Time}_{Sensor}_{CatID}.tif
    # e.g. MS_TOA_20p00m_20220803_213641_WV03_CatID.tif
    # We want to match MS_TOA... with PS_TOA...
    parts = filename.split('_')
    if len(parts) >= 7 and parts[1] in ["TOA", "Ortho", "SRLite"]:
        return "_".join(parts[3:])
    
    # Old Naming: {Stem}_ortho_{type}_toa.tif
    if "_ortho_" in filename:
        return filename.split("_ortho_")[0]
        
    return filename

def main():
    parser = argparse.ArgumentParser(description="Apply SRLite Calibration")
    parser.add_argument("--input-dir", required=True, nargs='+', help="Input directories (MS and PS TOA)")
    parser.add_argument("--params-dir", required=True, help="Directory containing SRLite parameter CSVs")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    parser.add_argument("--threads", type=int, default=8, help="Number of threads for overviews")
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Scan params directory
    print(f"Scanning parameters in {args.params_dir}...")
    param_files = glob.glob(os.path.join(args.params_dir, "*_params.json"))
    
    # Build Lookup Map for fuzzy matching (Suffix -> Row)
    suffix_map = {}
    for pfile in param_files:
        # Filename is like MS_SRLite_..._params.json
        # We want to map the invariant suffix of this file to the file path
        fname = os.path.basename(pfile).replace("_params.json", ".tif")
        suffix = get_invariant_suffix(fname)
        suffix_map[suffix] = pfile
    
    # Find images
    images = []
    for d in args.input_dir:
        images.extend(glob.glob(os.path.join(d, "*.tif")))
    
    # Filter for TOA files (Exclude Pan)
    images = [f for f in images if "_toa" in f.lower() or "_TOA_" in f]
    images = [f for f in images if not (os.path.basename(f).startswith("P_TOA") or "_pan" in os.path.basename(f).lower())]
    print(f"Found {len(images)} TOA images.")
    
    for img_path in images:
        fname = os.path.basename(img_path)
        
        row = None
        
        # Try suffix match (e.g. PS matching MS params, or MS matching MS params)
        suffix = get_invariant_suffix(fname)
        if suffix in suffix_map:
            param_file = suffix_map[suffix]
            # Read the JSON param file
            with open(param_file, 'r') as f:
                row = json.load(f)
        
        if row is None:
            # This is expected for files that failed QC in step 220 (e.g. clouds)
            print(f"Skipping {fname}: No parameters found in CSV.")
            continue
            
        if "_TOA_" in fname:
            out_name = fname.replace("_TOA_", "_SRLite_")
        else:
            out_name = fname.replace("_toa.tif", "_srlite.tif")
            
        out_path = os.path.join(args.output_dir, out_name)
        
        if os.path.exists(out_path) and not args.overwrite:
            print(f"Skipping {out_name}, exists.")
            continue
            
        print(f"Calibrating {fname}...")
        try:
            success = apply_correction(img_path, out_path, row, threads=args.threads)
            if success:
                add_overviews_and_stats(out_path, threads=args.threads)
        except Exception as e:
            print(f"  Error processing {fname}: {e}")

if __name__ == "__main__":
    main()