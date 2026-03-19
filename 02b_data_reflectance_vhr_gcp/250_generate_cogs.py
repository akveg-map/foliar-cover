import os
import glob
import argparse
import subprocess
import sys

"""
250_generate_cogs.py

Description:
    Step 5 of VHR Workflow (Final Output Generation).
    Converts processed imagery (TOA, Pansharpened, SRLite) into 
    Cloud Optimized GeoTIFFs (COGs).
    
    Uses gdal_translate -of COG.

Usage:
    python 250_generate_cogs.py \
        --input-dirs "/path/to/02_ortho_toa" "/path/to/03_pansharpen" "/path/to/04_srlite" \
        --output-dir "/path/to/05_cogs" \
        --threads 4
"""

def convert_to_cog(src_path, dst_path, overwrite=False, resampling="AVERAGE", threads=1):
    if os.path.exists(dst_path) and not overwrite:
        print(f"Skipping {os.path.basename(dst_path)}, exists.")
        return True

    print(f"Generating COG: {os.path.basename(src_path)}")
    
    # gdal_translate command for COG
    # Using -of COG (GDAL 3.1+)
    # COMPRESS=DEFLATE, PREDICTOR=2 (good for imagery), BIGTIFF=IF_NEEDED
    # OVERVIEW_RESAMPLING=AVERAGE
    cmd = [
        "gdal_translate",
        src_path,
        dst_path,
        "-of", "COG",
        "-co", "COMPRESS=DEFLATE",
        "-co", "PREDICTOR=2",
        "-co", "BIGTIFF=YES",
        "-co", f"OVERVIEW_RESAMPLING={resampling}",
        "-co", f"NUM_THREADS={threads}"
    ]
    
    try:
        # Use subprocess.run to avoid pipe deadlocks that happen with check_call + PIPE
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error converting {os.path.basename(src_path)}: {e}")
        if e.stderr:
            print(f"GDAL Error Output: {e.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Generate Cloud Optimized GeoTIFFs")
    parser.add_argument("--input-dirs", required=True, nargs='+', help="Input directories to search for TIFs")
    parser.add_argument("--output-dir", required=True, help="Output directory for COGs")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    parser.add_argument("--threads", type=int, default=4, help="Number of threads for gdal_translate")
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Find all TIF files in input directories
    images = []
    for d in args.input_dirs:
        # Avoid picking up temp files or non-image tifs if possible, but * is usually safe
        # We exclude .ovr files
        found = glob.glob(os.path.join(d, "*.tif"))
        images.extend([f for f in found if ".ovr" not in f and "aux.xml" not in f])
    
    print(f"Found {len(images)} images to convert.")
    
    tasks = []
    for img_path in images:
        filename = os.path.basename(img_path)
        # Optional: Add suffix or keep same name? 
        # Usually keeping same name is fine if in different folder.
        # Or we can ensure .tif extension (sometimes .TIF)
        base = os.path.splitext(filename)[0]
        out_name = base + "_cog.tif"
        out_path = os.path.join(args.output_dir, out_name)
        
        resampling = "AVERAGE"
        if "_cloud" in filename.lower():
            resampling = "MODE"
        
        tasks.append((img_path, out_path, resampling))

    # Run sequentially to avoid I/O thrashing and OOM on large files.
    # We use internal GDAL threading (NUM_THREADS) to speed up each file.
    for i, (src, dst, res) in enumerate(tasks):
        print(f"[{i+1}/{len(tasks)}] Processing {os.path.basename(src)}...")
        convert_to_cog(src, dst, args.overwrite, res, args.threads)

if __name__ == "__main__":
    main()