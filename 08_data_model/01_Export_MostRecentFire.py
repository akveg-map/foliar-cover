# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Export most recent fire year
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Export most recent fire year" exports the most recent fire year raster to Google Cloud storage.
# ---------------------------------------------------------------------------

# Import packages
import ee
from google.auth.transport.requests import AuthorizedSession

#### SET UP GEE ENVIRONMENT
####____________________________________________________

# Define paths
asset_project = 'akveg-map'
storage_bucket = 'akveg-data'
storage_prefix = 'ancillary_v20240822'

# Authenticate with Earth Engine
print('Requesting information from server...')
ee.Authenticate()
ee.Initialize(project=asset_project)

# Specify the cloud project you want associated with Earth Engine requests.
session = AuthorizedSession(
  ee.data.get_persistent_credentials().with_quota_project(asset_project)
)

# Define asset path
asset_path = f'projects/{asset_project}/assets'

# Load data
prediction_region = ee.FeatureCollection(f'{asset_path}/regions/AlaskaYukon_MapDomain_3338_v20230330')
elevation_image = ee.Image(
    f'projects/{asset_project}/assets/covariates_v20240711/Elevation_10m_3338'
).rename(['elevation'])
fireyear_image = ee.Image(f'{asset_path}/disturbance/mrfy_akyuk_1917_2023_10m_3338_v20240309')

# Define output projection
projection = elevation_image.select('elevation').projection().getInfo()

#### EXPORT DATA TO STORAGE
####____________________________________________________

# Export tiff to storage
print('Creating GEE task...')
task = ee.batch.Export.image.toCloudStorage(
  image=fireyear_image,
  description='export-fire-year',
  bucket='akveg-data',
  fileNamePrefix=f'{storage_prefix}/AlaskaYukon_FireYear_10m_3338.tif',
  scale=10,
  crs=projection['crs'],
  crsTransform=projection['transform'],
  region=prediction_region.geometry(),
  maxPixels=1e12,
  fileFormat='GeoTIFF',
  formatOptions={
    'noData': -32768
  }
)
task.start()
print('GEE task sent to server.')
print('----------')
