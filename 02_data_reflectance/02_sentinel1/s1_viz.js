var tiles = ee.FeatureCollection('projects/akveg-map/assets/tiles/AKVEG_050km_tiles_3338_v20230325');
var regions = ee.FeatureCollection('projects/akveg-map/assets/regions/ABoVE_Alaska_3parts_Buff10km_BuffMinus5km_Simplify5km_4326_v20230328');
if(false) {
  var s1_composite_test = ee.Image.loadGeoTIFF('gs://akveg-data/s1_2022_v20230326/s1_flat_seasonal_2022_AK100H18V04_v20230326.tif');
  s1_composite_test = s1_composite_test
    .updateMask(s1_composite_test.select(0).neq(-32768));
  var s1_composite_qa_test = ee.Image.loadGeoTIFF('gs://akveg-data/s1_2022_v20230326/s1_flat_seasonal_2022_qa_AK100H18V04_v20230326.tif')
  s1_composite_qa_test = s1_composite_qa_test
    .updateMask(s1_composite_qa_test.select(0).neq(255));

  print(s1_composite_qa, s1_composite_qa_test);

  Map.addLayer(s1_composite_test, {bands:['VV_p50_froz_asc','VV_p50_grow_asc','VV_p50_fall_asc'], min:-1900, max:-100}, 's1_composite VV_asc');
  Map.addLayer(s1_composite_test, {bands:['VH_p50_froz_asc','VH_p50_grow_asc','VH_p50_fall_asc'], min:-3000, max:-900}, 's1_composite VH_asc');
  Map.addLayer(s1_composite_qa_test, {bands:['n_froz_asc','n_grow_asc','n_fall_asc'], min:1, max:40}, 's1_composite obs counts_asc', false);
  Map.addLayer(s1_composite_qa_test, {bands:['yearTier_froz_asc','yearTier_grow_asc','yearTier_fall_asc'], min:1, max:3}, 's1_composite input years_asc', false);

  Map.addLayer(s1_composite_test, {bands:['VV_p50_froz_desc','VV_p50_grow_desc','VV_p50_fall_desc'], min:-1900, max:-100}, 's1_composite VV_desc');
  Map.addLayer(s1_composite_test, {bands:['VH_p50_froz_desc','VH_p50_grow_desc','VH_p50_fall_desc'], min:-3000, max:-900}, 's1_composite VH_desc');
  Map.addLayer(s1_composite_qa_test, {bands:['n_froz_desc','n_grow_desc','n_fall_desc'], min:1, max:40}, 's1_composite obs counts_desc', false);
  Map.addLayer(s1_composite_qa_test, {bands:['yearTier_froz_desc','yearTier_grow_desc','yearTier_fall_desc'], min:1, max:3}, 's1_composite input years_desc', false);
}
// throw('stop')
var s1_composite_coll = ee.ImageCollection('projects/akveg-map/assets/s1_2022_v20230326')
s1_composite_coll = s1_composite_coll.map(function(img) {
  return img.updateMask(img.neq(-32768))})
// Map.addLayer(s1_composite_coll, {}, 's1_composite_coll', false);
var s1_composite = s1_composite_coll.mosaic()

// var s1_composite_qa_coll = ee.ImageCollection('projects/akveg-map/assets/s1_v20230326_qa')
// s1_composite_qa_coll = s1_composite_qa_coll.map(function(img) {
//   return img.updateMask(img.select(0).neq(255))})
// var s1_composite_qa = s1_composite_qa_coll.mosaic()

print(s1_composite);
// Map.addLayer(s1_composite);

Map.addLayer(s1_composite, {bands:['VV_p50_froz_asc','VV_p50_grow_asc','VV_p50_fall_asc'], min:-1900, max:-100}, 's1_composite VV_asc');
Map.addLayer(s1_composite, {bands:['VH_p50_froz_asc','VH_p50_grow_asc','VH_p50_fall_asc'], min:-3000, max:-900}, 's1_composite VH_asc');
Map.addLayer(s1_composite_coll, {bands:['n_froz_asc','n_grow_asc','n_fall_asc'], min:1, max:40}, 's1_composite obs counts_asc', false);
Map.addLayer(s1_composite_coll, {bands:['yearTier_froz_asc','yearTier_grow_asc','yearTier_fall_asc'], min:1, max:3}, 's1_composite input years_asc', false);

Map.addLayer(s1_composite, {bands:['VV_p50_froz_desc','VV_p50_grow_desc','VV_p50_fall_desc'], min:-1900, max:-100}, 's1_composite VV_desc');
Map.addLayer(s1_composite, {bands:['VH_p50_froz_desc','VH_p50_grow_desc','VH_p50_fall_desc'], min:-3000, max:-900}, 's1_composite VH_desc');
Map.addLayer(s1_composite_coll, {bands:['n_froz_desc','n_grow_desc','n_fall_desc'], min:1, max:40}, 's1_composite obs counts_desc', false);
Map.addLayer(s1_composite_coll, {bands:['yearTier_froz_desc','yearTier_grow_desc','yearTier_fall_desc'], min:1, max:3}, 's1_composite input years_desc', false);

Map.addLayer(tiles, {}, 'tiles', false);
Map.addLayer(regions, {}, 'regions', false);