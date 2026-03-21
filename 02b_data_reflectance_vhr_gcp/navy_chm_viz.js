/**
 * Navy North Slope CHM Visualization
 * Includes 0.5m PS SRLite (Input) and DINOv3 CHM (Output)
 */

var strips = [
  {id: '20240710', path: '20240710_222652_WV03_10400100996FB100'},
  {id: '20220803', path: '20220803_213641_WV03_10400100786F6C00'},
  {id: '20200714', path: '20200714_220835_WV02_10300100AB37D700'}
];

var vis_ps = {bands: ['B3', 'B2', 'B1'], min: 0, max: 1500};
var vis_chm = {
  min: 0, 
  max: 500, // 5 meters
  palette: ['#000000', '#440154', '#3b528b', '#21918c', '#5ec962', '#fde725']
};

strips.forEach(function(strip) {
  // 1. Input PS SRLite
  var ps_url = 'gs://akveg-data/vhr/navy_north_slope/processed/' + strip.path + '/225_srlite/PS_SRLite_00p50m_' + strip.path + '.tif';
  var ps_img = ee.Image.loadGeoTIFF(ps_url);
  Map.addLayer(ps_img, vis_ps, strip.id + ' PS SRLite', false);

  // 2. Output CHM (In Centimeters)
  var chm_url = 'gs://akveg-data/vhr/navy_north_slope/processed/' + strip.path + '/250_cog/CHM_cm_DINOv3_' + strip.path + '.tif';
  var chm_img = ee.Image.loadGeoTIFF(chm_url);
  
  // Mask nodata (-9999)
  var chm_masked = chm_img.updateMask(chm_img.gt(-9999));
  
  Map.addLayer(chm_masked, vis_chm, strip.id + ' CHM (cm)', true);
});

Map.setCenter(-156.6, 71.3, 12);
