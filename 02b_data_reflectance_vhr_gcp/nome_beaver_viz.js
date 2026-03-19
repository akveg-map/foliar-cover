// Auto-generated GEE script for VHR COGs
// Source: gs://akveg-data/vhr/nome_beaver/processed

// Visualization Parameters (False Color: NIR, Red, Green)
var vis_nrg = {bands: ['nir', 'red', 'green'], min: 0, max: [5000, 2000, 2000]};
var vis_pan = {bands: ['pan'], min: 0, max: 5000};
var vis_cloud = {min: 0, max: 1, palette: ['black', 'white']};
var vis_rgb = {bands: ['red', 'green', 'blue'], min: 0, max: 5000};

// Image Collections
var ic_ccdc_20190818_215105 = ee.ImageCollection([
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20190818_215105_WV03_1040010050B5A700/202_ccdc_sr/ccdc_20190818_215105.tif'),
]);

var ic_MS_TOA_02p00m = ee.ImageCollection([
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20190818_215105_WV03_1040010050B5A700/205_ortho_toa/MS_TOA_02p00m_20190818_215105_WV03_1040010050B5A700.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20220712_214724_WV02_10300100D6D40F00/205_ortho_toa/MS_TOA_02p00m_20220712_214724_WV02_10300100D6D40F00.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212222_WV03_1040010097BADA00/205_ortho_toa/MS_TOA_02p00m_20240623_212222_WV03_1040010097BADA00.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212311_WV03_10400100988B6F00/205_ortho_toa/MS_TOA_02p00m_20240623_212311_WV03_10400100988B6F00.tif'),
]);

var ic_P_TOA_00p50m = ee.ImageCollection([
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20190818_215105_WV03_1040010050B5A700/205_ortho_toa/P_TOA_00p50m_20190818_215105_WV03_1040010050B5A700.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20220712_214724_WV02_10300100D6D40F00/205_ortho_toa/P_TOA_00p50m_20220712_214724_WV02_10300100D6D40F00.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212222_WV03_1040010097BADA00/205_ortho_toa/P_TOA_00p50m_20240623_212222_WV03_1040010097BADA00.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212311_WV03_10400100988B6F00/205_ortho_toa/P_TOA_00p50m_20240623_212311_WV03_10400100988B6F00.tif'),
]);

var ic_MS_Cloud_02p00m = ee.ImageCollection([
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20190818_215105_WV03_1040010050B5A700/210_cloud/MS_Cloud_02p00m_20190818_215105_WV03_1040010050B5A700.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20220712_214724_WV02_10300100D6D40F00/210_cloud/MS_Cloud_02p00m_20220712_214724_WV02_10300100D6D40F00.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212222_WV03_1040010097BADA00/210_cloud/MS_Cloud_02p00m_20240623_212222_WV03_1040010097BADA00.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212311_WV03_10400100988B6F00/210_cloud/MS_Cloud_02p00m_20240623_212311_WV03_10400100988B6F00.tif'),
]);

var ic_PS_TOA_00p50m = ee.ImageCollection([
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20190818_215105_WV03_1040010050B5A700/212_pansharpen/PS_TOA_00p50m_20190818_215105_WV03_1040010050B5A700.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20220712_214724_WV02_10300100D6D40F00/212_pansharpen/PS_TOA_00p50m_20220712_214724_WV02_10300100D6D40F00.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212222_WV03_1040010097BADA00/212_pansharpen/PS_TOA_00p50m_20240623_212222_WV03_1040010097BADA00.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212311_WV03_10400100988B6F00/212_pansharpen/PS_TOA_00p50m_20240623_212311_WV03_10400100988B6F00.tif'),
]);

var ic_MS_TOA_02p00m_30m = ee.ImageCollection([
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20190818_215105_WV03_1040010050B5A700/220_srlite_input/MS_TOA_02p00m_20190818_215105_WV03_1040010050B5A700_30m.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20220712_214724_WV02_10300100D6D40F00/220_srlite_input/MS_TOA_02p00m_20220712_214724_WV02_10300100D6D40F00_30m.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212222_WV03_1040010097BADA00/220_srlite_input/MS_TOA_02p00m_20240623_212222_WV03_1040010097BADA00_30m.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212311_WV03_10400100988B6F00/220_srlite_input/MS_TOA_02p00m_20240623_212311_WV03_10400100988B6F00_30m.tif'),
]);

var ic_PS_TOA_00p50m_30m = ee.ImageCollection([
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20190818_215105_WV03_1040010050B5A700/220_srlite_input/PS_TOA_00p50m_20190818_215105_WV03_1040010050B5A700_30m.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20220712_214724_WV02_10300100D6D40F00/220_srlite_input/PS_TOA_00p50m_20220712_214724_WV02_10300100D6D40F00_30m.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212222_WV03_1040010097BADA00/220_srlite_input/PS_TOA_00p50m_20240623_212222_WV03_1040010097BADA00_30m.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212311_WV03_10400100988B6F00/220_srlite_input/PS_TOA_00p50m_20240623_212311_WV03_10400100988B6F00_30m.tif'),
]);

var ic_MS_SRLite_02p00m = ee.ImageCollection([
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20190818_215105_WV03_1040010050B5A700/225_srlite/MS_SRLite_02p00m_20190818_215105_WV03_1040010050B5A700.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20220712_214724_WV02_10300100D6D40F00/225_srlite/MS_SRLite_02p00m_20220712_214724_WV02_10300100D6D40F00.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212222_WV03_1040010097BADA00/225_srlite/MS_SRLite_02p00m_20240623_212222_WV03_1040010097BADA00.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212311_WV03_10400100988B6F00/225_srlite/MS_SRLite_02p00m_20240623_212311_WV03_10400100988B6F00.tif'),
]);

var ic_PS_SRLite_00p50m = ee.ImageCollection([
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20190818_215105_WV03_1040010050B5A700/225_srlite/PS_SRLite_00p50m_20190818_215105_WV03_1040010050B5A700.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20220712_214724_WV02_10300100D6D40F00/225_srlite/PS_SRLite_00p50m_20220712_214724_WV02_10300100D6D40F00.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212222_WV03_1040010097BADA00/225_srlite/PS_SRLite_00p50m_20240623_212222_WV03_1040010097BADA00.tif'),
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212311_WV03_10400100988B6F00/225_srlite/PS_SRLite_00p50m_20240623_212311_WV03_10400100988B6F00.tif'),
]);

var ic_ccdc_20220712_214724 = ee.ImageCollection([
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20220712_214724_WV02_10300100D6D40F00/202_ccdc_sr/ccdc_20220712_214724.tif'),
]);

var ic_ccdc_20240623_212222 = ee.ImageCollection([
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212222_WV03_1040010097BADA00/202_ccdc_sr/ccdc_20240623_212222.tif'),
]);

var ic_ccdc_20240623_212311 = ee.ImageCollection([
  ee.Image.loadGeoTIFF('gs://akveg-data/vhr/nome_beaver/processed/20240623_212311_WV03_10400100988B6F00/202_ccdc_sr/ccdc_20240623_212311.tif'),
]);

// Map Layers
Map.addLayer(ic_ccdc_20190818_215105, vis_nrg, 'ccdc_20190818_215105', false);
Map.addLayer(ic_ccdc_20220712_214724, vis_nrg, 'ccdc_20220712_214724', false);
Map.addLayer(ic_ccdc_20240623_212222, vis_nrg, 'ccdc_20240623_212222', false);
Map.addLayer(ic_ccdc_20240623_212311, vis_nrg, 'ccdc_20240623_212311', false);
Map.addLayer(ic_P_TOA_00p50m, vis_pan, 'P_TOA_00p50m', false);
Map.addLayer(ic_MS_TOA_02p00m, vis_nrg, 'MS_TOA_02p00m', false);
Map.addLayer(ic_MS_TOA_02p00m_30m, vis_nrg, 'MS_TOA_02p00m_30m', false);
Map.addLayer(ic_MS_SRLite_02p00m, vis_nrg, 'MS_SRLite_02p00m', false);
Map.addLayer(ic_PS_TOA_00p50m, vis_nrg, 'PS_TOA_00p50m', true);
Map.addLayer(ic_PS_TOA_00p50m_30m, vis_nrg, 'PS_TOA_00p50m_30m', true);
Map.addLayer(ic_PS_SRLite_00p50m, vis_nrg, 'PS_SRLite_00p50m', true);
Map.addLayer(ic_MS_Cloud_02p00m.mosaic().selfMask(), vis_cloud, 'MS_Cloud_02p00m', true);

Map.centerObject(ic_PS_SRLite_00p50m);