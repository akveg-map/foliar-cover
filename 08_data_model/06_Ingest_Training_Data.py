# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Ingest training data
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-02-25
# Usage: Must be executed in a Python 3.12+ installation with authentication to Google Earth Engine.
# Description: "Ingest training data" translates the exported csv file of site visit training data to an asset in Google Earth Engine. The csv file should be in a Google Cloud Storage Bucket for the project.
# ---------------------------------------------------------------------------

# Import packages
import ee
from google.auth.transport.requests import AuthorizedSession
from datetime import datetime

#### SET UP ENVIRONMENT
####____________________________________________________

# Define paths
ee_project = 'akveg-map'
storage_bucket = 'akveg-data'
storage_prefix = 'site_data'
version_date = datetime.now().strftime('%Y%m%d')
asset_description = "AKVEG site visit data for training and validation of vegetation models. See https://akveg-map.readthedocs.io/ for details. For public data use var akveg_site_visits_public_points = akveg_site_visits_points.filter(ee.Filter.eq('private', false))"

# Authenticate with Earth Engine
print('Requesting information from server...')
ee.Authenticate()
ee.Initialize(project=ee_project)

# Specify the cloud project you want associated with Earth Engine requests.
session = AuthorizedSession(
  ee.data.get_persistent_credentials().with_quota_project(ee_project)
)

# Define paths
csv_path = f'gs://{storage_bucket}/{storage_prefix}/akveg_site_visits_3338.csv'
asset_id = f'projects/{ee_project}/assets/sites/akveg_site_visit_points'

# Check if asset exists and delete if so
try:
    ee.data.getAsset(asset_id)
    print(f'Asset {asset_id} already exists. Deleting...')
    ee.data.deleteAsset(asset_id)
except ee.EEException:
    pass

#### INGEST DATA TO GEE ASSET
####____________________________________________________

# Define the ingestion parameters
ingestion_params = {
    'id': asset_id,
    'sources': [
        {
            'uris': [csv_path],
            'xColumn': 'cent_x',
            'yColumn': 'cent_y',
            'crs': 'EPSG:3338'
        }
    ],
    'properties': {
        'versionDate': version_date,
        'description': asset_description
    }
}

# Generate a unique task ID for the Earth Engine batch system
task_id = ee.data.newTaskId()[0]

# Submit the ingestion task
print(f'Starting table ingestion. Task ID: {task_id}')
ee.data.startTableIngestion(request_id=task_id, params=ingestion_params)
