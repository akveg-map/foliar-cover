#!/usr/bin/env python3
import argparse
import os
import rasterio
import numpy as np
import torch
import torch.nn.functional as F
from rasterio.windows import Window
from transformers import AutoModelForDepthEstimation
from scipy import ndimage
from datetime import datetime
import time
import sys
import tempfile
import shutil
import gc
import json

"""
230_predict_chm_dinov3.py (V3.4 - Production Chunked Scaling)

Optimizations:
1. Chunked Finalization: Row-by-row normalization/scaling to handle giant strips (Order 020) without OOM.
2. Source-Masked Accumulation: Weights are masked by the canonical input footprint (nodata=65535).
3. Memmapped Buffers: Scale-independent processing for massive strips.
4. int16 storage (cm units).
5. Heartbeat Status: Writes periodic JSON status for GCS syncing.
"""

def get_weight_map(tile_size, overlap):
    w = np.ones((tile_size, tile_size), dtype=np.float32)
    taper = np.sin(np.linspace(0, np.pi/2, overlap))**2
    for i in range(overlap):
        val = taper[i]
        w[i, :] *= val
        w[tile_size-1-i, :] *= val
        w[:, i] *= val
        w[:, tile_size-1-i] *= val
    return w

def gcs_to_vsigs(path):
    if path and path.startswith("gs://"):
        return path.replace("gs://", "/vsigs/")
    return path

def update_status(path, data):
    try:
        with open(path, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

def main():
    parser = argparse.ArgumentParser(description="DINOv3 Production Inference V3.4")
    parser.add_argument("--input", required=True, help="Input PS GeoTIFF")
    parser.add_argument("--mask", help="Optional cloud mask")
    parser.add_argument("--output", required=True, help="Output GeoTIFF")
    parser.add_argument("--limit-tiles", type=int)
    parser.add_argument("--model", default="facebook/dinov3-vitl16-chmv2-dpt-head")
    parser.add_argument("--tmp-dir", default="/tmp")
    parser.add_argument("--status-file", default="/tmp/chm_status.json")
    args = parser.parse_args()

    start_time = time.time()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[{datetime.now().isoformat()}] Using device: {device}", flush=True)
    
    print(f"[{datetime.now().isoformat()}] Loading model: {args.model}", flush=True)
    model = AutoModelForDepthEstimation.from_pretrained(args.model).to(device)
    model.eval()

    SAT_MEAN = torch.tensor([0.420, 0.411, 0.296]).view(1, 3, 1, 1).to(device)
    SAT_STD = torch.tensor([0.213, 0.156, 0.143]).view(1, 3, 1, 1).to(device)

    work_dir = tempfile.mkdtemp(dir=args.tmp_dir, prefix="chm_v3_")
    
    try:
        with rasterio.open(gcs_to_vsigs(args.input)) as src:
            profile = src.profile.copy()
            width, height = src.width, src.height
            src_nodata = src.nodata if src.nodata is not None else 65535
            
            tile_size = 1024
            overlap = 128
            step = tile_size - overlap
            weight_map = get_weight_map(tile_size, overlap)
            
            print(f"[{datetime.now().isoformat()}] Initializing memmapped buffers ({width}x{height})...", flush=True)
            sum_h = np.memmap(os.path.join(work_dir, 'sum_h.dat'), dtype='float32', mode='w+', shape=(height, width))
            sum_w = np.memmap(os.path.join(work_dir, 'sum_w.dat'), dtype='float32', mode='w+', shape=(height, width))
            sum_h[:] = 0
            sum_w[:] = 0

            # Pre-read cloud mask if small, or read per chunk if massive
            cloud_ds = None
            if args.mask:
                cloud_ds = rasterio.open(gcs_to_vsigs(args.mask))

            rows = range(0, height, step)
            cols = range(0, width, step)
            grid = [(r, c) for r in rows for c in cols]
            
            # --- V3.6 Optimization: Mid-Strip Verification ---
            start_tile = int(os.environ.get("START_TILE", 0))
            if start_tile > 0:
                print(f"[{datetime.now().isoformat()}] Jumping to start tile: {start_tile}", flush=True)
                grid = grid[start_tile:]

            if args.limit_tiles: grid = grid[:args.limit_tiles]
            
            total_tiles = len(grid)
            print(f"[{datetime.now().isoformat()}] Starting V3.6 Inference on {total_tiles} tiles...", flush=True)

            with torch.inference_mode():
                for i, (r, c) in enumerate(grid):
                    read_win = Window(c, r, tile_size, tile_size)
                    # Use internal NoData mask instead of thresholding reflectance
                    tile_mask_raw = src.read_masks(1, window=read_win, boundless=True)
                    if not np.any(tile_mask_raw > 0):
                        if (i + 1) % 50 == 0:
                            print(f"[{datetime.now().isoformat()}] Skipping empty tile {i+1}...", flush=True)
                        continue

                    data = src.read([3, 2, 1], window=read_win, boundless=True, fill_value=src_nodata)
                    # Rasterio masks: 255 is valid, 0 is nodata
                    tile_mask = (tile_mask_raw > 0).astype(np.float32)
                    
                    data_clipped = np.clip(data, 0, 1500)
                    data_clipped[:, tile_mask == 0] = 0 
                    
                    tensor = torch.from_numpy(data_clipped).unsqueeze(0).to(device).float() / 1500.0
                    tensor = (tensor - SAT_MEAN) / SAT_STD
                    
                    outputs = model(pixel_values=tensor)
                    preds = F.interpolate(outputs.predicted_depth.unsqueeze(1), size=(tile_size, tile_size), mode="bicubic", align_corners=False)
                    chm_tile = preds.squeeze().cpu().numpy()
                    
                    h_slice = slice(r, min(r + tile_size, height))
                    w_slice = slice(c, min(c + tile_size, width))
                    th, tw = h_slice.stop - h_slice.start, w_slice.stop - w_slice.start
                    
                    masked_weight = weight_map[:th, :tw] * tile_mask[:th, :tw]
                    sum_h[h_slice, w_slice] += chm_tile[:th, :tw] * masked_weight
                    sum_w[h_slice, w_slice] += masked_weight

                    if (i + 1) % 50 == 0 or (i + 1) == total_tiles:
                        elapsed = time.time() - start_time
                        tps = (i + 1) / elapsed
                        percent = (i + 1) / total_tiles * 100
                        print(f"[PROGRESS] {datetime.now().isoformat()} | Tile {i+1}/{total_tiles} | Speed: {tps:.2f} t/s", flush=True)
                        update_status(args.status_file, {"tile_current": i + 1, "tile_total": total_tiles, "percent": percent, "tiles_per_sec": tps, "timestamp": datetime.now().isoformat()})

            # 5. --- V3.4 Optimization: Chunked Finalization ---
            print(f"[{datetime.now().isoformat()}] Finalizing strip in chunks...", flush=True)
            profile.update(count=1, dtype='int16', nodata=-9999, compress=None, tiled=True)
            
            with rasterio.open(args.output, 'w', **profile) as dst:
                chunk_size = 5000 # Process 5000 rows at a time
                for start_row in range(0, height, chunk_size):
                    end_row = min(start_row + chunk_size, height)
                    nrows = end_row - start_row
                    
                    # Read chunk from memmaps
                    h_chunk = sum_h[start_row:end_row, :]
                    w_chunk = sum_w[start_row:end_row, :]
                    
                    # Normalize
                    valid_idx = w_chunk > 0
                    chm_chunk = np.zeros((nrows, width), dtype=np.float32)
                    chm_chunk[valid_idx] = h_chunk[valid_idx] / w_chunk[valid_idx]
                    
                    # Scaling & Masking
                    chm_chunk = np.clip(chm_chunk, 0, 327)
                    chm_int = (chm_chunk * 100).astype(np.int16)
                    
                    # Final cleaning
                    mask_chunk = ndimage.binary_erosion(valid_idx, iterations=5)
                    chm_int[~mask_chunk] = -9999
                    
                    if cloud_ds:
                        c_mask = cloud_ds.read(1, window=Window(0, start_row, width, nrows), boundless=True, fill_value=1)
                        chm_int[c_mask > 0] = -9999
                        
                    dst.write(chm_int, 1, window=Window(0, start_row, width, nrows))
                    
                    # Free chunk memory
                    del h_chunk, w_chunk, chm_chunk, chm_int, mask_chunk
                    gc.collect()
                    print(f"  - Finalized rows {start_row} to {end_row}", flush=True)

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        if cloud_ds: cloud_ds.close()

    # 9. --- V3.5 Optimization: Write Metrics JSON ---
    total_elapsed = time.time() - start_time
    
    # Get input size in GB
    try:
        input_size_gb = round(os.path.getsize(args.input) / (1024**3), 2)
    except:
        input_size_gb = "unknown"

    metrics = {
        "strip_id": os.path.basename(args.output).replace("CHM_cm_DINOv3_", "").replace(".tif", ""),
        "input_path": args.input,
        "input_size_gb": input_size_gb,
        "resolution_m": src.res[0],
        "model_name": args.model,
        "inference_version": "V3.5",
        "units": "centimeters",
        "scaling_factor": 100,
        "nodata_value": -9999,
        "footprint_erosion_px": 3,
        "blending_overlap_px": 128,
        "reflectance_stretch_max": 1500,
        "processing_timestamp": datetime.now().isoformat(),
        "total_tiles": total_tiles,
        "inference_time_min": round(total_elapsed / 60, 2),
        "tiles_per_sec": round(total_tiles / total_elapsed, 2)
    }
    metrics_path = args.output.replace(".tif", "_metrics.json")
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"[{datetime.now().isoformat()}] Metrics saved to {metrics_path}", flush=True)

    print(f"[{datetime.now().isoformat()}] V3.5 Inference Complete. Total time: {total_elapsed/60:.1f} min", flush=True)

if __name__ == "__main__":
    main()
