import os
import glob
import argparse
import sys
import shutil
from functools import partial
import rasterio

# Try importing omnicloudmask
try:
    import torch
    from omnicloudmask import predict_from_load_func, load_multiband
except ImportError:
    print("Error: omnicloudmask or torch not found.")
    print("Please ensure you are running this script in the 'omni' conda environment.")
    sys.exit(1)

"""
210_generate_cloud_mask.py

Description:
    Step 2.5 of VHR Workflow (Cloud Masking).
    Generates cloud masks for VHR TOA imagery using OmniCloudMask.
    
    Inputs:
        - Multispectral TOA (*_toa.tif)
    Output:
        - Cloud Mask (*_cloud.tif)
    
    Requirements:
        - 'omni' conda environment with omnicloudmask installed.
        - GPU recommended.

Usage:
    python 210_generate_cloud_mask.py \
        --input "/path/to/02_ortho_toa" \
        --output "/path/to/02_ortho_toa_cloud" \
        --device cuda
"""

def get_band_indices(filepath):
    """
    Determines R, G, NIR band indices based on band count.
    Returns list [R, G, NIR] (1-based).
    """
    with rasterio.open(filepath) as src:
        count = src.count
    
    # 4-band (B, G, R, N) -> R=3, G=2, N=4
    if count == 4:
        return [3, 2, 4]
    # 8-band (C, B, G, Y, R, RE, N, N2) -> R=5, G=3, N=7
    elif count == 8:
        return [5, 3, 7]
    else:
        return None

def main():
    parser = argparse.ArgumentParser(description="Generate Cloud Masks using OmniCloudMask")
    parser.add_argument("--input", required=True, help="Input folder containing MS TOA files")
    parser.add_argument("--output", required=True, help="Output folder for Cloud Masks")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing masks")
    parser.add_argument("--batch-size", type=int, default=1, help="Batch size for inference")
    parser.add_argument("--device", default="cuda", help="Inference device (cuda or cpu)")
    parser.add_argument("--dtype", default="bf16", help="Inference dtype (bf16, float32, etc.)")
    parser.add_argument("--resolution", type=float, default=10.0, help="Resampling resolution in meters (default 10)")
    args = parser.parse_args()

    # Check device availability
    if args.device == 'cuda' and not torch.cuda.is_available():
        print("Warning: CUDA not available, switching to CPU.")
        args.device = 'cpu'

    os.makedirs(args.output, exist_ok=True)

    # Find MS TOA files
    # Look for *_toa.tif. We will filter by band count later.
    files = glob.glob(os.path.join(args.input, "*.tif"))
    # Filter for likely TOA files (from step 205)
    files = [f for f in files if "toa" in os.path.basename(f).lower()]
    
    print(f"Found {len(files)} candidate files in {args.input}")

    for f in files:
        base_name = os.path.basename(f)
        
        # Determine bands
        indices = get_band_indices(f)
        if not indices:
            # Skip non-MS files (e.g. Pan)
            continue
            
        # Define output filename
        if "_TOA_" in base_name:
            final_output_name = base_name.replace("_TOA_", "_Cloud_")
        elif "_toa" in base_name:
            final_output_name = base_name.replace("_toa", "_cloud")
        else:
            final_output_name = base_name.replace(".tif", "_cloud.tif")
            
        final_output_path = os.path.join(args.output, final_output_name)
        
        if os.path.exists(final_output_path) and not args.overwrite:
            print(f"Skipping {final_output_name}, already exists.")
            continue
            
        print(f"Processing {base_name}...")
        
        # Define loader with specific bands and resolution
        # omnicloudmask.load_multiband handles resampling and band selection
        loader = partial(load_multiband, resample_res=args.resolution, band_order=indices)
        
        try:
            # Run inference
            # predict_from_load_func returns a list of Path objects
            pred_paths = predict_from_load_func(
                scene_paths=[f],
                load_func=loader,
                inference_dtype=args.dtype,
                no_data_value=65535, # Matches 205 output nodata
                output_dir=args.output,
                inference_device=args.device,
                mosaic_device='cpu',
                overwrite=True, # Overwrite temp OCM file if it exists
                batch_size=args.batch_size
            )
            
            if pred_paths:
                generated_path = str(pred_paths[0])
                
                # Rename to standard name
                if generated_path != final_output_path:
                    shutil.move(generated_path, final_output_path)
                    
                print(f"  Generated: {final_output_name}")
                
        except Exception as e:
            print(f"  Error processing {base_name}: {e}")
            # Clear cache on error
            if args.device == 'cuda':
                torch.cuda.empty_cache()
        
        # Clear cache between runs
        if args.device == 'cuda':
            torch.cuda.empty_cache()

if __name__ == "__main__":
    main()