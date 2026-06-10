# Sentinel 2 Composites
# Version 20230713d includes imagery inputs from 2019 through the end of the 2023 growing season

# Imagery is tiled in the 50km AKVEG tiles (5000x5000 pixels each at 10 m resolution) and stored in a Google Cloud Storage bucket (akveg-data/s2_sr_2019_2023_gMedian_v20240713d) as part of the akveg-map project. The data can be accessed as a mosaic within Google Earth Engine via as a cloud-backed image collection (https://developers.google.com/earth-engine/Earth_Engine_asset_from_cloud_geotiff)

# ## Version history
#
# ### v20240713d
# GEE snapshot: [https://code.earthengine.google.com/ecb8bb60b4985e1cd1a03865002c6992]
# GEE script path: [https://code.earthengine.google.com/?scriptPath=users%2Fmmacander%2Fakveg_map%3Asentinel_2%2Fs2_medians_v20240713d ]
#
# As of 2024-07-17, the lastest version of the Sentinel 2 reflectance composites in v20240713d. A description is below.
#
# Sentinel 2 Level 2A (surface reflectance) data ([https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED]) are available for Alaska and Canada from 2019 through the present. The product is produced by the European Space Agency (ESA) and incorporates both an atmospheric correction and an illumination correction (unlike Landsat Collection 2 surface reflectance, for example, which incorporates an atmospheric correction only). The DEM used for the illumination correction was changed during winter 2020-2021 to the Copernicus GLO-30 global DEM ([https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_DEM_GLO30]), and the more recent results based on GLO-30 appear to be improved overall and have fewer artifacts at abrupt terrain breaks compared to the earlier results. 
#
# Input data are first screened at the granule level, to include only images that meet criteria of 1) years between 2019 and 2023 inclusive; 2) day of year >= the first day of year when the maximum solar elevation is 40 degrees or higher; 3) day of year <= the last day of year when the maximum solar elevation is 25 degrees or lower; and 4) a granule 'cloudy pixel percentage' of 80% or less. For the day of year criteria, the thresholds are assigned at the level of the 50 km output tile.
#
# The images are then masked to exclude clouds, cloud shadow, snow, and other bad data. 1) Clouds and cloud shadow are masked based on the Cloud Score+ algorithm ([https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_CLOUD_SCORE_PLUS_V1_S2_HARMONIZED]), masking pixels where the 'cs' band < 0.6. 2) Snow and other bad data are masked based on the scene classification map ('SCL' band of the image), masking values of 1 (saturated or defective), 2 (dark area pixels), 3 (cloud shadow), and 11 (snow / ice). 3) For scenes where the Dynamic World ([https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1]) product was generated, i.e. any scene where the 'cloudy pixel percentage' was <= 35%, pixels where the labelled class was 9 (snow/ice) are also masked.
#
# After masking, the Sentinel 2 data were mosaicked based on date and orbit number, to flatten data from overlap areas that occur at the edges of MGRS tiles. Without this step, there would be duplicate data from the overlap areas. 
#
# 5 seasonal composites are generated from the quality-masked images, nominally representing spring, early summer, midsummer, late summer, and fall. Since snow-masking is applied, the spring and fall periods are intended to represent the snow-free portion of those periods. The seasons are defined based on an existing per-pixel analysis of the dates of snow-free Sentinel 2 imagery ([https://code.earthengine.google.com/6b223ec1a1419a7b8210900b23f3e4c3] or [https://code.earthengine.google.com/?scriptPath=users%2Fmmacander%2Fakveg_map%3Asentinel_2%2Fs2_v20230113_doys]) that included 2019–2022 imagery filtered and masked similarly to the rules above. Day of year percentiles were calculated for each pixel based on the dates of snow-free observations. The central dates of the composite periods were defined as follows: 1) spring = 5th percentile of the snow-free observation dates; 2) midsummer = July 31; 3) fall = 95th percentile of the snow-free observation dates; 4) early summer = 25% of the way between spring and midsummer; and 5) late summer = midway between midsummer and fall. 
#
# The composites were then calculated as the geometric median of observations within a time window around the central date of each season. For each season, both a narrow and wide time window were considered; if the number of quality-masked observations within the narrow time window was < 3, then the wide time window was used. If the number of quality-masked observations with the wide time window was < 3, then alternate seasonal windows were considered, as described below. The general assumption behind this approach was that the geometric median was not a robust metric with less than 3 observations, because if one of the the observations was an outlier then the result would be heavily influenced by the outlier. The exception was midsummer with a wide time window, for which only one quality-masked observation was required. This was to help ensure that every pixel had some reflectance estimate for each seasonal window (midsummer was a backup for each of the other seasonal windows). Generally, the minimum number of observations was easily achieved for the wide window in each seasonal period, except for snow-dominated areas (on or near glaciers and snow-fields) and some geographic regions with high cloud cover and low observation density (e.g. portions of the Aleutian Islands).
#
# TODO: Insert tables with composite windows (narrow and wide), including tier ID. Insert table with backup tiers.
#
# TODO: Consider using DOY analysis from the complete Landsat TM, ETM+, and OLI record (1984–present), excluding Landsat 7 ETM+ data collected after the SLC-off malfunction to avoid striping artifacts. And/or, the refined snow analysis based on the Sentinel 2 Dynamic World product.
#
# TODO: Consider restoring fire masking. Fire masking limited observations to pre- and/or post-fire imagery for pixels where fires occurred during the 2019-2023 window. Pre- and post-fire products can be produced later as separate tiled product, only processing tiles that intersect fire perimeters, and only for pixels within fire perimeter (could consider a buffer). In main composites, when combined with fallback tiers, fire masking was leading to some composites with mix of pre- and post-fire in different seasons and was contributing to high compute load.
#
# TODO: Consider selective use of a full growing season backup tier (e.g. ~May 1-October 31). It was computationally intensive and was only needed for a small number of pixels, mostly in permanent snowfields. Was contributing to very high computer and/or processing failures. Consider reviewing areas with limited data and running full season or something similar there (e.g. mid-Aleutians).
#
# ### v2024-03-11
# GEE snapshot: [https://code.earthengine.google.com/f7ccb6d08f9f201c2f09d6433719433e]
# GEE script path: [https://code.earthengine.google.com/?scriptPath=users%2Fmmacander%2Fakveg_map%3Asentinel_2%2Fs2_medians_v20240311]
#
# Prior version for portion of study area. Demonstrates much reduced snow contamination in early season composites compared to previous version. Also demonstrates partial fire masking, using fire polygons for 2019-2023 to mask input imagery that was acquired the year of or before a fire. So where a 2020 fire is mapped in the fire perimeter polygon data, only 2021-2023 data is included in the composites. This should make the composites represent the current condition (after the fire). Problems with this approach are that for training, we may prefer the pre-fire conditions. Also, fires in 2023 will have no image because it is all masked. The script currently falls back to a non-seasonal full snow-free season composite when there is insufficient data available but this is not desirable behavior for 2023 firescars.
#
# ### v2023-04-18
# GEE snapshot: [https://code.earthengine.google.com/4ab67b271cae54051b8d756d847c2a95]
# GEE script path: [https://code.earthengine.google.com/?scriptPath=users%2Fmmacander%2Fakveg_map%3Asentinel_2%2Fs2_medians_v20230418]
#
# Prior version for complete study area. Less robust snow masking. Only a single time window per composite period (no narrow and wide windows). No backstops to fill in composites periods. Partial fire masking.
#
# ## Visualization
# Visualize results after creating the Cloud GeoTiff Backed Earth Engine Assets with this viz script:
#
# [https://code.earthengine.google.com/?scriptPath=users%2Fmmacander%2Fakveg_map%3Asentinel_2%2Fs2_viz]
#

# ## Background on Cloud GeoTiff Backed Earth Engine Assets
#
# ***Note:*** *The REST API contains new and advanced features that may not be suitable for all users.  If you are new to Earth Engine, please get started with the [JavaScript guide](https://developers.google.com/earth-engine/guides/getstarted).*
#
# Earth Engine can load images from Cloud Optimized GeoTiffs (COGs) in Google Cloud Storage ([learn more](https://developers.google.com/earth-engine/guides/image_overview#images-from-cloud-geotiffs)).  This notebook demonstrates how to create Earth Engine assets backed by COGs.  An advantage of COG-backed assets is that the spatial and metadata fields of the image will be indexed at asset creation time, making the image more performant in collections.  (In contrast, an image created through `ee.Image.loadGeoTIFF` and put into a collection will require a read of the GeoTiff for filtering operations on the collection.)  A disadvantage of COG-backed assets is that they may be several times slower than standard assets when used in computations.
#
# To create a COG-backed asset, make a `POST` request to the Earth Engine `CreateAsset` endpoint.  As shown in the following, this request must be authorized to create an asset in your user folder.

import argparse
import logging
import os
import ee
try:
    from google.cloud import storage
except ImportError:
    print("Error: 'google-cloud-storage' is required. Install via: pip install google-cloud-storage")
    exit(1)
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def delete_assets_in_parallel(asset_list):
    """Deletes a list of assets using a ThreadPoolExecutor."""
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(ee.data.deleteAsset, asset['name']) for asset in asset_list]
        for future in futures:
            try:
                future.result()
            except Exception as e:
                logging.error(f"Delete failed: {e}")

def delete_collection_and_contents(asset_id):
    """
    Deletes an ImageCollection and all its contents (flat structure).
    """
    try:
        # Check if asset exists
        try:
            ee.data.getAsset(asset_id)
        except ee.EEException:
            logging.info(f"Asset {asset_id} does not exist. Skipping delete.")
            return

        logging.info(f"Scanning contents of {asset_id} for deletion...")
        
        # List assets with pagination
        all_assets = []
        page_token = None
        while True:
            params = {'parent': asset_id}
            if page_token:
                params['pageToken'] = page_token
            response = ee.data.listAssets(params)
            if 'assets' in response:
                all_assets.extend(response['assets'])
            page_token = response.get('nextPageToken')
            if not page_token:
                break
        
        if all_assets:
            logging.info(f"Deleting {len(all_assets)} child assets...")
            delete_assets_in_parallel(all_assets)
        
        # Delete the collection itself
        logging.info(f"Deleting collection {asset_id}...")
        ee.data.deleteAsset(asset_id)
        logging.info("Delete complete.")

    except Exception as e:
        logging.error(f"Error during collection delete: {e}")
        raise

def create_image_collection(asset_id):
    """Creates an empty ImageCollection."""
    logging.info(f"Creating ImageCollection {asset_id}...")
    try:
        ee.data.createAsset({'type': 'IMAGE_COLLECTION'}, asset_id)
        logging.info("Collection created.")
    except ee.EEException as e:
        logging.error(f"Failed to create collection: {e}")
        raise

def list_gcs_blobs(bucket_name, prefix):
    """Lists all TIF blobs in a GCS bucket/prefix."""
    logging.info(f"Listing files in gs://{bucket_name}/{prefix}...")
    storage_client = storage.Client()
    blobs = storage_client.list_blobs(bucket_name, prefix=prefix)
    
    tif_files = []
    for blob in blobs:
        if blob.name.endswith('.tif'):
            tif_files.append(f"gs://{bucket_name}/{blob.name}")
    
    logging.info(f"Found {len(tif_files)} TIF files.")
    return tif_files

def ingest_cogs(tif_list, collection_id):
    """Ingests list of GCS URIs into the GEE Collection."""
    logging.info(f"Starting ingestion of {len(tif_list)} assets...")
    
    for i, uri in enumerate(tif_list):
        filename = os.path.basename(uri)
        # Example filename: s2_sr_2019_2023_gMedian_AK050H60V18_all_v20240713d.tif
        asset_name = os.path.splitext(filename)[0]
        
        # Parse season from filename
        # Format: s2_sr_2019_2023_gMedian_TILE_SEASON_VERSION.tif
        parts = filename.split('_')
        if len(parts) > 6:
            season = parts[6]
        else:
            season = 'unknown'
            logging.warning(f"Could not parse season from {filename}, using 'unknown'")

        asset_id = f"{collection_id}/{asset_name}"
        
        request = {
            'type': 'IMAGE',
            'gcs_location': {
                'uris': [uri]
            },
            'properties': {
                'seasonName': season,
                'source_uri': uri
            },
            # Dates reflect the composite period (2019-2023)
            'startTime': '2019-01-01T00:00:00Z',
            'endTime': '2024-01-01T00:00:00Z',
        }
        
        try:
            # Log every 50 assets to reduce noise
            if i % 50 == 0:
                logging.info(f"[{i+1}/{len(tif_list)}] Creating asset {asset_id}...")
            ee.data.createAsset(request, asset_id)
        except ee.EEException as e:
            logging.error(f"Failed to create asset {asset_id}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Ingest Sentinel-2 Composites to GEE")
    parser.add_argument("--bucket", default="akveg-data", help="GCS Bucket Name")
    parser.add_argument("--prefix", default="s2_sr_2019_2023_gMedian_v20240713d", help="GCS Prefix (folder path)")
    parser.add_argument("--project", default="akveg-map", help="GEE Project ID")
    parser.add_argument("--collection", default="s2_sr_2019_2023_gMedian_v20240713d", help="GEE Collection Name (relative to project assets)")
    
    args = parser.parse_args()
    
    # Initialize EE
    try:
        ee.Initialize(project=args.project)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=args.project)
        
    full_collection_id = f"projects/{args.project}/assets/{args.collection}"
    
    # 1. Delete existing collection and contents
    delete_collection_and_contents(full_collection_id)
    
    # 2. Create fresh collection
    create_image_collection(full_collection_id)
    
    # 3. List files from GCS
    tifs = list_gcs_blobs(args.bucket, args.prefix)
    
    # 4. Ingest all files
    ingest_cogs(tifs, full_collection_id)

if __name__ == "__main__":
    main()