import os
import sys
import argparse
import subprocess
import json
import ee

"""
265_segmentation_gee.py

Description:
    Step 6 (Alternative) of VHR Workflow.
    Performs SNIC Segmentation and Iterative Merging on VHR COGs using Google Earth Engine.
    
    Adapts the workflow from 'snic_201911_wMerge.js'.
    
    Inputs:
        - VHR COGs in GCS (e.g., PS_SRLite or PS_TOA)
    
    Outputs:
        - Segmentation Image (Cluster IDs) exported to EE Asset and/or Google Drive.

Usage:
    python 265_segmentation_gee.py \
        --bucket "akveg-data" \
        --prefix "vhr/vhr_cogs_lowres" \
        --asset-dir "projects/akveg-map/assets/segments" \
        --drive-folder "2025_akveg_segments" \
        --project "akveg-map"
"""

def snic_merge(image_orig, sniced, threshold, max_size=256):
    """
    Merges segments based on spectral similarity of their means.
    Replicates 'snic_merge' from snic_201911_wMerge.js.
    """
    bands = image_orig.bandNames()
    
    # Neighbors: min and max over 2px kernel
    # In JS: sniced.focal_min(2) implies radius=2, units=pixels
    min_img = sniced.focal_min(radius=2, units='pixels')
    max_img = sniced.focal_max(radius=2, units='pixels')
    
    # Difference between neighbors
    diff = max_img.subtract(min_img).select(bands)
    clusters_max = max_img.select('clusters')
    
    # Identify similar neighbors
    # max difference of all bands <= threshold
    similar = diff.reduce(ee.Reducer.max()).lte(threshold)
    
    # Update cluster IDs: where similar, take the max ID from neighborhood
    clusters_new = sniced.select('clusters').where(similar, clusters_max).rename('clusters_max')
    
    # Propagate the merge: For each original cluster, assign the max 'new' ID found within it.
    # This ensures the whole cluster moves to the new ID.
    clusters_new = clusters_new.addBands(sniced.select('clusters')) \
        .reduceConnectedComponents(ee.Reducer.max(), 'clusters', max_size) \
        .rename('clusters')
        
    # Recompute means for the new merged clusters
    # We take the original image bands + the new cluster ID
    # Group by the new cluster ID
    return image_orig.select(bands).addBands(clusters_new) \
        .reduceConnectedComponents(ee.Reducer.mean(), 'clusters', max_size) \
        .addBands(clusters_new)

def process_image(gs_path, asset_id, drive_folder, dry_run=False):
    """
    Defines the EE processing graph and submits export tasks.
    """
    filename = os.path.basename(gs_path)
    name_no_ext = os.path.splitext(filename)[0]
    
    print(f"Processing {filename}...")

    # 1. Load Image from GCS
    img = ee.Image.loadGeoTIFF(gs_path)
    
    # Use input projection (do not resample)
    proj = img.projection()
    
    # 2. Pre-process
    # Map bands to standard names. 
    # PS_SRLite/TOA COGs usually have b01_blue, b02_green, b03_red, b04_nir
    # We need blue, green, red, nir for the logic
    img = img.select(
        ['b01_blue', 'b02_green', 'b03_red', 'b04_nir'],
        ['blue', 'green', 'red', 'nir']
    )
    
    # Calculate NDVI
    # (NIR - Red) / (NIR + Red)
    ndvi = img.normalizedDifference(['nir', 'red']).rename('ndvi')
    
    # Create Float Image (0-1) for SNIC
    # Input is 0-10000.
    img_float = img.addBands(ndvi).float().divide(10000)
    
    # 3. SNIC Segmentation
    # Parameters from JS script
    snic_params = {
        'image': img_float,
        'size': 10,
        'compactness': 0.0001,
        'connectivity': 4,
        'neighborhoodSize': 128,
    }
    
    dgSegs = ee.Algorithms.Image.Segmentation.SNIC(**snic_params)
    
    # Select and rename mean bands
    dgSegs_means = dgSegs.select(
        ['blue_mean', 'green_mean', 'red_mean', 'nir_mean', 'ndvi_mean'],
        ['blue', 'green', 'red', 'nir', 'ndvi']
    )
    dgSegs_clusters = dgSegs.select('clusters')
    dgSegs_seeds = dgSegs.select('seeds')
    
    # Recombine for merge function
    sniced = dgSegs_clusters.addBands(dgSegs_means).addBands(dgSegs_seeds)
    
    # 4. Iterative Merging
    merge_threshold = 0.005
    
    # Iteration 1
    dgSegsMerged = snic_merge(img_float, sniced, merge_threshold)
    
    # Iteration 2
    dgSegsMerged2 = snic_merge(img_float, dgSegsMerged, merge_threshold)
    
    # Fill gaps (Mosaic)
    dgSegsMerged2Filled = ee.ImageCollection([dgSegsMerged, dgSegsMerged2]).mosaic()
    
    # Select Clusters band for export
    result_img = dgSegsMerged2Filled.select('clusters')
    
    # 5. Exports
    
    # A. Export to Asset
    if asset_id:
        asset_path = f"{asset_id}/{name_no_ext}_seg"
        print(f"  Exporting to Asset: {asset_path}")
        
        task_asset = ee.batch.Export.image.toAsset(
            image=result_img,
            description=f"asset_{name_no_ext}_seg",
            assetId=asset_path,
            region=img.geometry(),
            crs=proj,
            maxPixels=1e13,
            pyramidingPolicy={'clusters': 'mode'}
        )
        if not dry_run:
            task_asset.start()
            print(f"    Task ID: {task_asset.id}")

    # B. Export to Drive
    if drive_folder:
        print(f"  Exporting to Drive: {drive_folder}/{name_no_ext}_seg.tif")
        
        task_drive = ee.batch.Export.image.toDrive(
            image=result_img,
            description=f"drive_{name_no_ext}_seg",
            folder=drive_folder,
            fileNamePrefix=f"{name_no_ext}_seg",
            region=img.geometry(),
            crs=proj,
            maxPixels=1e13,
            formatOptions={'cloudOptimized': True}
        )
        if not dry_run:
            task_drive.start()
            print(f"    Task ID: {task_drive.id}")

def main():
    parser = argparse.ArgumentParser(description="GEE SNIC Segmentation on GCS COGs")
    parser.add_argument("--bucket", required=True, help="GCS Bucket containing COGs")
    parser.add_argument("--prefix", required=True, help="GCS Prefix (folder) containing COGs")
    parser.add_argument("--asset-dir", help="EE Asset Folder for output (optional)")
    parser.add_argument("--drive-folder", help="Google Drive Folder for output (optional)")
    parser.add_argument("--project", help="Google Cloud Project for EE")
    parser.add_argument("--filter", default="PS_SRLite", help="String to filter input filenames (default: PS_SRLite)")
    parser.add_argument("--dry-run", action="store_true", help="Print tasks without submitting")
    args = parser.parse_args()

    if not args.asset_dir and not args.drive_folder:
        print("Error: Must specify at least one output destination (--asset-dir or --drive-folder).")
        sys.exit(1)

    # Initialize Earth Engine
    try:
        ee.Initialize(project=args.project)
        print("Earth Engine initialized.")
    except Exception as e:
        print(f"Failed to initialize Earth Engine: {e}")
        sys.exit(1)

    # List files in GCS
    gcs_pattern = f"gs://{args.bucket}/{args.prefix}/*{args.filter}*.tif"
    print(f"Searching for files: {gcs_pattern}")
    
    try:
        # Use gsutil to list files
        result = subprocess.check_output(["gsutil", "ls", gcs_pattern], text=True)
        files = result.strip().split('\n')
        files = [f for f in files if f.endswith('.tif')]
    except subprocess.CalledProcessError:
        print("No files found or gsutil error.")
        files = []

    print(f"Found {len(files)} images.")

    for gs_path in files:
        process_image(gs_path, args.asset_dir, args.drive_folder, args.dry_run)

if __name__ == "__main__":
    main()