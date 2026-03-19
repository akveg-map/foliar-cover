import os
import sys
import argparse
import time
import numpy as np
import rasterio
from rasterio.windows import Window
from itertools import chain

# Try importing pysnic
try:
    from pysnic.algorithms.snic import snic, compute_grid
    from pysnic.ndim.operations_collections import nd_computations
    from pysnic.metric.snic import create_augmented_snic_distance
except ImportError:
    print("Error: pysnic is required. Please install it (pip install pysnic).")
    sys.exit(1)

"""
260_segmentation.py

Description:
    Step 6 of VHR Workflow (Segmentation).
    Segments the input raster (e.g., Pansharpened or SRLite output) into 
    superpixels using the SNIC algorithm.
    
    Outputs:
        - Segmentation raster (UInt32) where pixel values are segment IDs.

Usage:
    python 260_segmentation.py \
        --input "/path/to/04_srlite/image.tif" \
        --output "/path/to/06_segmentation/image_seg.tif" \
        --compactness 10.0 \
        --segment-size 100 \
        --tile-size 4096 \
        --overwrite
"""

def process_tile(src, window, compactness, segment_size_sqm, pixel_area_sqm, id_offset):
    """
    Process a single tile of the image.
    """
    # Read data: (Bands, H, W) -> (H, W, Bands)
    data = src.read(window=window)
    
    # Check for empty tile (nodata)
    if not np.any(data):
        return np.zeros((window.height, window.width), dtype=np.int32), 0

    # Transpose to (H, W, Bands) for SNIC
    img_data = np.moveaxis(data, 0, -1)
    
    # Calculate number of segments
    tile_area_sqm = window.width * window.height * pixel_area_sqm
    num_segments = int(round(tile_area_sqm / segment_size_sqm))
    if num_segments < 1:
        num_segments = 1
        
    # 1. Compute Grid (2D)
    # We pass only (H, W) to ensure 2D seeds
    grid = compute_grid(img_data.shape[:2], num_segments)
    seeds = list(chain.from_iterable(grid))
    seed_len = len(seeds)
    
    if seed_len == 0:
        return np.zeros((window.height, window.width), dtype=np.int32), 0

    # 2. Distance Metric
    distance_metric = create_augmented_snic_distance(img_data.shape, seed_len, compactness)
    
    # 3. Run SNIC
    # Use nd_computations["2"] for 2D image with channels
    segmentation, _, _ = snic(
        img_data, 
        seeds, 
        compactness, 
        nd_computations["2"], 
        distance_metric
    )
    
    segmentation = np.array(segmentation, dtype=np.int32)
    
    # Apply ID offset (SNIC returns 0-based IDs)
    segmentation += id_offset
    
    # Mask nodata: If all bands are 0, set segment to 0
    mask = np.all(img_data == 0, axis=-1)
    if np.any(mask):
        segmentation[mask] = 0
        
    # Calculate max ID used
    max_id = segmentation.max()
    
    return segmentation, max_id

def main():
    parser = argparse.ArgumentParser(description="Generate Image Segments using SNIC")
    parser.add_argument("--input", required=True, help="Input multiband raster")
    parser.add_argument("--output", required=True, help="Output segmentation raster")
    parser.add_argument("--compactness", type=float, default=10.0, help="SNIC compactness (default: 10.0)")
    parser.add_argument("--segment-size", type=float, help="Target segment size in square meters")
    parser.add_argument("--segment-pixels", type=float, default=20.0, help="Target segment size in pixels (default: 20)")
    parser.add_argument("--tile-size", type=int, default=4096, help="Tile size for processing (default: 4096)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output")
    args = parser.parse_args()
    
    if os.path.exists(args.output) and not args.overwrite:
        print(f"Skipping {args.output}, exists.")
        return
        
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    with rasterio.open(args.input) as src:
        res_x, res_y = src.res
        pixel_area_sqm = abs(res_x * res_y)
        print(f"Processing {os.path.basename(args.input)} (Res: {res_x:.2f}m, Area: {pixel_area_sqm:.2f} sqm/px)")
        
        if args.segment_size is not None:
            segment_size_sqm = args.segment_size
            print(f"Target Segment Size: {segment_size_sqm} sqm")
        else:
            segment_size_sqm = args.segment_pixels * pixel_area_sqm
            print(f"Target Segment Size: {args.segment_pixels} pixels ({segment_size_sqm:.2f} sqm)")
        
        # Calculate tiling info
        num_tiles_x = (src.width + args.tile_size - 1) // args.tile_size
        num_tiles_y = (src.height + args.tile_size - 1) // args.tile_size
        total_tiles = num_tiles_x * num_tiles_y
        
        print(f"Image Dimensions: {src.width} x {src.height}")
        print(f"Tile Size: {args.tile_size}")
        print(f"Total Tiles: {total_tiles} ({num_tiles_x} cols x {num_tiles_y} rows)")

        profile = src.profile.copy()
        profile.update(dtype=rasterio.int32, count=1, nodata=0, compress='lzw', bigtiff='YES')
        for k in ['photometric', 'interleave', 'alpha', 'extra_samples']: profile.pop(k, None)
            
        current_id_offset = 1
        tile_idx = 0
        
        with rasterio.open(args.output, 'w', **profile) as dst:
            for row in range(0, src.height, args.tile_size):
                for col in range(0, src.width, args.tile_size):
                    tile_idx += 1
                    window = Window(col, row, min(args.tile_size, src.width - col), min(args.tile_size, src.height - row))
                    print(f"  Tile {tile_idx}/{total_tiles} (off: {col}, {row}) ...", end='', flush=True)
                    start_t = time.time()
                    seg_tile, max_id = process_tile(src, window, args.compactness, segment_size_sqm, pixel_area_sqm, current_id_offset)
                    dst.write(seg_tile, 1, window=window)
                    print(f" Done ({time.time() - start_t:.2f}s). IDs: {current_id_offset}-{max_id}")
                    if max_id >= current_id_offset: current_id_offset = max_id + 1

if __name__ == "__main__":
    main()