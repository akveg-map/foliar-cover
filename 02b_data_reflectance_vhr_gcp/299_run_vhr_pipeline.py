#!/usr/bin/env python3
import argparse
import subprocess
import os
import sys
import shutil
import glob

"""
299_run_vhr_pipeline.py

Description:
    Wrapper script to run the full VHR processing pipeline (Steps 200-212)
    for a single input folder.
    
    Steps:
    1. 200_ortho_pgc_warp.py (Ortho)
    2. 202_export_ccdc_sr.py (CCDC Export) [Runs asynchronously on EE]
    3. 205_batch_calc_toa.py (TOA)
    4. 210_generate_cloud_mask.py (Cloud Mask) [Runs in 'omni' conda env]
    5. 212_pansharpen_gram_schmidt.py (Pansharpen)
    6. 220_calculate_srlite_params.py (SRLite)
    7. 225_apply_srlite.py (Apply SRLite)
    8. 250_generate_cogs.py (Generate COGs)
    9. 255_upload_cogs.py (Upload COGs)
    10. 256_create_gee_script.py (Create GEE Script)
    11. 265_segmentation_gee.py (Segmentation GEE)

Usage:
    # Sample Folders:
    # 050300601010_01
    # 050300602010_01
    # 050300603010_01

    # Example Usage:
    # conda activate pgc
    # cd akveg-vhr/vhr-pipeline # Assumes starting from parent directory one level above akveg-vhr repo
    python 299_run_vhr_pipeline.py \
        --input "/data/gis/raster_base/Alaska/AKVegMap/EVWHS/navy_north_slope/unzipped/050300601010_01" \
                "/data/gis/raster_base/Alaska/AKVegMap/EVWHS/navy_north_slope/unzipped/050300602010_01" \
                "/data/gis/raster_base/Alaska/AKVegMap/EVWHS/navy_north_slope/unzipped/050300603010_01" \
        --output-base "/data/gis/raster_base/Alaska/AKVegMap/EVWHS/navy_north_slope/pipeline_output_snap" \
        --dem "/data/gis/gis_base/DEM/ifsar/wgs1984_ellipsoid_height/alaska_ifsar_dsm_20200925_plus_us_noaa_g2009.tif" \
        --epsg 3338 \
        --threads 20 \
        --res-pan 0.5 --res-ms 2.0 \
        --skip-seg \
        --seg-asset-dir "projects/akveg-map/assets/segments"
    #     --res-pan 5 --res-ms 20 \
    #     --suffix "_lowres" \
    #     --overwrite \
    #     --skip-ccdc \
    #     --skip-srlite \
    #     --skip-apply \
    #     --skip-ortho \
    #     --skip-toa \
    #     --skip-cloud \
    #     --skip-pansharpen \
    #     --skip-cogs \
"""

def run_step(script_name, args, description, use_conda_env=None):
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"SCRIPT: {script_name}")
    print(f"{'='*60}")

    # Determine script path (assume in same dir as this runner)
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
    
    if not os.path.exists(script_path):
        print(f"Error: Script not found: {script_path}")
        sys.exit(1)

    cmd = []
    
    if use_conda_env:
        # Use conda run to execute in specific environment
        # Assumes 'conda' is available in PATH
        cmd.extend(["conda", "run", "-n", use_conda_env, "python", script_path])
    else:
        # Use current python interpreter
        cmd.extend([sys.executable, script_path])
        
    cmd.extend(args)
    
    print(f"Running command:\n{' '.join(cmd)}\n")
    
    try:
        subprocess.check_call(cmd)
        print(f"Successfully completed {description}.")
    except subprocess.CalledProcessError as e:
        print(f"Error running {description}. Return code: {e.returncode}")
        sys.exit(1)
    except OSError as e:
        print(f"Execution failed: {e}")
        if use_conda_env:
            print(f"Hint: Ensure 'conda' is in your PATH and environment '{use_conda_env}' exists.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Run VHR Pipeline Steps 200-212")
    
    parser.add_argument("--input", required=True, nargs='+', help="Input directory(ies) containing raw imagery (unzipped)")
    parser.add_argument("--output-base", required=True, help="Base directory for processed output")
    parser.add_argument("--dem", required=True, help="Path to DEM file")
    parser.add_argument("--epsg", required=True, help="Target EPSG code")
    parser.add_argument("--threads", type=int, default=20, help="Number of threads")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    
    # Resolution overrides (Optional)
    parser.add_argument("--res-pan", type=float, help="Output resolution for PAN (meters)")
    parser.add_argument("--res-ms", type=float, help="Output resolution for MS (meters)")
    
    # Folder naming
    parser.add_argument("--suffix", default="", help="Suffix for output folder names (e.g. '_low')")
    
    # Step control
    parser.add_argument("--skip-ortho", action="store_true", help="Skip Step 200 (Ortho)")
    parser.add_argument("--skip-toa", action="store_true", help="Skip Step 205 (TOA)")
    parser.add_argument("--skip-cloud", action="store_true", help="Skip Step 210 (Cloud Mask)")
    parser.add_argument("--skip-pansharpen", action="store_true", help="Skip Step 212 (Pansharpen)")
    parser.add_argument("--skip-ccdc", action="store_true", help="Skip Step 202 (CCDC Export)")
    parser.add_argument("--skip-srlite", action="store_true", help="Skip Step 220 (SRLite)")
    parser.add_argument("--skip-apply", action="store_true", help="Skip Step 225 (Apply SRLite)")
    parser.add_argument("--skip-cogs", action="store_true", help="Skip Step 250 (Generate COGs)")
    parser.add_argument("--skip-upload", action="store_true", help="Skip Step 255 (Upload COGs)")
    parser.add_argument("--skip-gee", action="store_true", help="Skip Step 256 (Create GEE Script)")
    parser.add_argument("--skip-seg", action="store_true", help="Skip Step 265 (Segmentation GEE)")
    
    # Environment for Cloud Masking
    parser.add_argument("--omni-env", default="omni", help="Conda environment name for OmniCloudMask (Step 210)")
    parser.add_argument("--ee-env", default="ee", help="Conda environment name for Earth Engine (Step 202)")
    
    # CCDC/SRLite args
    parser.add_argument("--bucket", default="akveg-data", help="GCS Bucket for CCDC export (Step 202)")
    parser.add_argument("--prefix", default="vhr/landsat_ccdc_sr_pipeline", help="GCS Prefix for CCDC export (Step 202)")
    parser.add_argument("--project", help="Google Cloud Project for EE (Step 202)")
    parser.add_argument("--ccdc-dir", help="Directory containing CCDC exports (Step 220)")
    parser.add_argument("--upload-prefix", default="vhr/vhr_cogs_snap", help="GCS Prefix for COG upload (Step 255)")
    parser.add_argument("--srlite-output", help="Output CSV for SRLite parameters (Step 220)")
    
    # Segmentation args (Step 265)
    parser.add_argument("--seg-asset-dir", help="EE Asset Folder for Segmentation output (Step 265)")
    parser.add_argument("--seg-drive-folder", help="Google Drive Folder for Segmentation output (Step 265)")

    args = parser.parse_args()
    
    # Define Output Directories
    dir_ortho = os.path.join(args.output_base, f"200_ortho{args.suffix}")
    dir_toa = os.path.join(args.output_base, f"205_ortho_toa{args.suffix}")
    dir_cloud = os.path.join(args.output_base, f"210_ortho_toa_cloud{args.suffix}")
    dir_pansharpen = os.path.join(args.output_base, f"212_pansharpen{args.suffix}")
    dir_srlite = os.path.join(args.output_base, f"225_srlite{args.suffix}")
    dir_cogs = os.path.join(args.output_base, f"250_cogs{args.suffix}")
    
    print("\nPipeline Configuration:")
    print(f"  Input: {args.input}")
    print(f"  Output: {args.output_base}")
    print(f"  Suffix: {args.suffix}")
    print(f"  Skipped Steps: {[k.replace('skip_', '') for k, v in vars(args).items() if k.startswith('skip_') and v]}")
    print("-" * 60)

    # --- Step 200: Ortho ---
    if not args.skip_ortho:
        for inp in args.input:
            ortho_args = [
                "--input", inp,
                "--output", dir_ortho,
                "--dem", args.dem,
                "--epsg", str(args.epsg),
                "--threads", str(args.threads)
            ]
            if args.overwrite: ortho_args.append("--overwrite")
            if args.res_pan: ortho_args.extend(["--res-pan", str(args.res_pan)])
            if args.res_ms: ortho_args.extend(["--res-ms", str(args.res_ms)])
            
            run_step("200_ortho_pgc_warp.py", ortho_args, f"Step 200: Orthorectification ({os.path.basename(inp)})")

    # --- Step 202: CCDC Export ---
    if not args.skip_ccdc:
        ccdc_args = [
            "--input", dir_ortho,
            "--bucket", args.bucket,
            "--prefix", args.prefix
        ]
        if args.project:
            ccdc_args.extend(["--project", args.project])
        if args.overwrite:
            ccdc_args.append("--overwrite")
            
        run_step("202_export_ccdc_sr.py", ccdc_args, "Step 202: Export CCDC SR", use_conda_env=args.ee_env)

    # --- Step 205: TOA ---
    if not args.skip_toa:
        toa_args = [
            "--input", dir_ortho,
            "--output", dir_toa,
            "--threads", str(args.threads)
        ]
        if args.overwrite: toa_args.append("--overwrite")
        # Pass resolution args to TOA if provided (to ensure consistency if 200 was skipped or for resizing)
        if args.res_pan: toa_args.extend(["--res-pan", str(args.res_pan)])
        if args.res_ms: toa_args.extend(["--res-ms", str(args.res_ms)])

        run_step("205_batch_calc_toa.py", toa_args, "Step 205: TOA Reflectance")

    # --- Step 210: Cloud Mask ---
    if not args.skip_cloud:
        cloud_args = [
            "--input", dir_toa,
            "--output", dir_cloud,
            "--device", "cuda",
            "--batch-size", "1"
        ]
        if args.overwrite: cloud_args.append("--overwrite")

        run_step("210_generate_cloud_mask.py", cloud_args, "Step 210: Cloud Masking", use_conda_env=args.omni_env)

    # --- Step 212: Pansharpen ---
    if not args.skip_pansharpen:
        ps_args = [
            "--input", dir_toa,
            "--output", dir_pansharpen,
            "--threads", str(args.threads)
        ]
        if args.overwrite: ps_args.append("--overwrite")
        
        run_step("212_pansharpen_gram_schmidt.py", ps_args, "Step 212: Pansharpening")

    # --- Step 220: SRLite ---
    if not args.skip_srlite:
        # Determine CCDC directory (default to 202_ccdc_sr inside output_base if not provided)
        ccdc_dir = args.ccdc_dir if args.ccdc_dir else os.path.join(args.output_base, f"202_ccdc_sr{args.suffix}")
        os.makedirs(ccdc_dir, exist_ok=True)

        srlite_args = [
            "--vhr-dir", dir_toa, dir_pansharpen,
            "--ccdc-dir", ccdc_dir,
            "--output-dir", dir_srlite,
            "--bucket", args.bucket,
            "--prefix", args.prefix,
            "--threads", str(args.threads)
        ]
        if os.path.exists(dir_cloud):
            srlite_args.extend(["--cloud-dir", dir_cloud])
        if args.overwrite:
            srlite_args.append("--overwrite")
            
        run_step("220_calculate_srlite_params.py", srlite_args, "Step 220: Calculate SRLite Params")

    # --- Step 225: Apply SRLite ---
    if not args.skip_apply:
        if os.path.exists(dir_srlite):
            apply_args = [
                "--input-dir", dir_toa, dir_pansharpen,
                "--params-dir", dir_srlite,
                "--output-dir", dir_srlite
            ]
            if args.overwrite: apply_args.append("--overwrite")
            
            run_step("225_apply_srlite.py", apply_args, "Step 225: Apply SRLite Calibration")

    # --- Step 250: Generate COGs ---
    if not args.skip_cogs:
        # Inputs: TOA (MS/Pan), Pansharpened, SRLite (MS/PS), Cloud
        input_dirs = [d for d in [dir_toa, dir_pansharpen, dir_srlite, dir_cloud] if os.path.exists(d)]
        
        if not input_dirs:
            print("Warning: No input directories found for COG generation.")
        else:
            cog_args = [
                "--input-dirs", *input_dirs,
                "--output-dir", dir_cogs,
                "--threads", str(args.threads) # Use pipeline threads for internal compression
            ]
            if args.overwrite: cog_args.append("--overwrite")
            
            run_step("250_generate_cogs.py", cog_args, "Step 250: Generate COGs")

    # --- Step 255: Upload COGs ---
    if not args.skip_upload:
        if os.path.exists(dir_cogs):
            upload_args = [
                "--input-dir", dir_cogs,
                "--bucket", args.bucket,
                "--prefix", args.upload_prefix
            ]
            if args.overwrite:
                upload_args.append("--overwrite")
            
            run_step("255_upload_cogs.py", upload_args, "Step 255: Upload COGs")
        else:
            print("Warning: COG directory not found, skipping upload.")

    # --- Step 256: Create GEE Script ---
    if not args.skip_gee:
        if os.path.exists(dir_cogs):
            gee_out = os.path.join(dir_cogs, f"gee_viz{args.suffix}.js")
            gee_args = [
                "--input-dir", dir_cogs,
                "--bucket", args.bucket,
                "--prefix", args.upload_prefix,
                "--output", gee_out
            ]
            run_step("256_create_gee_script.py", gee_args, "Step 256: Create GEE Script")

    # --- Step 265: Segmentation (GEE) ---
    if not args.skip_seg:
        if not args.seg_asset_dir and not args.seg_drive_folder:
             print("Warning: Skipping Step 265 (Segmentation) because neither --seg-asset-dir nor --seg-drive-folder was provided.")
        else:
            seg_args = [
                "--bucket", args.bucket,
                "--prefix", args.upload_prefix
            ]
            if args.project:
                seg_args.extend(["--project", args.project])
            if args.seg_asset_dir:
                seg_args.extend(["--asset-dir", args.seg_asset_dir])
            if args.seg_drive_folder:
                seg_args.extend(["--drive-folder", args.seg_drive_folder])
            
            # Adjust filter if SRLite was skipped (assuming PS_TOA fallback)
            if args.skip_srlite:
                seg_args.extend(["--filter", "PS_TOA"])

            run_step("265_segmentation_gee.py", seg_args, "Step 265: Segmentation (GEE)", use_conda_env=args.ee_env)

if __name__ == "__main__":
    main()