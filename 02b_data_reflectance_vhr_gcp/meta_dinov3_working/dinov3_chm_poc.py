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
    Proof-of-Concept script to run Meta's DINOv3 Canopy Height Model (CHMv2) 
    using the Hugging Face 'transformers' library. Supports GCS paths.

Usage:
    export HF_TOKEN="your_hugging_face_token"
    export GS_PROJECT_ID="akveg-map"
    python dinov3_chm_poc.py \
        --input "gs://akveg-data/vhr/nome_beaver/processed/...tif" \
        --output "poc_chm_chip.tif"
"""

def gcs_to_vsigs(path):
    if path.startswith("gs://"):
        return path.replace("gs://", "/vsigs/")
    return path

def extract_chip(src_dataset, size):
    width, height = src_dataset.width, src_dataset.height
    col_off, row_off = max(0, (width - size) // 2), max(0, (height - size) // 2)
    window = Window(col_off, row_off, min(size, width), min(size, height))
    # Read first 3 bands (B, G, R)
    data = src_dataset.read([1, 2, 3], window=window)
    return data, src_dataset.window_transform(window)

def main():
    parser = argparse.ArgumentParser(description="DINOv3 CHM PoC")
    parser.add_argument("--input", required=True, help="Input GeoTIFF (gs:// or local)")
    parser.add_argument("--output", required=True, help="Output GeoTIFF")
    parser.add_argument("--size", type=int, default=1024, help="Chip size")
    parser.add_argument("--model", default="facebook/dinov3-vitl16-chmv2-dpt-head", help="HF model ID")
    args = parser.parse_args()

    # Load Model
    print(f"Loading model: {args.model} ...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    processor = AutoImageProcessor.from_pretrained(args.model)
    model = AutoModelForDepthEstimation.from_pretrained(args.model).to(device)
    model.eval()

    # Read Image
    print(f"Processing chip from {args.input} ...")
    with rasterio.open(gcs_to_vsigs(args.input)) as src:
        data_bgr, transform = extract_chip(src, args.size)
        profile = src.profile.copy()

    # Convert BGR to RGB and scale to uint8
    data_rgb = np.stack([data_bgr[2], data_bgr[1], data_bgr[0]], axis=0)
    # 2-98 percentile stretch
    valid_pixels = data_rgb[data_rgb > 0]
    if valid_pixels.size > 0:
        p2, p98 = np.percentile(valid_pixels, (2, 98))
        img_uint8 = (np.clip((data_rgb - p2) / (p98 - p2), 0, 1) * 255).astype(np.uint8)
    else:
        img_uint8 = data_rgb.astype(np.uint8)
        
    image_pil = Image.fromarray(img_uint8.transpose(1, 2, 0))

    # Inference
    print("Running DINOv3 CHM inference ...")
    with torch.no_grad():
        inputs = processor(images=image_pil, return_tensors="pt").to(device)
        outputs = model(**inputs)
        
        prediction = torch.nn.functional.interpolate(
            outputs.predicted_depth.unsqueeze(1),
            size=image_pil.size[::-1],
            mode="bicubic",
            align_corners=False,
        )
        chm_array = prediction.squeeze().cpu().numpy().astype(np.float32)

    # Save
    print(f"Saving to {args.output} ...")
    profile.update({
        'height': chm_array.shape[0], 'width': chm_array.shape[1],
        'count': 1, 'dtype': 'float32', 'transform': transform,
        'compress': 'deflate', 'nodata': -9999.0
    })
    # Simple nodata mask
    chm_array[(data_bgr[0] == 0) & (data_bgr[1] == 0)] = -9999.0

    with rasterio.open(args.output, 'w', **profile) as dst:
        dst.write(chm_array, 1)

    print("PoC Complete!")

if __name__ == "__main__":
    main()