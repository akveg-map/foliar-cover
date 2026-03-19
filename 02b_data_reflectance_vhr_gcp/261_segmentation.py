"""
description: runs SNIC segmentation at three Navy sites with user-chosen parameters
authors: dwexler, mmacander
date: 2026/02/24
"""

# imports
import ee
import argparse
import os

# authenticate and initialize Earth Engine
# ee.Authenticate() # Removed for headless pipeline execution

# ==========================================================
# 1. VARIABLES TO BE MODIFIED BY THE USER
# ==========================================================
# list of Gaussian kernel sizes (pixels)
KERNEL_SIZES = [1]
# list of SNIC sizes (pixels)
SNIC_SIZES = [10]
# resolution of the input imagery
SCALE = 2
# spectral similarity threshold used to merge segments
THRESHOLD_SPECTRAL = 0.005
# size threshold below which segments are removed
THRESHOLD_SIZE = 5

# ==========================================================
# 3. PIPELINE FUNCTIONS
# ==========================================================
def merge_spectral(clusters, raw, threshold):
    """Merges segments using raw spectral data."""
    # 1. calculate spectral means of clusters over raw image
    raw_means = raw.addBands(clusters).reduceConnectedComponents(
        reducer=ee.Reducer.mean(),
        labelBand='clusters',
        maxSize=256
    )
    # 2. detect edges on the raw spectral means
    min_val = raw_means.focal_min(radius=1.5, units='pixels')
    max_val = raw_means.focal_max(radius=1.5, units= 'pixels')
    diff = max_val.subtract(min_val)
    # 3. identify weak boundaries (spectral diff <= threshold)
    similar = diff.reduce(ee.Reducer.max()).lte(ee.Number(threshold))
    # 4. merge: adopt neighbor's ID where spectral difference is low
    clusters_max = clusters.focal_max(radius=1.5, units='pixels')
    clusters_merged = clusters.where(similar, clusters_max)
    return clusters_merged.rename('clusters')

def merge_size(clusters, threshold):
    """Merges segments based on pixel count."""
    # 1. count pixels in each segment
    size = clusters.connectedPixelCount(maxSize=100, eightConnected=True)
    # 2. mask small segments
    large_segments = clusters.updateMask(size.gte(threshold))
    # 3. fill holes with majority neighbor
    filled = large_segments.unmask(
        large_segments.focal_mode(radius=1.5, iterations=1)
    )
    return filled.rename('clusters')

def run_segmentation(image, kernel_size, snic_size):
    """Main function for SNIC segmentation and post-processing."""
    # rename input bands
    raw = image.select(['blue', 'green', 'red', 'nir'])
    # add NDVI band
    ndvi = raw.normalizedDifference(['nir', 'red']).rename('ndvi')
    raw = raw.addBands(ndvi).float().divide(10000)
    # smooth image with Gaussian kernel
    image_for_snic = raw
    if kernel_size > 0:
        kernel = ee.Kernel.gaussian(
            radius=kernel_size, 
            sigma=0.75, 
            units='pixels', 
            normalize=True)
        image_for_snic = raw.convolve(kernel)
    # perform SNIC segmentation
    snic = ee.Algorithms.Image.Segmentation.SNIC(
        image=image_for_snic,
        size=snic_size,
        compactness=1/10000,
        connectivity=4,
        neighborhoodSize=128
    )
    # post processing, merges segments based on spectral properties and size
    clusters = snic.select('clusters')
    clusters = merge_spectral(clusters, raw, THRESHOLD_SPECTRAL)
    clusters = merge_spectral(clusters, raw, THRESHOLD_SPECTRAL)
    clusters = merge_size(clusters, THRESHOLD_SIZE)
    return clusters

# ==========================================================
# 4. EXECUTE PIPELINE
# ==========================================================
def main():
    parser = argparse.ArgumentParser(description="Run SNIC Segmentation on GCS Image")
    parser.add_argument("--image", required=True, help="GCS URI of the input image")
    parser.add_argument("--asset-id", required=True, help="Base Asset ID for output")
    parser.add_argument("--scale", type=float, default=SCALE, help="Scale in meters")
    args = parser.parse_args()

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "akveg-map")
    ee.Initialize(project=project_id)

    raw_image = ee.Image.loadGeoTIFF(args.image)
    proj = raw_image.projection().getInfo()
    processing_region = raw_image.geometry()

    # loop through kernel and SNIC parameters
    for k in KERNEL_SIZES:
        for s in SNIC_SIZES:
            # run segmentation and name output
            segmented = run_segmentation(raw_image, k, s)
            s_padded = f"{s:02d}"
            params = f"kernel_{k}_size_{s_padded}"
            
            # Construct export name/ID
            export_asset_id = f"{args.asset_id}_SNIC_{params}"
            description = os.path.basename(export_asset_id)

            # export as GEE asset
            task = ee.batch.Export.image.toAsset(
                image=segmented,
                description=description,
                assetId=export_asset_id,
                region=processing_region,
                scale=args.scale,
                crs=proj['crs'],
                crsTransform=proj['transform'],
                maxPixels=1e13,
                pyramidingPolicy={'.default': 'mode'}
            )
            task.start()
            print(f"Started Task: {description} -> {export_asset_id}")

if __name__ == "__main__":
    main()