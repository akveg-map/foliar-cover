# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Buffer point features
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-02-25
# Usage: Must be executed in a Python 3.12+ installation with authentication to Google Earth Engine.
# Description: "Buffer point features" transforms point geometries into circular polygon representations using the buffer radius stored in the 'plot_radius_m' field.
# ---------------------------------------------------------------------------

# Import packages
import ee
from datetime import datetime

#### SET UP ENVIRONMENT
####____________________________________________________

# Define paths
ee_project = 'akveg-map'
storage_bucket = 'akveg-data'
storage_prefix = 'site_data'
version_date = datetime.now().strftime('%Y%m%d')
asset_description = "AKVEG site visit data for training and validation of vegetation models. Buffered data are circular representations of each site visit based on the variable 'plot_radius_m' field. See https://akveg-map.readthedocs.io/ for details. For public data use var akveg_site_visits_public_points = akveg_site_visits_points.filter(ee.Filter.eq('private', false))"

# Authenticate with Earth Engine
print('Requesting information from server...')
ee.Authenticate()
ee.Initialize(project=ee_project)

# Define asset path
asset_path = f'projects/{ee_project}/assets'

# Define feature collections
point_feature = ee.FeatureCollection(f'{asset_path}/sites/akveg_site_visit_points')
buffer_asset = f'{asset_path}/sites/akveg_site_visit_buffers'

# Check if asset exists and delete if so
try:
    ee.data.getAsset(buffer_asset)
    print(f'Asset {buffer_asset} already exists. Deleting...')
    ee.data.deleteAsset(buffer_asset)
except ee.EEException:
    pass

#### BUFFER POINT FEATURE
####____________________________________________________

# Buffer the point feature based on the 'plot_radius_m' column
print('Buffering points...')
buffer_feature = point_feature.map(lambda f: f.buffer(f.getNumber('plot_radius_m')))

# Set metadata properties
buffer_feature = buffer_feature.set({
    'versionDate': version_date,
    'description': asset_description
})

# Export the buffered points as a new Earth Engine Asset
task_buffer = ee.batch.Export.table.toAsset(
    collection=buffer_feature,
    description='akveg-buffered-points',
    assetId=buffer_asset
)
task_buffer.start()
print('Buffered points export task sent to server.')
