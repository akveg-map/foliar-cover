import os
import glob
import argparse
import subprocess
import sys

"""
255_upload_cogs.py

Description:
    Step 5.5 of VHR Workflow.
    Uploads generated COGs to Google Cloud Storage using gsutil.
    Uses parallel upload (-m) and reads file list from stdin (-I).

Usage:
    python 255_upload_cogs.py \
        --input-dir "/path/to/05_cogs" \
        --bucket "akveg-data" \
        --prefix "vhr/vhr_cogs" \
        --overwrite
"""

def main():
    parser = argparse.ArgumentParser(description="Upload COGs to GCS using gsutil")
    parser.add_argument("--input-dir", required=True, help="Directory containing COGs")
    parser.add_argument("--bucket", required=True, help="GCS Bucket")
    parser.add_argument("--prefix", required=True, help="GCS Prefix")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files on GCS")
    args = parser.parse_args()

    # Find files
    files = glob.glob(os.path.join(args.input_dir, "*.tif"))
    if not files:
        print("No TIF files found to upload.")
        return

    print(f"Found {len(files)} files to upload to gs://{args.bucket}/{args.prefix}/")

    # Construct gsutil command
    # -m: Parallel processing
    # cp: Copy
    # -n: No-clobber (skip if exists) - used if overwrite is False
    # -I: Read file list from stdin
    # -o ...: Enable parallel composite uploads for large files (>150MB)
    cmd = [
        "gsutil", 
        "-o", "GSUtil:parallel_composite_upload_threshold=150M", 
        "-m", "cp"
    ]
    
    if not args.overwrite:
        cmd.append("-n")
        
    cmd.extend(["-I", f"gs://{args.bucket}/{args.prefix}/"])
    
    print(f"Running: {' '.join(cmd)}")
    
    # Run subprocess with input from stdin
    file_list_str = "\n".join(files)
    
    try:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)
        process.communicate(input=file_list_str)
        if process.returncode != 0:
            print("Error during upload.")
            sys.exit(process.returncode)
    except Exception as e:
        print(f"Execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()