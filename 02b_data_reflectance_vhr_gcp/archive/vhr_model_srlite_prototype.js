var sas = ee.FeatureCollection("projects/akveg-map/assets/study_areas/AKVegMap_project_areas_merged_3338_v20250125"),
    mentasta = ee.FeatureCollection("projects/akveg-map/assets/study_areas/MentastaLake_MapDomain_3338");

var srCirViz = {bands: ['nir', 'red', 'green'], min:[0,0,0], max:[5000,2000,2000]},
    srRgbViz = {bands: ['red', 'green', 'blue'], min:[0,0,0], max:[2000,2000,2000]};

var crs = 'EPSG:3338';
var crsTransform_30m = [30,0,15,0,-30,15];

var exportVersion = 'v20250304';

var vhr = ee.ImageCollection('projects/akveg-map/assets/reflectance_vhr/ortho_toa_images')
  .map(function(img) {return img.rename('blue','green','red','nir')})
  .map(function(img) {
    var dateString = img.getString('yyyymmdd_hhmmss');
    var date = ee.Date.parse("yyyyMMdd_HHmmss", dateString);
    var doy = date.getRelative({
        unit:'day',
        inUnit:'year'})
        .add(1);
    var dataMask = img.select('blue').gte(0);
    var doyImg = ee.Image.constant(doy).int16().updateMask(dataMask).rename('doy');
    return img.addBands(doyImg);
  });
  
var vhr_cloud = ee.ImageCollection('projects/akveg-map/assets/reflectance_vhr/ortho_toa_images_cloud')
  .map(function(img) {return img.rename('cloud_ocm')});
var landsat_ccdc_sr = ee.ImageCollection('projects/akveg-map/assets/reflectance_vhr/landsat_ccdc_sr');

var snowDoysCcdcNdsi = ee.ImageCollection('projects/foreststructure/ABoVE/CCDC/CCDC_NDSI_SnowDoys').mosaic();
var lastSnowDoy_NDSI_p1 = snowDoysCcdcNdsi.select(['lastSnowDoy_NDSI_p1']);
var lastSnowDoy_NDSI_p4 = snowDoysCcdcNdsi.select(['lastSnowDoy_NDSI_p4']);
var firstSnowDoy_NDSI_p1 = snowDoysCcdcNdsi.select(['firstSnowDoy_NDSI_p1']);
var firstSnowDoy_NDSI_p4 = snowDoysCcdcNdsi.select(['firstSnowDoy_NDSI_p4']);

var lastSnowDoy = lastSnowDoy_NDSI_p1.max(60).unmask(60).rename('phenology_lastSnowDoy'),
 firstSnowDoy = firstSnowDoy_NDSI_p1.min(304).unmask(304).rename('phenology_firstSnowDoy'),
 snowFreeLength = firstSnowDoy.subtract(lastSnowDoy).rename('phenology_snowFreeDays');
var phenologyMetrics = lastSnowDoy.addBands(firstSnowDoy).addBands(snowFreeLength);

print(vhr, vhr_cloud, landsat_ccdc_sr);

var vhr_w_cloud = vhr.linkCollection({
  imageCollection: vhr_cloud,
  linkedBands: ['cloud_ocm'],
  matchPropertyName: 'yyyymmdd_hhmmss'});
  
print(vhr_w_cloud);

var vhr_w_cloud_ccdc = vhr_w_cloud.linkCollection({
  imageCollection: landsat_ccdc_sr,
  linkedBands: ['blue_ccdc','green_ccdc','red_ccdc','nir_ccdc','water_occurrence'],
  matchPropertyName: 'yyyymmdd_hhmmss'});
  
print(vhr_w_cloud_ccdc);

// var seasonal_doy_stack = ee.Image('users/mmacander/alaska_metrics/mcd43a4_061_ndvi_seasonal_doy_percentiles_v20250128');
// print(seasonal_doy_stack);

// seasonal_doy_stack = seasonal_doy_stack
//   .addBands(seasonal_doy_stack.select('doy_end_ndvi_p095_of_max').subtract(seasonal_doy_stack.select('doy_start_ndvi_p095_of_max')).int16().rename('n_days_ndvi_p095_of_max'))
//   .addBands(seasonal_doy_stack.select('doy_end_ndvi_p090_of_max').subtract(seasonal_doy_stack.select('doy_start_ndvi_p090_of_max')).int16().rename('n_days_ndvi_p090_of_max'))
//   .addBands(seasonal_doy_stack.select('doy_end_ndvi_p085_of_max').subtract(seasonal_doy_stack.select('doy_start_ndvi_p085_of_max')).int16().rename('n_days_ndvi_p085_of_max'))
//   .addBands(seasonal_doy_stack.select('doy_end_ndvi_p080_of_max').subtract(seasonal_doy_stack.select('doy_start_ndvi_p080_of_max')).int16().rename('n_days_ndvi_p080_of_max'))
//   .addBands(seasonal_doy_stack.select('doy_end_ndvi_p075_of_max').subtract(seasonal_doy_stack.select('doy_start_ndvi_p075_of_max')).int16().rename('n_days_ndvi_p075_of_max'));
  
// Map.addLayer(seasonal_doy_stack.unmask(0), {min: [136,197,213], max: [196,227,273], bands: ['doy_start_ndvi_p090_of_max','doy_max_ndvi','doy_end_ndvi_p090_of_max']}, 'seasonal_doy_stack', false);

// vhr_w_cloud = vhr_w_cloud.map(function(img) {
//   var dateString = img.getString('yyyymmdd_hhmmss');
//   var date = ee.Date.parse("yyyyMMdd_HHmmss", dateString);
//   var doy = date.getRelative({
//       unit:'day',
//       inUnit:'year'})
//       .add(1);
//   var dataMask = img.select('B0').gte(0);
//   var doyImg = ee.Image.constant(doy).int16().updateMask(dataMask).rename('doy');
//   var doys2peak = doyImg.subtract(seasonal_doy_stack.select('doy_max_ndvi')).rename('doys_to_max');
//   var doys2peak_negAbs = doys2peak.abs().multiply(-1).int16().rename('negAbs_doys_to_max');
//   img = img.addBands(doyImg).addBands(doys2peak).addBands(doys2peak_negAbs);
//   return img;
// });

var vhr_w_cloud_masked = vhr_w_cloud_ccdc.map(function(img) {
  var ocm_mask = img.select('cloud_ocm').unmask(0).not();
  var snow_mask = img.select('doy').add(14).gte(lastSnowDoy);
  var water_mask = img.select('water_occurrence').lte(50);
  var nirDiff_mask = img.select('nir').subtract(img.select('nir_ccdc')).abs().lte(500)
  return img.updateMask(ocm_mask).updateMask(snow_mask).updateMask(water_mask).updateMask(nirDiff_mask);
});//.limit(2);

vhr_w_cloud_masked = vhr_w_cloud_masked
  // .limit(2);
// Map.addLayer(vhr_w_cloud.qualityMosaic('negAbs_doys_to_max').unmask(0), {min:0, max:[5000,2000,2200], bands:['B3','B2','B1']});

// Map.addLayer(vhr_w_cloud_masked.mosaic().unmask(0), {min:0, max:[5000,2000,2200], bands:['B3','B2','B1']});
// Map.addLayer(vhr_w_cloud_masked.qualityMosaic('negAbs_doys_to_max').unmask(0), {min:0, max:[5000,2000,2200], bands:['B3','B2','B1']});
Map.addLayer(vhr_w_cloud_ccdc, {min:0, max:[5000,2000,2000], bands:['nir','red','green']}, 'input 2m before masking');
Map.addLayer(vhr_w_cloud_masked, {min:0, max:[5000,2000,2000], bands:['nir','red','green']}, 'input 2m');
Map.addLayer(vhr_w_cloud_masked, {min:0, max:[5000,2000,2000], bands:['nir_ccdc','red_ccdc','green_ccdc']}, 'input 30m ccdc sr');




var vhr_w_cloud_masked_corr = vhr_w_cloud_masked.map(corrLinFit_BGRN);
print('vhr_w_cloud_masked_corr', vhr_w_cloud_masked_corr);

Map.addLayer(vhr_w_cloud_masked_corr, srCirViz, 'corr', false);

// var corr_params = ee.FeatureCollection(vhr_w_cloud_masked_corr, 'swathFootprint').select([
var corr_params = ee.FeatureCollection(vhr_w_cloud_masked_corr).select([
  "yyyymmdd_hhmmss",
  "blue_offset", "blue_scale", "green_offset", "green_scale", 
  "red_offset", "red_scale", "nir_offset", "nir_scale", 
  "system:index", "system:time_start"], null, true);
print(corr_params);

var tableDescription = 'ortho_toa_images_correction_parameters_' + exportVersion;
Export.table.toDrive({
  collection: corr_params,  
  description: tableDescription,
  fileFormat: 'CSV',
  folder: '2025_akveg',
});
Export.table.toAsset({
  collection: corr_params,  
  description: tableDescription,
  assetId: 'projects/akveg-map/assets/reflectance_vhr/' + tableDescription,
  // folder: '2020_serdp',
});

Map.addLayer(ee.Image().byte().paint(sas.merge(mentasta), 1, 2), {palette:'yellow'}, 'study areas');

throw('stop');

// var crsTransform2m = [2,0,276210,0,-2,2276750];
// Export.image.toAsset({
//   image: dg_mulSwathsCorr.select('blue', 'green', 'red', 'nir').mosaic(),// 'projects/foreststructure/Alaska_Working/HRSI/fairbanks_wv23_20180527_20180603_mosaic_ms2m_').mosaic(),
//   description: "dg_corr_2m_" + exportVersion,
//   crsTransform: crsTransform2m,
//   region: sa,
//   // scale: 2,
//   assetId: "projects/foreststructure/Alaska_Working/HRSI/fairbanks_wv23_20180527_20180603_mosaic_ms2m_" + exportVersion,
//   crs: crs,
//   maxPixels: 1e12,
//   pyramidingPolicy: {'imageNum': 'mode'}
// });

function corrLinFit(vhr_image, landsat_image, band) {
  // var crs = landsat_image.projection().crs();
  // var crsTransform = landsat_image.projection().transform();
  var vhr_30m = vhr_image
    .reproject(crs, crsTransform_30m)
    .reduceResolution(ee.Reducer.mean(), true, 64);//changed from 512 to see if internal error solved
  // Map.addLayer(vhr_30m, dgCirViz, 'vhr_30m');
  // var sfdoyLandMask = sfdoy_land.lt(vhr_30m.select('doy').min(203)//204 is max sf_doy
  //   .subtract(14)) //subtract some days to account for interannual variability in snow cover
  //   .updateMask(vhr_30m.select('blue'))
  //   .selfMask().int16();
  // print('vhr_30m', vhr_30m);
  var vhr_30m_masked = vhr_30m  
    // .updateMask(vhr_image.select('digitized_cloud'))
    .updateMask(landsat_image.select('blue'));

  // Map.addLayer(vhr_30m_masked.select('blue'), {}, 'vhr_30m_mask_blue');
  var landsat_image_snowFreeLand = landsat_image
    .updateMask(vhr_30m_masked.select('blue'));
  // Map.addLayer(landsat_image_snowFreeLand, srCirViz, 'landsat_image_snowFreeLand');
  // print('landsat_image_snowFreeLand',landsat_image_snowFreeLand);
  var bands = vhr_30m_masked.select(band).rename(band + "_P")
    .addBands(landsat_image_snowFreeLand.select(band).rename(band + '_L'));
  // print('bands',bands);
  //////////////////////
  //Linear
  // var corrFit = bands.reduceRegion({
  //     reducer: ee.Reducer.linearFit(),
  //     geometry: ee.Geometry(vhr_image.geometry()), 
  //     scale: 30,
  //     maxPixels: 1e12
  // });
  // var scale = ee.Number(corrFit.get('scale'));
  // var offset = ee.Number(corrFit.get('offset'));
  
  ///////////////////////////
  //Robust. ToDo make a picker
  var robustCorrFit = ee.Image(1).rename('constant').addBands(bands)
    .reduceRegion({
      reducer: ee.Reducer.robustLinearRegression(2,1),
      geometry: ee.Geometry(vhr_image.geometry()), 
      scale: 30,
      maxPixels: 1e12
  });
  var coefList =ee.Array(robustCorrFit.get('coefficients')).toList();
  var offset = ee.Number(ee.List(coefList.get(0)).get(0)); // y-intercept
  var scale = ee.Number(ee.List(coefList.get(1)).get(0)); // slope
  // print(offset, scale);

  // print('offset',offset);
  var corr = vhr_image.select(band).multiply(scale).add(offset).int16();
  var corr_30m = vhr_30m.select(band).multiply(scale).add(offset).int16();
  // print('corr_30m',corr_30m);
  var corrDiff = landsat_image.select(band).subtract(corr_30m).int16()
    .rename(band+'_diff');
  corr = corr.addBands(corrDiff);
    // .addBands(sfdoyLandMask.rename('sfdoyLandMask_' + band));
  var keyScale = 'LandsatCalScale_'+band;
  var keyOffset = 'LandsatCalOffset_'+band;
  // return corr.setMulti({keyScale: scale, keyOffset: offset}).copyProperties(vhr_image);
  return corr.set(band + '_scale', scale, band + '_offset', offset).copyProperties(vhr_image, ['yyyymmdd_hhmmss', 'system:time_start','system:index']);//, 'image_num']);
}

function corrLinFit_BGRN(stacked_image) {
  var vhr_image = stacked_image.select('blue','green','red','nir');
  var landsat_image = stacked_image.select(['blue_ccdc','green_ccdc','red_ccdc','nir_ccdc'],['blue','green','red','nir']);
  
  var nirDiff_mask = stacked_image.select('nir').subtract(stacked_image.select('nir_ccdc')).abs().lte(1000)
  // var swath_dt = vhr_image.date();//.millis();
  // var swath_doy = vhr_image.date().getRelative('day','year').add(1);
  // var landsat_image = fitMap(swath_dt)
  //   .updateMask(waterMask)
  //   .updateMask(lastSnowDoy.subtract(10).lt(swath_doy))
  //   .updateMask(vhr_image.select('blue'));
  // Map.addLayer(landsat_image, srCirViz, 'landsat target', true);
  var blueCorr = ee.Image(corrLinFit(vhr_image, landsat_image, 'blue'));
  // print('blueCorr', blueCorr);
  var greenCorr = corrLinFit(vhr_image, landsat_image, 'green');
  // print('greenCorr', greenCorr);
  var redCorr = corrLinFit(vhr_image, landsat_image, 'red');
  var nirCorr = corrLinFit(vhr_image, landsat_image, 'nir');
  // var imageNum = vhr_image.select('imageNum');
  // print(test_img);
  // print(blueCorr);
  
  var corr = blueCorr
    .addBands(greenCorr).addBands(redCorr).addBands(nirCorr);
    // .addBands(imageNum);
    // .addBands(vhr_image.select('digitized_cloud', 'doy', 
    //                           'year', 'image_num', 'diff0731', 'diff0731_negAbs'));

  corr = corr.addBands(ee.Image(corr).select('blue_diff').abs()
              .add(ee.Image(corr).select('green_diff').abs())
              .add(ee.Image(corr).select('red_diff').abs())
              .add(ee.Image(corr).select('nir_diff').abs())
              .multiply(-1).rename('negAbsDiff').int16())
              .updateMask(corr.select('blue'));
  return ee.Image(corr.copyProperties(greenCorr).copyProperties(redCorr).copyProperties(nirCorr));
}

