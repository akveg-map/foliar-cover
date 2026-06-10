//2023-03-26 version
//Script cleanup
//Fix GCS nodata export
//cleanup(bash): gsutil -m rm -r gs://akveg-data/s1_2022_v20230320

//2023-03-25 version
//Changed to AKVEG 100km tiles

//Set nMin=1 for backstop tiers
//Changed MGRS version to latest tiles, lower overlap

//2023-03-20 version
//Rescale to INT16 (could multiply by 100 and round/truncate
//Tweak DEM setDefaultProjection to avoid striping
//Require minimum sample size for year tier 1 and 2. Perhaps 3?
//add version without gamma correction so there are no holes
//Export to Cloud Storage

//Vollrath version of repo does not preserve image dates
// var slope_lib = require('users/andreasvollrath/radar:slope_correction_lib2.js');
var slope_lib = require('users/mmacander/public:functions/s1_slope_correction_module.js');
var aboveConstants = require('users/mmacander/public:functions/aboveConstants'); // Load module
var tiler = require('users/gena/packages:tiler')

var version = 'v20230326',
  // match = 'AK100H18', //wildcard match for tile name
  // minH = 1, maxH = 34,
  // minH = 35, maxH = 38,
  // minH = 39, maxH = 44,
  // minH = 45, maxH = 48,
  // minH = 49, maxH = 52,
  // minH = 53, maxH = 58,
  minH = 70, maxH = 75,
  minV = 1, maxV = 99,
  draw = false,
  draw_tile = false,
  exportAsset = false,
  exportGCS = true,
  exportDrive = false;
  // crsTransform = [10,0,5,0,-10,5]; // EPSG:3338 version to nest in Landsat [XDIM, 0.0, ULX, 0.0, -YDIM, ULY]

// var tiles_akveg = ee.FeatureCollection('projects/akveg-map/assets/tiles/AKVEG_100km_tiles_3338_v20230325');
var tiles_akveg = ee.FeatureCollection('projects/akveg-map/assets/tiles/AKVEG_050km_tiles_3338_v20230329');
var tiles = tiles_akveg;

// var above_ak = ee.FeatureCollection('users/mmacander/above_mapping/study_areas/ABoVE_Alaska_4parts_Buff10km_BuffMinus5km_Simplify5km_3338');
// var studyArea = above_ak.filter(ee.Filter.eq('Region','North American Beringea and Alaska Maritime'));
var above_ak = ee.FeatureCollection('projects/akveg-map/assets/regions/ABoVE_Alaska_3parts_Buff10km_BuffMinus5km_Simplify5km_4326_v20230328');
var studyArea = above_ak.filter(ee.Filter.eq('Region','North American Beringia and TNP'));

Map.addLayer(studyArea, {}, 'studyArea', false);

var tiles_sa = tiles.filterBounds(studyArea);
print(tiles_sa.size(), 'num tiles');

var elevationVis = {
  min: 0,
  max: 5000,
  palette: ['0000ff', '00ffff', 'ffff00', 'ff0000', 'ffffff']
};

var glo30 = ee.ImageCollection("COPERNICUS/DEM/GLO30");
var elevation_all = glo30.select('DEM');
// print(elevation_all.size(), elevation_all.filterBounds(geometry).limit(100))
Map.addLayer(elevation_all, {min:0, max:5000}, 'Elevation', false);

var manualList = [
  'AK050H65V25',
  'AK050H66V28',
  'AK050H66V29',
  'AK050H66V30',
  'AK050H67V25',
  'AK050H67V26',
  'AK050H67V28',
  'AK050H67V29',
  'AK050H67V30',
  'AK050H67V31',
  'AK050H68V25',
  'AK050H68V26',
  'AK050H68V27',
  'AK050H68V28',
  'AK050H68V29',
  'AK050H68V30',
  'AK050H68V31',
  ];


print(tiles_sa.limit(10));
var tiles_sel = tiles_sa
  .filter(ee.Filter.inList('gridID',manualList))
  // .filter(ee.Filter.gte('H', minH))
  // .filter(ee.Filter.lte('H', maxH))
  // .filter(ee.Filter.gte('V', minV))
  // .filter(ee.Filter.lte('V', maxV))
var tileList = ee.List(tiles_sel.reduceColumns(ee.Reducer.toList(), ['gridID']).get('list')).sort();
print(tileList);

// tileList = tileList
//   .filter(ee.Filter.stringStartsWith('item',match));

print(tileList);
// throw('stop');
// tileList.slice(0,100).getInfo().map(function(region) {
tileList.slice(0,200).getInfo().map(function(region) {
  var footprint = tiles_sa.filterMetadata('gridID','equals', region).first();
  var epsg = footprint.get('epsg').getInfo();
  var crs = 'EPSG:'+epsg;
  var clipper = footprint.geometry().intersection(above_ak); //.bounds(1, ee.String('EPSG:').cat(ee.String(epsg)));
  var transform = footprint.getString('transform').getInfo();
  var dimensions = footprint.getString('dimensions').getInfo();

  if(draw_tile) {Map.addLayer(footprint.geometry(), {}, region, true)}

  //Set this to match typical input CRS for the tile area (scale changes by latitude for global glo30 coll)
  var elevation = elevation_all
    .filterBounds(footprint.geometry());
  var elevation_proj = elevation.first().select(0).projection();
  elevation = elevation.mosaic()
    .setDefaultProjection(elevation_proj);

  // print(region);

  // Get S1 collection
  var s1_vv_vh =  ee.ImageCollection('COPERNICUS/S1_GRD')
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
    .filter(ee.Filter.eq('instrumentMode', 'IW'))
    .filterBounds(clipper)

  // print(s1_vv_vh.size());
  // Map.addLayer(s1_vv_vh, {}, 'ic');

  var s1_vv_vh_gamma_allYears = slope_lib.slope_correction(s1_vv_vh,
    {'model': 'volume',
    'elevation': elevation})
    .map(function(image) {
      return image.updateMask(image.select('no_data_mask')).select(['VV','VH'])
    });

  //Backup for areas where no correction possible; same output units
  var s1_vv_vh_nogam_allYears = s1_vv_vh.select('VV','VH')


  // Display collections for inspection
  // Map.addLayer(s1_vv_vh_gamma_allYears.filter(ee.Filter.eq('orbitProperties_pass', 'ASCENDING')), {}, 'asc s1_vv_vh_gamma_allYears', false);
  // Map.addLayer(s1_vv_vh_gamma_allYears.filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING')), {}, 'desc s1_vv_vh_gamma_allYears', false);

  // Map.addLayer(s1_vv_vh_nogam_allYears.filter(ee.Filter.eq('orbitProperties_pass', 'ASCENDING')), {}, 'asc s1_vv_vh_gamma_allYears', false);
  // Map.addLayer(s1_vv_vh_nogam_allYears.filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING')), {}, 'desc s1_vv_vh_gamma_allYears', false);

  // Map.addLayer(s1_vv_vh_fldem_allYears.filter(ee.Filter.eq('orbitProperties_pass', 'ASCENDING')), {}, 'asc s1_vv_vh_gamma_allYears', false);
  // Map.addLayer(s1_vv_vh_fldem_allYears.filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING')), {}, 'desc s1_vv_vh_gamma_allYears', false);

  var froz_asc = ee.ImageCollection([
    s1_percentile(s1_vv_vh_nogam_allYears, 2000, 2030, 1, 59, 'ASCENDING', 'asc', 4, 'froz', 1),
    s1_percentile(s1_vv_vh_gamma_allYears, 2000, 2030, 1, 59, 'ASCENDING', 'asc', 3, 'froz', 1),
    s1_percentile(s1_vv_vh_gamma_allYears, 2020, 2022, 1, 59, 'ASCENDING', 'asc', 2, 'froz', 3),
    s1_percentile(s1_vv_vh_gamma_allYears, 2022, 2022, 1, 59, 'ASCENDING', 'asc', 1, 'froz', 3)])
    .mosaic();

  var grow_asc = ee.ImageCollection([
    s1_percentile(s1_vv_vh_nogam_allYears, 2000, 2030, 182, 243, 'ASCENDING', 'asc', 4, 'grow', 1),
    s1_percentile(s1_vv_vh_gamma_allYears, 2000, 2030, 182, 243, 'ASCENDING', 'asc', 3, 'grow', 1),
    s1_percentile(s1_vv_vh_gamma_allYears, 2020, 2022, 182, 243, 'ASCENDING', 'asc', 2, 'grow', 3),
    s1_percentile(s1_vv_vh_gamma_allYears, 2022, 2022, 182, 243, 'ASCENDING', 'asc', 1, 'grow', 3)])
    .mosaic();

  var fall_asc = ee.ImageCollection([
    s1_percentile(s1_vv_vh_nogam_allYears, 2000, 2030, 274, 366, 'ASCENDING', 'asc', 4, 'fall', 1),
    s1_percentile(s1_vv_vh_gamma_allYears, 2000, 2030, 274, 366, 'ASCENDING', 'asc', 3, 'fall', 1),
    s1_percentile(s1_vv_vh_gamma_allYears, 2020, 2022, 274, 366, 'ASCENDING', 'asc', 2, 'fall', 3),
    s1_percentile(s1_vv_vh_gamma_allYears, 2022, 2022, 274, 366, 'ASCENDING', 'asc', 1, 'fall', 3)])
    .mosaic();

  var froz_desc = ee.ImageCollection([
    s1_percentile(s1_vv_vh_nogam_allYears, 2000, 2030, 1, 59, 'DESCENDING', 'desc', 4, 'froz', 1),
    s1_percentile(s1_vv_vh_gamma_allYears, 2000, 2030, 1, 59, 'DESCENDING', 'desc', 3, 'froz', 1),
    s1_percentile(s1_vv_vh_gamma_allYears, 2020, 2022, 1, 59, 'DESCENDING', 'desc', 2, 'froz', 3),
    s1_percentile(s1_vv_vh_gamma_allYears, 2022, 2022, 1, 59, 'DESCENDING', 'desc', 1, 'froz', 3)])
    .mosaic();

  var grow_desc = ee.ImageCollection([
    s1_percentile(s1_vv_vh_nogam_allYears, 2000, 2030, 182, 243, 'DESCENDING', 'desc', 4, 'grow', 1),
    s1_percentile(s1_vv_vh_gamma_allYears, 2000, 2030, 182, 243, 'DESCENDING', 'desc', 3, 'grow', 1),
    s1_percentile(s1_vv_vh_gamma_allYears, 2020, 2022, 182, 243, 'DESCENDING', 'desc', 2, 'grow', 3),
    s1_percentile(s1_vv_vh_gamma_allYears, 2022, 2022, 182, 243, 'DESCENDING', 'desc', 1, 'grow', 3)])
    .mosaic();

  var fall_desc = ee.ImageCollection([
    s1_percentile(s1_vv_vh_nogam_allYears, 2000, 2030, 274, 366, 'DESCENDING', 'desc', 4, 'fall', 1),
    s1_percentile(s1_vv_vh_gamma_allYears, 2000, 2030, 274, 366, 'DESCENDING', 'desc', 3, 'fall', 1),
    s1_percentile(s1_vv_vh_gamma_allYears, 2020, 2022, 274, 366, 'DESCENDING', 'desc', 2, 'fall', 3),
    s1_percentile(s1_vv_vh_gamma_allYears, 2022, 2022, 274, 366, 'DESCENDING', 'desc', 1, 'fall', 3)])
    .mosaic();

  var seasonal_s1 = froz_asc.addBands(froz_desc)
    .addBands(grow_asc).addBands(grow_desc)
    .addBands(fall_asc).addBands(fall_desc);
  // print(seasonal_s1);

  if(draw) {
    Map.addLayer(seasonal_s1, {bands:['VV_p50_froz_asc','VV_p50_grow_asc','VV_p50_fall_asc'], min:-1900, max:-100}, 's1_composite VV_asc');
    Map.addLayer(seasonal_s1, {bands:['VH_p50_froz_asc','VH_p50_grow_asc','VH_p50_fall_asc'], min:-3000, max:-900}, 's1_composite VH_asc');
    Map.addLayer(seasonal_s1, {bands:['n_froz_asc','n_grow_asc','n_fall_asc'], min:1, max:40}, 's1_composite obs counts_asc', false);
    Map.addLayer(seasonal_s1, {bands:['yearTier_froz_asc','yearTier_grow_asc','yearTier_fall_asc'], min:1, max:3}, 's1_composite input years_asc', false);
    Map.addLayer(seasonal_s1, {bands:['VV_p50_froz_desc','VV_p50_grow_desc','VV_p50_fall_desc'], min:-1900, max:-100}, 's1_composite VV_desc');
    Map.addLayer(seasonal_s1, {bands:['VH_p50_froz_desc','VH_p50_grow_desc','VH_p50_fall_desc'], min:-3000, max:-900}, 's1_composite VH_desc');
    Map.addLayer(seasonal_s1, {bands:['n_froz_desc','n_grow_desc','n_fall_desc'], min:1, max:40}, 's1_composite obs counts_desc', false);
    Map.addLayer(seasonal_s1, {bands:['yearTier_froz_desc','yearTier_grow_desc','yearTier_fall_desc'], min:1, max:3}, 's1_composite input years_desc', false);
  }

  if(exportAsset) {Export.image.toAsset({
    image: seasonal_s1,
    description: 'asset_s1_flat_seasonal_composite_2022_'+region+'_'+version,
    assetId: 'projects/foreststructure/Circumboreal/S1_Composites_3338/s1_flat_seasonal_composite_2022_'+region+'_'+version,
    crs: 'EPSG:3338',
    crsTransform: transform,
    maxPixels: 1e12,
  });}

  if(exportGCS) {
    // Map.addLayer(seasonal_s1.select('^VV.*').addBands(seasonal_s1.select('^VH.*')).clip(clipper).unmask(-32768));
    // print(seasonal_s1.select('^VV.*').addBands(seasonal_s1.select('^VH.*')).clip(clipper).unmask(-32768, false));
    Export.image.toCloudStorage({
      // image: seasonal_s1.select('^VV.*').addBands(seasonal_s1.select('^VH.*')).clip(clipper).unmask(-32768, false),
      image: seasonal_s1.clip(clipper).unmask(-32768, false),
      description: 'gcs_s1_flat_seasonal_composite_2022_'+region+'_'+version,
      bucket: 'akveg-data',
      fileNamePrefix: 's1_2022_'+version+'/s1_flat_seasonal_2022_'+region+'_'+version,
      dimensions: dimensions,
      crs: crs,
      crsTransform: transform,
      maxPixels: 1e12,
      fileFormat: 'GeoTIFF',
      formatOptions: {cloudOptimized: true}});

    // Export.image.toCloudStorage({
    //   image: seasonal_s1.select('^n.*').addBands(seasonal_s1.select('^yearTier.*')).byte().clip(clipper).unmask(255),
    //   description: 'gcs_qa_s1_flat_seasonal_composite_2022_'+region+'_'+version,
    //   bucket: 'akveg-data',
    //   fileNamePrefix: 's1_2022_'+version+'/s1_flat_seasonal_2022_qa_'+region+'_'+version,
    //   dimensions: dimensions,
    //   // crs: 'EPSG:3338',
    //   crs: crs,
    //   crsTransform: transform,
    //   maxPixels: 1e12,
    //   fileFormat: 'GeoTIFF',
    //   formatOptions: {cloudOptimized: true}});
  }

  if(exportDrive) {Export.image.toDrive({
    image: seasonal_s1.unmask(-32768),
    description: 's1_flat_seasonal_composite_2022_'+region+'_'+version,
    folder: '2023_akveg',
    crs: 'EPSG:3338',
    crsTransform: transform,
    fileFormat: 'GeoTIFF',
    // formatOptions: {cloudOptimized: true},
  })  }

  return(region);
  });

function s1_percentile(ic, startYear, endYear, startDoy, endDoy, pass, passName, yearsNum, seasonName, nMin) {
    // print(startYear, endYear, startDoy, endDoy, pass, passName, yearsNum, seasonName)
    var startDate = startYear + '-07-01';
    var endDate = (endYear + 1) + '-03-01';
    var ic_filt = ic
      .filterDate(startDate, endDate)
      .filter(ee.Filter.calendarRange(startDoy, endDoy, 'day_of_year'))
      .filter(ee.Filter.eq('orbitProperties_pass', pass))
      //add empty image to avoid errors from empty collections
      .merge(ee.ImageCollection(ee.Image().double().rename('VV').addBands(ee.Image().double().rename('VH'))));
    // print(ic_filt.size(), ic_filt);
    // var ic_filt_n = ic_filt.count().select(['VV'],['n_'+seasonName+'_'+passName]).uint16();
    var ic_filt_n = ic_filt.count().select(['VV'],['n_'+seasonName+'_'+passName]).int16();
    var nMask = ic_filt_n.gte(nMin);
    var median = ic_filt
      .median()
      .regexpRename('$', '_p50_'+seasonName+'_'+passName)
      .multiply(100)
      .clamp(-32000, 32000)
      .int16();
    var composite = median.addBands(ic_filt_n)
      .addBands(ee.Image(yearsNum).int16().rename('yearTier_'+seasonName+'_'+passName))
      .updateMask(nMask);
    return composite;
  }
