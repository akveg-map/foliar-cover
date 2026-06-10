# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Ingest validation grid to GEE
# Author: Timm Nawrocki
# Last Updated: 2025-12-16
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Ingest validation grid to GEE" creates a COG-backed asset for the validation grid in Google Earth Engine (GEE).
# ---------------------------------------------------------------------------

# Import packages
import ee
import json
import os
import re
from google.auth.transport.requests import AuthorizedSession
from google.cloud import storage
from pprint import pprint

#### SET UP GEE ENVIRONMENT
####____________________________________________________

# Define paths
ee_project = 'akveg-map'
storage_bucket = 'akveg-data'
storage_prefix = 'validation_v20240729'

# Authenticate with Earth Engine
print('Requesting information from server...')
ee.Authenticate()
ee.Initialize(project=ee_project)

# Specify the cloud project you want associated with Earth Engine requests.
session = AuthorizedSession(
  ee.data.get_persistent_credentials().with_quota_project(ee_project)
)

# Request list of storage objects
client = storage.Client()
file_list = []
for blob in client.list_blobs(storage_bucket, prefix=storage_prefix):
  file_list.append(blob.name)

# Filter the list to geotiffs in the
reg = re.compile(r'^' + storage_prefix + r'/.*.tif$')
geotiff_list = list(filter(reg.search, file_list))

# Get list of GEE assets
asset_list = []
for asset in ee.data.listAssets(f'projects/{ee_project}/assets/{storage_prefix}')['assets']:
  asset_list.append(os.path.split(asset['name'])[1] + '.tif')

#### INGEST COG INTO GEE
####____________________________________________________

# Ingest each geotiff in the storage folder
for geotiff in geotiff_list:
  # Define file name
  file_name = os.path.split(geotiff)[1]
  # Ingest asset if it does not already exist
  if file_name not in asset_list:
      print(f'Ingesting {file_name} as a COG-backed asset...')

      # Request body as a dictionary.
      request = {
        'type': 'IMAGE',
        'gcs_location': {
          'uris': [f'gs://{storage_bucket}/{storage_prefix}/{file_name}']
        },
        'properties': {
          'source': 'https://github.com/accs-uaa/akveg-map'
        },
        'startTime': '2024-01-01T00:00:00.000000000Z',
        'endTime': '2024-12-31T15:01:23.000000000Z',
      }
      pprint(json.dumps(request))

      # Specify a folder (or ImageCollection) name and the new asset name.
      asset_id = f'{storage_prefix}/{os.path.splitext(file_name)[0]}'

      # Define the request url
      url = 'https://earthengine.googleapis.com/v1alpha/projects/{}/assets?assetId={}'

      # Post the request
      response = session.post(
        url=url.format(ee_project, asset_id),
        data=json.dumps(request)
      )
      pprint(json.loads(response.content))
  else:
    print(f'{file_name} has already been ingested as a COG-backed asset.')
