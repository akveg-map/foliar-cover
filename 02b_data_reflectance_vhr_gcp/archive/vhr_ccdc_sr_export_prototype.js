var temporalSegmentation = require('users/wiell/temporalSegmentation:temporalSegmentation'); // Load module

var crs_transform = [30.0, 0.0, 15.0,0.0, -30.0, 15.0]; //generic 30m with pixel centered on (0,0)
print(ee.ImageCollection("projects/CCDC/measures/v1").first(),
      ee.ImageCollection("projects/CCDC/measures/v1_overlap").first());

// var footprints = ee.FeatureCollection('users/mmacander/srlite/strips_v20220929')
// var footprints = ee.FeatureCollection('users/mmacander/srlite/footprints_evhr_ak_ahri_v20221004')
// var footprints = ee.FeatureCollection('users/mmacander/srlite/footprints_evhr_ak_ahri_b2_v20230807')
// var footprints = ee.FeatureCollection('users/mmacander/srlite/footprints_estimated_evhr_ak_ahri_b3_v20230807')
// .filter(ee.Filter.inList('region',['Alaska']));//.not()); 
var vhr_ic = ee.ImageCollection('projects/akveg-map/assets/reflectance_vhr/ortho_toa_images')
  .map(function(img) {return img.rename(['blue','green','red','nir'])})
  // Temporary filter to redo scenes after CCDC cut-off date
  .filterDate('2022-07-02', '2030-12-31');
// var footprints = ic.map(function(img) {
//   var fp = ee.Feature(img.geometry());
//   return fp.copyProperties(img)
// });

// footprints = ee.FeatureCollection(footprints);

print(vhr_ic);

//Split into batches of 500-1000, run each batch separately
//Wait for task list to be fully populated, then Run All
// var footprintList = footprints.toList(800,0).map(function(f) {return ee.Feature(f).getString('toaFile').slice(0,-8)});
var footprintList = vhr_ic.toList(100,0).map(function(f) {return ee.Feature(f).getString('yyyymmdd_hhmmss')});//.slice(0,-8)});
Map.addLayer(vhr_ic);

print(vhr_ic);

// throw('stop')
var result = footprintList.getInfo().map(extractCcdcFromVHR);

function extractCcdcFromVHR(yyyymmdd_hhmmss) {
  var vhr_img = vhr_ic.filterMetadata('yyyymmdd_hhmmss','equals', yyyymmdd_hhmmss).first()
  var footprint = ee.Feature(vhr_img.geometry());
  // Map.addLayer(footprint, {}, 'footprint');
  var footprint_mask = vhr_img.select('blue').mask();
  // var epsgCode = footprint.getNumber('epsg').int32().getInfo();
  var epsgCode = 3338;
  // var region = footprint.getString('region').getInfo();
  var region = 'alaska_ahri'
  var crs = 'EPSG:' + epsgCode;//.getInfo();
  // print(crs);

  //Bounding box of footprint in target CRS
  var clipper = footprint.geometry().bounds(1, crs);

  //Remove -toa.ntf
  // var fileNoExt = ee.String(toaFile).slice(0,-8);
  // var fileNoExt = region + '_' + toaFile;
  var fileNoExt = 'ccdc_'+yyyymmdd_hhmmss;
  var ccdc = ee.ImageCollection([
      ee.ImageCollection("projects/CCDC/measures/v1").mosaic(),
      ee.ImageCollection("projects/CCDC/measures/v1_overlap").mosaic()
  ]).mosaic();
  
  var segments = temporalSegmentation.Segments(ccdc,1); // Create temporal segments
  
  var targetDate = ee.Date.parse("yyyyMMdd_HHmmss", yyyymmdd_hhmmss);
  var year = targetDate.get('year');
  var mm = targetDate.get('month');
  var dd = targetDate.get('day');
  
  var targetDate_20220701 = ee.Date.fromYMD(2022, 7, 1);
  // var targetDate_20230101 = ee.Date.fromYMD(2023, 1, 1);
  // var targetDate_2022 = ee.Date.fromYMD(2022, mm, dd);
  var targetDate_2021 = ee.Date.fromYMD(2021, mm, dd);
  targetDate = ee.Date(ee.Algorithms.If(
    targetDate.millis().gt(targetDate_20220701.millis()), 
    targetDate_2021, 
    targetDate
    // ee.Algorithms.If(
    //   targetDate.millis().gt(targetDate_20220701.millis()), 
    //   targetDate_2021,
    //   targetDate
  ));
  // var targetDate = ee.Date.fromYMD(footprint.getNumber('year'),footprint.getNumber('month'),footprint.getNumber('day'))
  print(yyyymmdd_hhmmss, targetDate);
  
  var segment = segments.findByDate(targetDate);
  var ccdcTarget = segment.slice({date: targetDate, harmonics: 3, extrapolateMaxDays: 0});//, extrapolateMaxDays: 90});
  // print(ccdcTarget);
  
  //Code to generate composite from Landsat date closest to target date
  // var stack_withDateDiff = ccdc_input.map(function(img) {
  //   var mask = img.select('blue').mask();
  //   var dateDiff = img.date().difference(targetDate, 'days').float();
  //   var negAbsDateDiff = dateDiff.abs().multiply(-1).float();
  //   img = img
  //     .addBands(ee.Image(dateDiff).rename('dateDiff').float())
  //     .addBands(ee.Image(negAbsDateDiff).rename('negAbsDateDiff').float());
  //   return img.updateMask(mask);
  // });
  // print(stack_withDateDiff.limit(10));
  
  // var landsatClosestDate = stack_withDateDiff.qualityMosaic('negAbsDateDiff')
  //   .regexpRename('$', '_nearestDate');
  
  var waterOccurrence = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('occurrence').rename('water_occurrence').unmask(0);
  
  var exportResults = ccdcTarget.select(['BLUE','GREEN','RED','NIR'],['blue','green','red','nir']).regexpRename('$', '_ccdc')
    // .addBands(landsatClosestDate.select('blue_nearestDate','green_nearestDate','red_nearestDate','nir_nearestDate'))
    .multiply(10000)
    .clamp(-1000,16000)
    // .addBands(landsatClosestDate.select('dateDiff_nearestDate'))
    .addBands(waterOccurrence)
    .updateMask(footprint_mask);
  // print(exportResults);
  // Map.addLayer(exportResults.clip(clipper), {bands: ['nir_ccdc','red_ccdc','green_ccdc'], min:0, max:[5000,2000,2000]}, 'ccdc '+yyyymmdd_hhmmss);
  
  // var exportName = ee.String(fileNoExt).cat(ee.String('-ccdc'))//.getInfo()
  var exportName = fileNoExt;// + '-ccdc';
  
  // Export.image.toDrive({
  //   image: exportResults
  //     // .setDefaultProjection(crs, crs_transform)
  //     // .resample('bicubic')
  //     .unmask(-9999)
  //     .int16(),//.select('blue','green','red','nir'),
  //   // description: exportName.slice(0,60).getInfo(), //work-around for task length issue
  //   description: exportName,
  //   // fileNamePrefix: exportName.getInfo(),
  //   fileNamePrefix: exportName,
  //   folder: '2025_srlite',
  //   // region: footprint.geometry(),
  //   region: clipper,
  //   // crs: crs.getInfo(),
  //   crs: crs,
  //   crsTransform: crs_transform,
  //   formatOptions: {cloudOptimized: true, noData: -9999},
  // });

  Export.image.toCloudStorage({
    image: exportResults
       // .setDefaultProjection(crs, crs_transform)
      // .resample('bicubic')
      .unmask(-9999)
      .int16(),//.select('blue','green','red','nir'),
    description: 'gcp_'+exportName,
    bucket: 'akveg-data',
    fileNamePrefix: 'vhr/landsat_ccdc_sr/'+exportName,
    //  dimensions:,
    region: clipper,
    // crs: crs.getInfo(),
    crs: crs,
    crsTransform: crs_transform,
    formatOptions: {cloudOptimized: true, noData: -9999},
    //  maxPixels:,
    //  shardSize:,
    //  fileDimensions:,
    //  skipEmptyTiles:,
    //  fileFormat:,
  //  priority:,
  });
  // print(exportName);
  // Map.addLayer(exportResults.clip(clipper), {bands: 'water_occurrence', min:0, max:100}, 'JRC water occurrence');
  // Map.addLayer(exportResults.clip(clipper), visParamsCIR_nearestDate, 'nearestDate');
  // Map.addLayer(exportResults.clip(clipper), visParamsCIR_ccdc, 'ccdc');
  return ccdcTarget;  
}
