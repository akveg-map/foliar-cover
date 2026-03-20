#!/usr/bin/env python3
import argparse
import os
import rasterio
import numpy as np
import torch
from rasterio.windows import Window
from transformers import AutoImageProcessor, AutoModelForDepthEstimation
from PIL import Image
import sys

"""
dinov3_chm_poc.py

Description:
    Proof-of-Concept script to assess the feasibility of running Meta's DINOv3
    Canopy Height Model (CHMv2) on a small image chip extracted from a VHR
    Pansharpened GeoTIFF. Supports GCS paths (gs://) directly.

Usage:
    export HF_TOKEN="your_hugging_face_token"
    export GS_PROJECT_ID="akveg-map"
    python dinov3_chm_poc.py \
        --input "gs://akveg-data/vhr/nome_beaver/processed/..._PS_SRLite_...tif" \
        --output "/tmp/output_chm_chip.tif" \
        --size 1024
"""

def gcs_to_vsigs(path):
    """Converts gs:// path to /vsigs/ path for GDAL/rasterio."""
    if path.startswith("gs://"):
        return path.replace("gs://", "/vsigs/")
    return path

def extract_chip(src_dataset, size):
    """Extracts a central square chip of 'size' pixels from the dataset."""
    width = src_dataset.width
    height = src_dataset.height
    
    col_off = max(0, (width - size) // 2)
    row_off = max(0, (height - size) // 2)
    
    window = Window(col_off, row_off, min(size, width), min(size, height))
    
    # Read the first 3 bands (assumed B, G, R)
    # We will reverse to R, G, B for the model
    data = src_dataset.read([1, 2, 3], window=window)
    transform = src_dataset.window_transform(window)
    
    return data, transform, window

def main():
    parser = argparse.ArgumentParser(description="DINOv3 CHM PoC")
    parser.add_argument("--input", required=True, help="Input VHR GeoTIFF (Local or gs:// path)")
    parser.add_argument("--output", required=True, help="Output CHM GeoTIFF (Local path recommended for PoC)")
    parser.add_argument("--size", type=int, default=1024, help="Size of the chip to process")
    parser.add_argument("--model", default="facebook/dinov3-vitl16-chmv2-dpt-head", help="Hugging Face model ID")
    args = parser.parse_args()

    # GCP Environment Check
    project_id = os.environ.get("GS_PROJECT_ID")
    if args.input.startswith("gs://") and not project_id:
        print("Error: GS_PROJECT_ID environment variable is required for GCS access.")
        sys.exit(1)

    # 1. Load Model and Processor
    print(f"Loading model: {args.model} ...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    try:
        processor = AutoImageProcessor.from_pretrained(args.model)
        model = AutoModelForDepthEstimation.from_pretrained(args.model).to(device)
        model.eval()
    except Exception as e:
        print(f"Failed to load model from Hugging Face. Ensure HF_TOKEN is set if the model is gated.")
        print(f"Error: {e}")
        return

    # 2. Extract Chip
    input_path = gcs_to_vsigs(args.input)
    print(f"Extracting {args.size}x{args.size} chip from {input_path} ...")
    
    try:
        with rasterio.open(input_path) as src:
            # Assuming Bands 1=B, 2=G, 3=R
            data_bgr, transform, window = extract_chip(src, args.size)
            profile = src.profile.copy()
    except Exception as e:
        print(f"Error opening input raster: {e}")
        sys.exit(1)
        
    # Convert BGR (rasterio read order) to RGB
    data_rgb = np.stack([data_bgr[2], data_bgr[1], data_bgr[0]], axis=0)
    
    # Scale from 16-bit reflectance (0-10000 typical) to 8-bit standard image (0-255)
    # The exact scaling might need tweaking based on the specific TOA/SRLite range.
    # For now, we apply a robust stretch (e.g., 98th percentile).
    p2, p98 = np.percentile(data_rgb[data_rgb > 0], (2, 98))
    data_scaled = np.clip((data_rgb - p2) / (p98 - p2), 0, 1) * 255.0
    data_uint8 = data_scaled.astype(np.uint8)
    
    # Convert to PIL Image for Transformers (Shape: H, W, C)
    image_pil = Image.fromarray(data_uint8.transpose(1, 2, 0))

    # 3. Inference
    print("Running DINOv3 CHM inference ...")
    with torch.no_grad():
        inputs = processor(images=image_pil, return_tensors="pt").to(device)
        outputs = model(**inputs)
        
        # DPT model outputs raw depths. Interpolate back to original chip size.
        predicted_depth = outputs.predicted_depth
        prediction = torch.nn.functional.interpolate(
            predicted_depth.unsqueeze(1),
            size=image_pil.size[::-1],
            mode="bicubic",
            align_corners=False,
        )
        
        # Convert to numpy array
        chm_array = prediction.squeeze().cpu().numpy()
        
        # Ensure values are non-negative (canopy height >= 0)
        chm_array = np.clip(chm_array, 0, None).astype(np.float32)

    # 4. Save Output
    output_path = gcs_to_vsigs(args.output)
    print(f"Saving CHM to {output_path} ...")
    profile.update({
        'driver': 'GTiff',
        'height': chm_array.shape[0],
        'width': chm_array.shape[1],
        'count': 1,
        'dtype': 'float32',
        'transform': transform,
        'compress': 'deflate',
        'nodata': -9999.0
    })
    
    # Apply a simple nodata mask where input was 0
    nodata_mask = (data_bgr[0] == 0) & (data_bgr[1] == 0) & (data_bgr[2] == 0)
    chm_array[nodata_mask] = -9999.0

    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(chm_array, 1)

    print("PoC complete!")

if __name__ == "__main__":
    main()