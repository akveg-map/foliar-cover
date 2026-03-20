#!/usr/bin/env python3
import argparse
import os
import rasterio
import numpy as np
import torch
import torch.nn.functional as F
from rasterio.windows import Window
from transformers import AutoImageProcessor, AutoModelForDepthEstimation
from PIL import Image
import sys
from tqdm import tqdm

"""
230_predict_chm_dinov3.py

Description:
    Production script to run Meta's DINOv3 Canopy Height Model (CHMv2) on full
    Maxar pansharpened strips using a sliding-window approach with overlap
    to minimize edge artifacts.

Logic:
    1. Samples the strip to determine 2-98% stretch parameters for RGB normalization.
    2. Iterates over the raster in 1024x1024 patches with 256px overlap.
    3. Runs DINOv3 (ViT-L/16 CHMv2) inference on each patch.
    4. Crops the central 512x512 pixels to discard unreliable edge predictions.
    5. Writes the result to a single-band 0.5m resolution CHM GeoTIFF.

Usage:
    export HF_TOKEN="your_hugging_face_token"
    export GS_PROJECT_ID="akveg-map"
    python 230_predict_chm_dinov3.py \
        --input "gs://akveg-data/vhr/.../PS_SRLite_...tif" \
        --output "gs://akveg-data/vhr/.../CHM_DINOv3_...tif"
"""

def gcs_to_vsigs(path):
    if path.startswith("gs://"):
        return path.replace("gs://", "/vsigs/")
    return path

def get_stretch_params(src, sample_fraction=0.01):
    """Calculates 2-98 percentile stretch parameters based on a random sample."""
    print(f"Sampling {sample_fraction*100}% of pixels for stretch parameters...")
    # Read a coarse version of the first 3 bands
    step = int(1 / np.sqrt(sample_fraction))
    data = src.read([1, 2, 3], out_shape=(3, src.height // step, src.width // step))
    
    # Flatten and remove zeros (nodata)
    flat = data.reshape(3, -1)
    mask = (flat[0] > 0) & (flat[1] > 0) & (flat[2] > 0)
    valid = flat[:, mask]
    
    if valid.size == 0:
        return 0, 10000 # Fallback
        
    p2 = np.percentile(valid, 2, axis=1)
    p98 = np.percentile(valid, 98, axis=1)
    
    print(f"Stretch Params (2-98%): P2={p2}, P98={p98}")
    return p2, p98

def main():
    parser = argparse.ArgumentParser(description="DINOv3 Full-Strip CHM Inference")
    parser.add_argument("--input", required=True, help="Input VHR GeoTIFF (gs:// or local)")
    parser.add_argument("--output", required=True, help="Output CHM GeoTIFF")
    parser.add_argument("--tile-size", type=int, default=1024, help="Inference window size")
    parser.add_argument("--overlap", type=int, default=256, help="Overlap pixels on each side")
    parser.add_argument("--batch-size", type=int, default=1, help="Inference batch size")
    parser.add_argument("--model", default="facebook/dinov3-vitl16-chmv2-dpt-head", help="HF model ID")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 1. Load Model
    print(f"Loading model: {args.model} ...")
    try:
        processor = AutoImageProcessor.from_pretrained(args.model)
        model = AutoModelForDepthEstimation.from_pretrained(args.model).to(device)
        model.eval()
    except Exception as e:
        print(f"Error loading model: {e}")
        print("Hint: Ensure 'transformers' is installed from GitHub and HF_TOKEN is set.")
        sys.exit(1)

    # 2. Open Source and Prepare Output
    input_path = gcs_to_vsigs(args.input)
    output_path = gcs_to_vsigs(args.output)

    with rasterio.open(input_path) as src:
        p2, p98 = get_stretch_params(src)
        
        profile = src.profile.copy()
        profile.update({
            'count': 1,
            'dtype': 'float32',
            'nodata': -9999.0,
            'compress': 'lzw', # LZW is often better for Float32 depth maps
            'tiled': True,
            'blockxsize': 512,
            'blockysize': 512,
            'interleave': 'pixel'
        })

        # Logic for step size: We keep the central part
        # Total tile = 1024. Overlap = 256 on each side.
        # Central kept part = 1024 - 2*256 = 512.
        step_size = args.tile_size - 2 * args.overlap
        
        with rasterio.open(output_path, 'w', **profile) as dst:
            # We iterate such that the 'kept' portions are contiguous
            # Note: We need to handle edges by padding the read window
            
            rows = range(0, src.height, step_size)
            cols = range(0, src.width, step_size)
            total_steps = len(rows) * len(cols)
            
            pbar = tqdm(total=total_steps, desc="Processing Blocks")
            
            for r in rows:
                for c in cols:
                    # The read window includes the overlap
                    read_win = Window(c - args.overlap, r - args.overlap, 
                                      args.tile_size, args.tile_size)
                    
                    # Intersect with source bounds to handle edges
                    read_win = read_win.intersection(Window(0, 0, src.width, src.height))
                    
                    # Read BGR (Maxar 1,2,3)
                    data_bgr = src.read([1, 2, 3], window=read_win)
                    
                    # Create a standard tile-sized buffer (pad with zeros if near edges)
                    tile_bgr = np.zeros((3, args.tile_size, args.tile_size), dtype=data_bgr.dtype)
                    
                    # Calculate offsets within the 1024x1024 tile
                    target_c = max(0, args.overlap - c)
                    target_r = max(0, args.overlap - r)
                    tile_bgr[:, target_r:target_r+read_win.height, target_c:target_c+read_win.width] = data_bgr
                    
                    # Preprocess: Stretch and convert to RGB uint8
                    # data is (3, H, W). p2/p98 are (3,)
                    p2_v = p2[:, None, None]
                    p98_v = p98[:, None, None]
                    
                    # Convert BGR to RGB
                    tile_rgb = tile_bgr[[2, 1, 0], :, :]
                    
                    tile_scaled = np.clip((tile_rgb - p2_v) / (p98_v - p2_v), 0, 1) * 255.0
                    tile_uint8 = tile_scaled.astype(np.uint8)
                    
                    # Inference
                    image_pil = Image.fromarray(tile_uint8.transpose(1, 2, 0))
                    
                    with torch.no_grad():
                        inputs = processor(images=image_pil, return_tensors="pt").to(device)
                        outputs = model(**inputs)
                        
                        # Interpolate to tile size
                        prediction = torch.nn.functional.interpolate(
                            outputs.predicted_depth.unsqueeze(1),
                            size=(args.tile_size, args.tile_size),
                            mode="bicubic",
                            align_corners=False,
                        )
                        chm_tile = prediction.squeeze().cpu().numpy()

                    # Crop to the valid step_size area (central part)
                    # The output window in the destination GeoTIFF
                    out_win = Window(c, r, min(step_size, src.width - c), min(step_size, src.height - r))
                    
                    # Extract the corresponding central part from the 1024x1024 inference
                    # Offset into chm_tile is the overlap
                    crop_tile = chm_tile[args.overlap:args.overlap + out_win.height, 
                                         args.overlap:args.overlap + out_win.width]
                    
                    # Apply nodata mask where input was blank
                    # (Simplified: if any band is 0 in the central area)
                    in_crop = tile_bgr[0, args.overlap:args.overlap + out_win.height, 
                                          args.overlap:args.overlap + out_win.width]
                    crop_tile[in_crop == 0] = -9999.0
                    
                    dst.write(crop_tile.astype(np.float32), 1, window=out_win)
                    
                    pbar.update(1)
            
            pbar.close()

    print(f"Processing Complete. Output saved to: {output_path}")

if __name__ == "__main__":
    main()