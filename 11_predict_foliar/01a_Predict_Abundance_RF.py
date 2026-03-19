# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Predict abundance for Random Forest model
# Author: Timm Nawrocki, Matt Macander
# Last Updated: 2026-02-26
# Usage: Must be executed in a Python 3.12+ installation with authentication to Google Earth Engine.
# Description: "Predict abundance for Random Forest model" prepares covariates and initiates a prediction task in Google Earth Engine for classifier and regressor assets trained through Random Forest (scikit-learn).
# ---------------------------------------------------------------------------

# Define model targets
group = 'halgra'
version_date = '20260212'
presence_threshold = 3

# Import packages
import ee
import os

#### SET UP ENVIRONMENT
####____________________________________________________

# Define paths
ee_project = 'akveg-map'
storage_bucket = 'akveg-data'
storage_prefix = 'foliar_cover_v2p1'

# Define inputs
drive = 'C:/'
root_folder = 'ACCS_Work/Projects/VegetationEcology/AKVEG_Map/Data'
threshold_input = os.path.join(drive, root_folder,
                               f'Data_Output/model_results/version_{version_date}/{group}',
                               f'{group}_threshold_final.txt')

# Read threshold
threshold_reader = open(threshold_input, "r")
classifier_threshold = float(threshold_reader.readlines()[0])
threshold_reader.close()
print(f'Classifier threshold is: {classifier_threshold}')

# Authenticate with Earth Engine
print('Requesting information from server...')
ee.Authenticate()
ee.Initialize(project=ee_project)

# Define asset path
asset_path = f'projects/{ee_project}/assets'

# Define area of interest
test_area = ee.Image(f'{asset_path}/navy_arctic/IcyCape_CIR_0p5m_3338')

# Define covariate paths
covariate_path_v2 = f'{asset_path}/covariates_v20240711/'
covariate_path_v2p1 = f'{asset_path}/covariates_v20260118/'
sent1_path = f'{asset_path}/s1_2022_v20230326'
sent2_seasonal_path = f'{asset_path}/s2_sr_2019_2023_gMedian_v20240713d'
sent2_backup_path = f'{asset_path}/s2_sr_2019_2023_median_midsummer_v20240724'
dw_path = f'{asset_path}/dynamic_world_metrics/s2_dw_percentages_56789_v20250414'
alphaearth_path = 'GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL'

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

#### PREPARE DYNAMIC WORLD COVARIATES
####____________________________________________________

dynamic_world = ee.ImageCollection(dw_path) \
    .mosaic() \
    .select(['pct_nonsnow_water', 'pct_nonsnow_flooded_vegetation', 'pct_nonsnow_bare', 'pct_snow']) \
    .rename(['dw_water_pct', 'dw_flooded_pct', 'dw_bare_pct', 'dw_snow_pct']) \
    .int16()

#### PREPARE ALPHAEARTH COVARIATES
####____________________________________________________

embeddings = ee.ImageCollection(alphaearth_path) \
    .filterDate('2023-01-01', '2023-12-31') \
    .mosaic()

#### TRAIN AND EXPORT FOLIAR COVER MAP
####____________________________________________________

# Create image collection
covariate_image = covariate_image \
    .addBands(s1_final) \
    .addBands(s2_final) \
    .addBands(embeddings)

# Load the classifier and regressor
classifier_table = ee.FeatureCollection(f'{asset_path}/models/foliar_cover/{group}_classifier')
regressor_table = ee.FeatureCollection(f'{asset_path}/models/foliar_cover/{group}_regressor')

# Decode decision tree strings from the # placeholder into proper multi-line format
classifier_strings = classifier_table.sort('tree_index').aggregate_array('tree') \
    .map(lambda s: ee.String(s).replace('#', '\n', 'g'))

regressor_strings = regressor_table.sort('tree_index').aggregate_array('tree') \
    .map(lambda s: ee.String(s).replace('#', '\n', 'g'))

# Initialize the models
classifier = ee.Classifier.decisionTreeEnsemble(classifier_strings).setOutputMode('REGRESSION')
regressor = ee.Classifier.decisionTreeEnsemble(regressor_strings).setOutputMode('REGRESSION')

# Predict the outputs
probability_image = covariate_image.classify(classifier).rename(group)
foliar_raw = covariate_image.classify(regressor)

# Round the prediction to the nearest integer
foliar_rounded = foliar_raw.round()

# Set foliar cover to 0 based on thresholds
foliar_image = foliar_rounded.where(probability_image.lt(classifier_threshold), 0) \
                         .where(foliar_rounded.lt(presence_threshold), 0) \
                         .rename(f'{group}_cover')
print(f'Masked Foliar Image calculated for {group}.')

#### EXPORT TO CLOUD STORAGE
####____________________________________________________

# Unmask the empty pixels to -127, then cast to a signed 8-bit integer
foliar_export = foliar_image.unmask(-127).int8()

# Define export parameters and start the task
export_task = ee.batch.Export.image.toCloudStorage(**{
    'image': foliar_export,
    'description': f'IcyCape_{group}',
    'bucket': storage_bucket,
    'fileNamePrefix': f'{storage_prefix}/IcyCape_{group}_10m_3338',
    'region': test_area.geometry(),
    'scale': 10,
    'crs': 'EPSG:3338',
    'maxPixels': 1e13,
    #'tileScale': 16, UNCOMMENT FOR FULL EXTENT EXPORTS
    'formatOptions': {
        'cloudOptimized': True,
        'noData': -127
    }
})

export_task.start()
print(f'Export task for {group} successfully started! Check your GEE Task Manager or Cloud Storage.')
