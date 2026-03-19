// From https://code.earthengine.google.com/?scriptPath=users%2Fmmacander%2Fanwr%3Asegmentation%2Fsnic_201911_wMerge

var transform30m = [30,0,276210,0,-30,2276750],
    transform08m = [ 8,0,276210,0, -8,2276750],
    transform06m = [ 6,0,276210,0, -6,2276750],
    transform05m = [ 5,0,276210,0, -5,2276750],
    transform04m = [ 4,0,276210,0, -4,2276750],
    transform02m = [ 2,0,276210,0, -2,2276750];
var anwr_acp = ee.FeatureCollection("users/mmacander/ANWR/base_layers/ANWR_ACP_mapping_area_20180731"),
    anwr_1002 = ee.FeatureCollection("users/mmacander/ANWR/base_layers/ANWR_1002_Area"),
    anwr_acp_buff = ee.FeatureCollection("users/mmacander/ANWR/base_layers/ANWR_ACP_mapping_area_20180731_wBuffs");
var sa = anwr_acp_buff.union().first().geometry();

var dg2m = ee.Image('users/matt_macander/anwr/dg_corr_2m_20191109').select('blue', 'green', 'red', 'nir');
var srCirViz = {bands: ['nir','red','green'],  min: [0,0,0], max: [5000, 2000, 2000]},
    srRgbViz = {bands: ['red','green','blue'],  min: [0,0,0], max: [2000, 2000, 2000]};
var srCirSegViz = {bands: ['nir_mean','red_mean','green_mean'],  min: [0,0,0], max: [5000, 2000, 2000]},
    srRgbSegViz = {bands: ['red_mean','green_mean','blue_mean'],  min: [0,0,0], max: [2000, 2000, 2000]};
Map.addLayer(dg2m, srCirViz, 'dg2m');
// Map.centerObject(dg2m);

var dg2m_ndvi = dg2m.normalizedDifference(['nir', 'red']).multiply(10000).clamp(-10000, 10000).round().int16().rename('ndvi');
var dg2m_float = dg2m.addBands(dg2m_ndvi)
  .float().divide(10000)
  .reduceResolution(ee.Reducer.mean());


var dgSegs = ee.Algorithms.Image.Segmentation.SNIC({
  image: dg2m_float, 
  size: 10, //20
  compactness: 1/10000,
  connectivity: 4,
  neighborhoodSize: 128,
  // seeds: ee.Algorithms.Image.Segmentation.seedGrid(20, 'hex')
  })
  .reproject({crs: 'EPSG:3338', crsTransform: transform06m});
print(dgSegs, 'dgSegs');

Map.addLayer(dgSegs, srCirSegViz, 'dg segs cir', false);
Map.addLayer(dgSegs.randomVisualizer(), {}, 'dg segs', true);

var dgSegs_brrnn = dgSegs.select(['blue_mean', 'green_mean', 'red_mean', 'nir_mean', 'ndvi_mean'],
                                ['blue', 'green', 'red', 'nir', 'ndvi']);
Map.addLayer(dgSegs_brrnn, {}, 'Segs bgrnn', false);                                
var dgSegsOnly = dgSegs.select('clusters');
var dgSegsSeeds = dgSegs.select('seeds');

var dgSegs = dgSegsOnly.addBands(dgSegs_brrnn).addBands(dgSegsSeeds);

var patchsize = dgSegsOnly.connectedPixelCount(72 + 10, false);
var dgSegsOnlyBig = dgSegsOnly.updateMask(patchsize.gte(50));

function expandSeeds(seeds) {
  seeds = seeds.unmask(0).focal_max();
  return seeds.updateMask(seeds);
}

// // Compute per-cluster stdDev.
// var stdDev = dg2m_float.addBands(dgSegsOnlyBig).reduceConnectedComponents(ee.Reducer.stdDev(), "clusters", 256)
//     .reproject({crs: 'EPSG:3338', crsTransform: transform06m});
// Map.addLayer(stdDev, {min:0, max:0.01}, "StdDev", false);

// // Display outliers as transparent
// var outliers = stdDev.reduce('sum').gt(0.25)
//     .reproject({crs: 'EPSG:3338', crsTransform: transform06m});

// Map.addLayer(outliers.updateMask(outliers.not()), {}, "Outliers", false);

// var bands = ['blue', 'green', 'red', 'nir', 'ndvi'];
// // Within each outlier, find most distant member.
// var distance = dg2m_float.select(bands).spectralDistance(dgSegs_brrnn.select(bands), "sam").updateMask(outliers)
//     .reproject({crs: 'EPSG:3338', crsTransform: transform06m});

// var maxDistance = distance.addBands(dgSegsOnly).reduceConnectedComponents(ee.Reducer.max(), "clusters", 256)
//     .reproject({crs: 'EPSG:3338', crsTransform: transform06m});

// Map.addLayer(distance, {min:0, max:0.6}, "max distance", false);
// Map.addLayer(expandSeeds(distance.eq(maxDistance)), {palette: ["red"]}, "second seeds", false);
// Map.addLayer(expandSeeds(dgSegsSeeds), {palette: ["yellow"]}, "original seeds", false);

// var newSeeds = dgSegsSeeds.unmask(0).add(distance.eq(maxDistance).unmask(0))
//     .reproject({crs: 'EPSG:3338', crsTransform: transform06m});

// newSeeds = newSeeds.updateMask(newSeeds);

var snic_merge = function(image_orig,sniced,threshold){
  // var rg = ['#d7191c','#fdae61','#ffffbf','#a6d96a','#1a9641'];
  var bands = image_orig.bandNames(); 
  var min = sniced.focal_min(2); //max and min over kernel of sniced image - min and max will be different near cluster boundaries
  var max = sniced.focal_max(2);
  var diff = max.subtract(min).select(bands);
  var clusters_max = max.select('clusters');
  var similar = diff.reduce(ee.Reducer.max()).lte(ee.Number(threshold)); //max difference of all bands less than threshold
  
  var clusters_new = sniced.select('clusters').where(similar,clusters_max).rename('clusters_max');
  //wherever overlap band values are similar, set new cluster value to be the max cluster value from the overlap
  clusters_new = clusters_new.addBands(sniced.select('clusters')).reduceConnectedComponents(ee.Reducer.max(),'clusters',maxSize).rename('clusters');
  //recompute means of original image bands in each of the new clusters
  return image_orig.select(bands).addBands(clusters_new).reduceConnectedComponents(ee.Reducer.mean(),'clusters',maxSize).addBands(clusters_new);
};

var maxSize=256; //Bigger and things crash
var mergeThreshold = 0.005;
Map.addLayer(dg2m_float, {}, 'dg2m_float', false);
Map.addLayer(dgSegs, {}, 'dgSegs', false);
var dgSegsMerged = snic_merge(dg2m_float, dgSegs, mergeThreshold);
Map.addLayer(dgSegsMerged.select('clusters').randomVisualizer(), {}, 'segs merged');
// Map.addLayer(dgSegsMerged, {}, 'segs merged raw', false);
var dgSegsMerged2 = snic_merge(dg2m_float, dgSegsMerged, mergeThreshold);
var dgSegsMerged2Filled = ee.ImageCollection([dgSegsMerged, dgSegsMerged2]).mosaic();
Map.addLayer(dgSegsMerged2.select('clusters').randomVisualizer(), {}, 'segs merged2');
Map.addLayer(dgSegsMerged2Filled.select('clusters').randomVisualizer(), {}, 'segs merged2 filled');
// Map.addLayer(dgSegsMerged2, {}, 'segs merged2 raw', false);

// var sizeThresholdPixels = 0;//2 Landsat pixels = 50 6m pixels
// var focalModeRadiusPixels = 8;//7 or 8 pixel diameter would cover circular patch of 50 6m pixels
// // var sizeThresholdPixels = 250;//10 Landsat pixels = 250 6m pixels
// // var focalModeRadiusPixels = 16;//7 or 8 pixel diameter would cover circular patch of 50 6m pixels

// // count patch sizes
// var patchsize = dgSegsOnly.connectedPixelCount(sizeThresholdPixels + 10, false);

// // run a majority filter
// var filtered = dgSegsOnly.focal_mode({
//     radius: focalModeRadiusPixels, 
//     kernelType: 'circle',
//     units: 'pixels',
// }); 
  
// // updated image with majority filter where patch size is small
// var dgSegsOnlyFilt =  dgSegsOnly.where(patchsize.lt(sizeThresholdPixels),filtered); 

// //Iteration2
// var patchsize = dgSegsOnlyFilt.connectedPixelCount(sizeThresholdPixels + 10, false);
// var filtered = dgSegsOnlyFilt.focal_mode({
//     radius: focalModeRadiusPixels,
//     kernelType: 'circle',
//     units: 'pixels',
// }); 
// var dgSegsOnlyFilt2 =  dgSegsOnlyFilt.where(patchsize.lt(sizeThresholdPixels),filtered);

// //Iteration3
// var patchsize = dgSegsOnlyFilt2.connectedPixelCount(sizeThresholdPixels + 10, false);
// var filtered = dgSegsOnlyFilt2.focal_mode({
//     radius: focalModeRadiusPixels,
//     kernelType: 'circle',
//     units: 'pixels',
// }); 
// var dgSegsOnlyFilt3 =  dgSegsOnlyFilt2.where(patchsize.lt(sizeThresholdPixels),filtered);

// dgSegs = dgSegsOnly.addBands(dgSegs_brrnn);

// // print(dgSegs, dgSegsOnly, patchsize, filtered, dgSegsOnlyFilt);

// Map.addLayer(filtered.randomVisualizer(), {}, 'filtered', false);
// Map.addLayer(dgSegs2.randomVisualizer(), {}, 'dg segs2', true);
// Map.addLayer(dgSegsOnlyFilt.randomVisualizer(), {}, 'dg segs filt', false);
// Map.addLayer(dgSegsOnlyFilt2.randomVisualizer(), {}, 'dg segs filt iteration2', false);
// Map.addLayer(dgSegsOnlyFilt3.randomVisualizer(), {}, 'dg segs filt iteration3', false);
// Map.addLayer(patchsize.lt(50).selfMask(), {}, 'patchsize lt 50', false);

var exportArea = test_bnds;
var exportArea = sa;

// Export.image.toAsset({
//   image: dgSegsOnly.addBands(dgSegsSeeds),
//   region: exportArea,
//   assetId: 'users/mmacander/ANWR/segments/snic_segs_06m_20191129_sq',
//   crsTransform: transform06m,
//   // scale: 2,
//   crs: 'EPSG:3338',
//   maxPixels: 1e12,
//   pyramidingPolicy: {'clusters': 'mode'} 
//   });
// print(dgSegsMerged2Filled);
Export.image.toAsset({
  image: dgSegsMerged2Filled.select('clusters'),
  region: exportArea,
  assetId: 'users/mmacander/ANWR/segments/snic_20191201_segs_05m_10sq_merged_iter2_p005',
  crsTransform: transform06m,
  // scale: 2,
  crs: 'EPSG:3338',
  maxPixels: 1e12,
  pyramidingPolicy: {'clusters': 'mode'} 
  });

Export.image.toDrive({
  image: dgSegsMerged2Filled.select('clusters'),//Need to split into different exports or make type same
  region: exportArea,
  description: 'snic_20191201_segs_05m_10sq_merged_iter2_p005',
  folder: '2019_anwr',
  // scale: 2,
  crsTransform: transform06m,
  crs: 'EPSG:3338',
  maxPixels: 1e12,
  });

// Export.image.toAsset({
//   image: dgSegsOnlyFilt3,
//   region: exportArea,
//   assetId: 'users/mmacander/ANWR/segments/snic_segs_06m_20191126_wNDVI_filt3',
//   crsTransform: transform06m,
//   // scale: 2,
//   crs: 'EPSG:3338',
//   maxPixels: 1e12,
//   pyramidingPolicy: {'clusters': 'mode'} 
//   });

// Export.image.toDrive({
//   image: dgSegsOnlyFilt3,
//   region: exportArea,
//   description: 'snic_segs_06m_20191126_wNDVI_filt3',
//   folder: '2019_anwr',
//   // scale: 2,
//   crsTransform: transform06m,
//   crs: 'EPSG:3338',
//   maxPixels: 1e12,
//   });

// Map.addLayer(snic, srCirSegViz, 'snic asset cir', false);
// Map.addLayer(snic.select('clusters').randomVisualizer(), {}, 'snic asset');
// var range = snic.select('clusters').reduceRegion({
//   // reducer: ee.Reducer.minMax(), 
//   reducer: ee.Reducer.frequencyHistogram(), 
//   geometry: snic.geometry(),
//   maxPixels: 1e12});
// // print(range);
