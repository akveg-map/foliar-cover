# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Export covariate rasters
# Author: Timm Nawrocki
# Last Updated: 2026-04-12
# Usage: Must be executed in a Python 3.12+ installation with authentication to Google Earth Engine.
# Description: "Export covariate rasters" compiles covariate rasters and exports them in prediction tile grid for running the prediction step outside of Google Earth Engine.
# ---------------------------------------------------------------------------

# Import packages
import ee
from google.cloud import storage

#### SET UP ENVIRONMENT
####____________________________________________________

# Define paths
ee_project = 'akveg-map'
storage_bucket = 'akveg-data'
storage_prefix = 'foliar_cover_v2p1'

# Authenticate with Earth Engine
print('Requesting information from server...')
ee.Authenticate()
ee.Initialize(project=ee_project)

# Initialize GCS Client
storage_client = storage.Client()

# Define asset path
asset_path = f'projects/{ee_project}/assets'

# Define export areas
grid_path = 'projects/akveg-map/assets/regions/AlaskaYukon_MapTiles_v2p1_3338'
export_grid = ee.FeatureCollection(grid_path)

# Define covariate paths
covariate_path_v2 = f'{asset_path}/covariates_v20240711/'
covariate_path_v2p1 = f'{asset_path}/covariates_v20260118/'
sent1_path = f'{asset_path}/s1_2022_v20230326'
sent2_seasonal_path = f'{asset_path}/s2_sr_2019_2023_gMedian_v20240713d'
sent2_backup_path = f'{asset_path}/s2_sr_2019_2023_median_midsummer_v20240724'

#### DEFINE FUNCTIONS
####____________________________________________________

# Define function to check if a file exists in GCS
def gcs_blob_exists(gcs_uri):
    bucket_name = gcs_uri.split('/')[2]
    blob_name = '/'.join(gcs_uri.split('/')[3:])
    bucket = storage_client.bucket(bucket_name)
    return bucket.blob(blob_name).exists()

#### PREPARE STATIC ENVIRONMENTAL COVARIATES
####____________________________________________________

# Create multiband covariate image
covariate_image = ee.Image(covariate_path_v2 + 'CoastDist_10m_3338').rename('coast') \
  .addBands(ee.Image(covariate_path_v2 + 'Elevation_10m_3338').rename('elevation')) \
  .addBands(ee.Image(covariate_path_v2 + 'Exposure_10m_3338').rename('exposure')) \
  .addBands(ee.Image(covariate_path_v2 + 'HeatLoad_10m_3338').rename('heatload')) \
  .addBands(ee.Image(covariate_path_v2 + 'Position_10m_3338').rename('position')) \
  .addBands(ee.Image(covariate_path_v2 + 'RadiationAspect_10m_3338').rename('aspect')) \
  .addBands(ee.Image(covariate_path_v2 + 'Relief_10m_3338').rename('relief')) \
  .addBands(ee.Image(covariate_path_v2 + 'RiverDist_10m_3338').rename('river')) \
  .addBands(ee.Image(covariate_path_v2 + 'Roughness_10m_3338').rename('roughness')) \
  .addBands(ee.Image(covariate_path_v2 + 'Slope_10m_3338').rename('slope')) \
  .addBands(ee.Image(covariate_path_v2 + 'StreamDist_10m_3338').rename('stream')) \
  .addBands(ee.Image(covariate_path_v2 + 'Wetness_10m_3338').rename('wetness')) \
  .addBands(ee.Image(covariate_path_v2p1 + 'JanuaryMinimum_2006_2015_10m_3338').rename('january')) \
  .addBands(ee.Image(covariate_path_v2p1 + 'SummerWarmth_2006_2015_10m_3338').rename('summer')) \
  .addBands(ee.Image(covariate_path_v2p1 + 'Precipitation_2006_2015_10m_3338').rename('precip'))

#### PREPARE SENTINEL-1 COVARIATES
####____________________________________________________

# Load Sentinel-1 collection
s1_composite_coll = ee.ImageCollection(sent1_path)

# Update mask using the nodata value
s1_composite_coll = s1_composite_coll.map(lambda img: img.updateMask(img.neq(-32768)))

# Mosaic the Sentinel-1 images
s1_composite = s1_composite_coll.mosaic()

# Rename ascending bands
s1_composite_asc = s1_composite \
    .select(['VH_p50_grow_asc', 'VH_p50_fall_asc', 'VH_p50_froz_asc', 'VV_p50_grow_asc', 'VV_p50_fall_asc', 'VV_p50_froz_asc']) \
    .rename(['s1_1_vha', 's1_2_vha', 's1_3_vha', 's1_1_vva', 's1_2_vva', 's1_3_vva'])

# Rename descending bands
s1_composite_desc = s1_composite \
    .select(['VH_p50_grow_desc', 'VH_p50_fall_desc', 'VH_p50_froz_desc', 'VV_p50_grow_desc', 'VV_p50_fall_desc', 'VV_p50_froz_desc']) \
    .rename(['s1_1_vhd', 's1_2_vhd', 's1_3_vhd', 's1_1_vvd', 's1_2_vvd', 's1_3_vvd'])

# Fill in missing ascending data with descending data
s1_composite_asc_filled = ee.ImageCollection([
    s1_composite_desc.rename(['s1_1_vha', 's1_2_vha', 's1_3_vha', 's1_1_vva', 's1_2_vva', 's1_3_vva']),
    s1_composite_asc
]).mosaic()

# Fill in missing descending data with ascending data
s1_composite_desc_filled = ee.ImageCollection([
    s1_composite_asc.rename(['s1_1_vhd', 's1_2_vhd', 's1_3_vhd', 's1_1_vvd', 's1_2_vvd', 's1_3_vvd']),
    s1_composite_desc
]).mosaic()

# Create final image
s1_final = s1_composite_asc_filled.addBands(s1_composite_desc_filled)

#### PREPARE SENTINEL-2 COVARIATES
####____________________________________________________

# Define a function to add spectral indices
def add_s2_indices(image):
    nbr = image.normalizedDifference(['s2_nir', 's2_swir2']) \
        .multiply(10000).clamp(-10000, 10000).int16().rename('s2_nbr')
    ngrdi = image.normalizedDifference(['s2_green', 's2_red']) \
        .multiply(10000).clamp(-10000, 10000).int16().rename('s2_ngrdi')
    ndmi = image.normalizedDifference(['s2_nir', 's2_swir1']) \
        .multiply(10000).clamp(-10000, 10000).int16().rename('s2_ndmi')
    ndsi = image.normalizedDifference(['s2_green', 's2_swir1']) \
        .multiply(10000).clamp(-10000, 10000).int16().rename('s2_ndsi')
    ndvi = image.normalizedDifference(['s2_nir', 's2_red']) \
        .multiply(10000).clamp(-10000, 10000).int16().rename('s2_ndvi')
    ndwi = image.normalizedDifference(['s2_green', 's2_nir']) \
        .multiply(10000).clamp(-10000, 10000).int16().rename('s2_ndwi')
    return image.addBands([nbr, ngrdi, ndmi, ndsi, ndvi, ndwi])

# Load Sentinel-2 geometric median image collection
s2_geommedian = ee.ImageCollection(sent2_seasonal_path) \
    .mosaic() \
    .regexpRename('rededge', 'redge')

# Load Sentinel-2 growing season median image collection (used as backup images for missing data)
s2_backup = ee.ImageCollection(sent2_backup_path) \
    .mosaic() \
    .select(['B2', 'B3', 'B4', 'B5', 'B6', 'B7',
             'B8', 'B8A', 'B11', 'B12']) \
    .rename(['s2_blue', 's2_green', 's2_red', 's2_redge1', 's2_redge2',
             's2_redge3', 's2_nir', 's2_redge4', 's2_swir1', 's2_swir2']) \
    .int16()

# Identify reflectance bands (as opposed to metadata bands)
s2_reflectance_band_names = s2_geommedian.bandNames().filter(
    ee.Filter.And(
        ee.Filter.stringEndsWith('item', '_n').Not(),
        ee.Filter.stringEndsWith('item', '_tier').Not()
    )
)

# Select reflectance bands
s2_geommedian = s2_geommedian.select(s2_reflectance_band_names).int16()

# Process green-up composite (season 1)
s2_1 = ee.ImageCollection([
    s2_backup,
    s2_geommedian.select('^s2_seas1spring_.*')
      .regexpRename('_seas1spring_', '_')
      .int16()
]).mosaic()
s2_1 = add_s2_indices(s2_1).regexpRename('^s2_', 's2_1_')

# Process early summer composite (season 2)
s2_2 = ee.ImageCollection([
    s2_backup,
    s2_geommedian.select('^s2_seas2earlySummer_.*')
      .regexpRename('_seas2earlySummer_', '_')
      .int16()
]).mosaic()
s2_2 = add_s2_indices(s2_2).regexpRename('^s2_', 's2_2_')

# Process midsummer composite (season 3)
s2_3 = ee.ImageCollection([
    s2_backup,
    s2_geommedian.select('^s2_seas3midSummer_.*')
      .regexpRename('_seas3midSummer_', '_')
      .int16()
]).mosaic()
s2_3 = add_s2_indices(s2_3).regexpRename('^s2_', 's2_3_')

# Process late summer composite (season 4)
s2_4 = ee.ImageCollection([
    s2_backup,
    s2_geommedian.select('^s2_seas4lateSummer_.*')
      .regexpRename('_seas4lateSummer_', '_')
      .int16()
]).mosaic()
s2_4 = add_s2_indices(s2_4).regexpRename('^s2_', 's2_4_')

# Process senescence composite (season 5)
s2_5 = ee.ImageCollection([
    s2_backup,
    s2_geommedian.select('^s2_seas5fall_.*')
      .regexpRename('_seas5fall_', '_')
      .int16()
]).mosaic()
s2_5 = add_s2_indices(s2_5).regexpRename('^s2_', 's2_5_')

# Merge seasonal composites
s2_final = s2_1 \
    .addBands(s2_2) \
    .addBands(s2_3) \
    .addBands(s2_4) \
    .addBands(s2_5)

#### EXPORT COVARIATE RASTERS
####____________________________________________________

# Create image collection
covariate_image = covariate_image \
    .addBands(s1_final) \
    .addBands(s2_final) \
    .int16()

# Get a list of all grid codes to iteratively export
print('Fetching grid codes from grid feature collection...')
grid_codes = export_grid.aggregate_array('grid_code').getInfo()

# Filter grid list to a subset of grids (for testing purposes, comment line below for full export)
#target_grids = ['AK010H209V007']
#grid_codes = [code for code in grid_codes if code in target_grids]
grid_codes = grid_codes[0:1000]

# Loop through each grid code to submit a unique task
print(f'Found {len(grid_codes)} tiles to process.')
for grid_code in grid_codes:
    # Filter the feature collection to the specific grid code
    tile_feature = ee.Feature(export_grid.filter(ee.Filter.eq('grid_code', grid_code)).first())

    # Buffer the geometry by 20 meters
    export_geometry = tile_feature.geometry().buffer(20)

    # Define unique names for the task and output file
    task_description = f'covariates_{grid_code}'
    file_name = f'{storage_prefix}/rasters_covariates/{grid_code}_10m_3338'

    # Export grid if it does not already exist on GCS
    if not gcs_blob_exists(f'gs://{storage_bucket}/{file_name}'):
        # Define export parameters and start the task
        export_task = ee.batch.Export.image.toCloudStorage(**{
            'image': covariate_image,
            'description': task_description,
            'bucket': storage_bucket,
            'fileNamePrefix': file_name,
            'region': export_geometry,
            'scale': 10,
            'crs': 'EPSG:3338',
            'maxPixels': 1e13,
            'formatOptions': {
                'cloudOptimized': False,
                'noData': -32768
            }
        })

        # Initiate task
        export_task.start()
        print(f'Submitted task for {grid_code}.')
    else:
        print(f'{grid_code} already exists.')

print('All export tasks have been successfully submitted to Earth Engine.')
