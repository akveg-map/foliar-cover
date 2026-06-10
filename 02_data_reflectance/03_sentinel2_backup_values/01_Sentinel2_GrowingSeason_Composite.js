/* -*- coding: utf-8 -*-
---------------------------------------------------------------------------
Create median midsummer composite
Author: Timm Nawrocki, Alaska Center for Conservation Science
Last Updated: 2024-07-24
Usage: Must be executed from the Google Earth Engine code editor.
Description: "Create median midsummer composite" creates a midsummer composite for years 2019-2023 from the S2 harmonized surface reflectance Level 2A collection.
---------------------------------------------------------------------------*/

// 1. INITIALIZE

// Load covariates
var area_feature = ee.FeatureCollection('projects/akveg-map/assets/regions/AlaskaYukon_MapDomain_3338_v20230330');
var elevation_image = ee.Image('projects/akveg-map/assets/covariates_v20240711/Elevation_10m_3338').rename(['elevation']);

// Define projection
var projection = elevation_image.select('elevation').projection().getInfo();
print(projection)


// Define properties
var start_year = 2019
var end_year = 2023
var start_month = 5
var end_month = 10
var cloud_threshold = 40

// 2. DEFINE FUNCTIONS

// Define a function to mask image edges
function mask_edges(image) {
  var mask = image.select('B8A').mask().updateMask(image.select('B9').mask());
  return image.updateMask(mask);
}

// Define a function to mask clouds using cloud probability
function mask_cloud_probability(image) {
  var clouds = ee.Image(image.get('cloud_mask')).select('probability');
  var mask = clouds.lt(cloud_threshold);
  return image.updateMask(mask);
}

// Define a function to mask clouds and cirrus using QA band
function mask_cloud_cirrus(image) {
	var qa = image.select('QA60');
	// Bits 10 and 11 are clouds and cirrus, respectively.
	var cloud_bit_mask = 1 << 10;
	var cirrus_bit_mask = 1 << 11;
	//Both flags should be set to zero, indicating clear conditions.
	var mask = qa.bitwiseAnd(cloud_bit_mask).eq(0)
		.and(qa.bitwiseAnd(cirrus_bit_mask).eq(0));
	return image.updateMask(mask);
}

// Define a function for NGRDI calculation.
function add_NGRDI(image) {
  // Assign variables to the red and green Sentinel-2 bands.
  var red = image.select('B4');
  var green = image.select('B3');
  //Compute the Enhanced Vegetation Index-2 (EVI2).
  var ngrdi_calc = green.subtract(red)
    .divide(green.add(red))
    .multiply(1000)
    .rename('NGRDI');
  // Return the masked image with an NGRDI band.
  return image.addBands(ngrdi_calc);
}

// Define a function for NBR calculation.
function add_NBR(image) {
  //Compute the Normalized Burn Ratio (NBR).
  var nbr_calc = image.normalizedDifference(['B8', 'B12'])
    .multiply(1000)
    .rename('NBR');
  // Return the masked image with an NBR band.
  return image.addBands(nbr_calc);
}

// Define a function for NDMI calculation.
function add_NDMI(image) {
  //Compute the Normalized Difference Moisture Index (NDMI).
  var ndmi_calc = image.normalizedDifference(['B8', 'B11'])
    .multiply(1000)
    .rename('NDMI');
  // Return the masked image with an NDMI band.
  return image.addBands(ndmi_calc);
}

// Define a function for NDSI calculation.
function add_NDSI(image) {
  //Compute the Normalized Difference Snow Index (NDSI).
  var ndsi_calc = image.normalizedDifference(['B3', 'B11'])
    .multiply(1000)
    .rename('NDSI');
  // Return the masked image with an NDSI band.
  return image.addBands(ndsi_calc);
}

// Define a function for NDVI calculation.
function add_NDVI(image) {
  //Compute the Normalized Difference Vegetation Index (NDVI).
  var ndvi_calc = image.normalizedDifference(['B8', 'B4'])
    .multiply(1000)
    .rename('NDVI');
  // Return the masked image with an NDVI band.
  return image.addBands(ndvi_calc);
}

// Define a function for NDWI calculation.
function add_NDWI(image) {
  //Compute the Normalized Difference Water Index (NDWI).
  var ndwi_calc = image.normalizedDifference(['B3', 'B8'])
    .multiply(1000)
    .rename('NDWI');
  // Return the masked image with an NDWI band.
  return image.addBands(ndwi_calc);
}

// 3. CREATE CLOUD-REDUCED IMAGE COLLECTION

// Define select spectral bands.
var bands = ['B2',
            'B3',
            'B4',
            'B5',
            'B6',
            'B7',
            'B8',
            'B8A',
            'B11',
            'B12',
            'NBR',
            'NGRDI',
            'NDMI',
            'NDSI',
            'NDVI',
            'NDWI']

// Import Sentinel 2 Cloud Probability
var s2_cloud = ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
  .filterBounds(area_feature)
  .filter(ee.Filter.calendarRange(start_year, end_year, 'year'))
  .filter(ee.Filter.calendarRange(start_month, end_month, 'month'));

// Import Sentinel-2 Level 2A Data
var s2 = ee.ImageCollection('COPERNICUS/S2_HARMONIZED')
  .filterBounds(area_feature)
  .filter(ee.Filter.calendarRange(start_year, end_year, 'year'))
  .filter(ee.Filter.calendarRange(start_month, end_month, 'month'))
  .map(mask_edges);
var s2_sr = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(area_feature)
  .filter(ee.Filter.calendarRange(start_year, end_year, 'year'))
  .filter(ee.Filter.calendarRange(start_month, end_month, 'month'))
  .map(mask_edges);

// Join imagery and cloud probability datasets
var s2_join = ee.Join.saveFirst('cloud_mask').apply({
  primary: s2,
  secondary: s2_cloud,
  condition:
      ee.Filter.equals({leftField: 'system:index', rightField: 'system:index'})
});
var s2sr_join = ee.Join.saveFirst('cloud_mask').apply({
  primary: s2_sr,
  secondary: s2_cloud,
  condition:
      ee.Filter.equals({leftField: 'system:index', rightField: 'system:index'})
});

// Mask the Sentinel-2 imagery
var s2_masked = ee.ImageCollection(s2_join)
  .map(mask_cloud_probability)
  .map(mask_cloud_cirrus)
  .map(add_NBR)
  .map(add_NGRDI)
  .map(add_NDMI)
  .map(add_NDSI)
  .map(add_NDVI)
  .map(add_NDWI)
  .select(bands);
var s2sr_masked = ee.ImageCollection(s2sr_join)
  .map(mask_cloud_probability)
  .map(mask_cloud_cirrus)
  .map(add_NBR)
  .map(add_NGRDI)
  .map(add_NDMI)
  .map(add_NDSI)
  .map(add_NDVI)
  .map(add_NDWI)
  .select(bands);

// 4. CREATE MEDIAN COMPOSITES

// Filter growing season image collection.
var filter_summer = ee.Filter.or(
  ee.Filter.date('2019-06-10', '2019-08-20'),
  ee.Filter.date('2020-06-10', '2020-08-20'),
  ee.Filter.date('2021-06-10', '2021-08-20'),
  ee.Filter.date('2022-06-10', '2022-08-20'),
  ee.Filter.date('2023-06-10', '2023-08-20'));
var collection_summer = s2sr_masked.filter(filter_summer);

// Create median composite
var median_summer = collection_summer.median()
  .toInt16();

// Export cloud-optimized geotiff to storage
Export.image.toCloudStorage({
  image: median_summer,
  description: 'median_summer_2019_2023',
  bucket: 'akveg-data',
  fileNamePrefix: 's2_sr_2019_2023_median_v20240724/Sent2_Midsummer_2019_2023_10m_3338.tif',
  crs: projection.crs,
  crsTransform: projection.transform,
  region: area_feature,
  fileFormat: 'GeoTIFF',
  formatOptions: {
    cloudOptimized: true
  },
  maxPixels: 1e13
});