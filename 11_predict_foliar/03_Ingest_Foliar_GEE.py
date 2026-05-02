# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Ingest foliar cover data
# Author: Timm Nawrocki
# Last Updated: 2026-04-28
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Ingest foliar cover data" creates COG-backed assets for a folder foliar cover map geotiffs in GEE.
# ---------------------------------------------------------------------------

# Import packages
import ee
import os
import re
from google.cloud import storage

# Define diagnostic set list
target_list = ['abies']
dist_list = ['abies', 'bromos', 'calnoo', 'larlar', 'pinus', 'wetgram']

#### SET UP GEE ENVIRONMENT
####____________________________________________________

# Define paths
ee_project = 'akveg-map'
ee_prefix = 'foliar_cover_v2p1'
storage_bucket = 'akveg-data'
storage_prefix = 'foliar_cover_v2p1/rasters_cog'

# Authenticate with Earth Engine
print('Requesting information from server...')
ee.Authenticate()
ee.Initialize(project=ee_project)

# Ensure the parent ImageCollection exists in GEE
parent_asset_id = f'projects/{ee_project}/assets/{ee_prefix}'
try:
    ee.data.getAsset(parent_asset_id)
    print(f"Parent asset found: {parent_asset_id}")
except ee.EEException:
    print(f"Parent asset not found. Creating ImageCollection: {parent_asset_id}")
    ee.data.createAsset(
        {'type': 'IMAGE_COLLECTION'},
        parent_asset_id
    )

# Get list of existing GEE assets to avoid duplicates
existing_assets = []
# We use a try/except here in case the folder was just created and is empty
try:
    assets_response = ee.data.listAssets({'parent': parent_asset_id})
    if 'assets' in assets_response:
        for asset in assets_response['assets']:
            # Extract just the filename part for comparison
            existing_assets.append(os.path.basename(asset['name']) + '.tif')
except ee.EEException as e:
    print(f"Error listing assets (folder might be empty): {e}")

#### INGEST COGS INTO GEE
####____________________________________________________

# Send ingestion request for each geotiff
for group in target_list:
    # Define file name
    if group in dist_list:
        file_name = f'{group}_Dst_10m_3338.tif'
    else:
        file_name = f'{group}_Cvr_10m_3338.tif'

    # Define the target asset ID
    asset_name = os.path.splitext(file_name)[0]
    full_asset_id = f'{parent_asset_id}/{asset_name}'

    # Ingest asset if it does not already exist
    if file_name not in existing_assets:
        print(f'Ingesting {file_name} as a COG-backed asset...')

        # Request body using the Python Client syntax
        request = {
            'type': 'IMAGE',
            'gcs_location': {
                'uris': [f'gs://{storage_bucket}/{storage_prefix}/{file_name}']
            },
            'properties': {
                'source': 'https://github.com/accs-uaa/akveg-map',
                'original_filename': file_name
            },
            'startTime': '2023-01-01T00:00:00Z',
            'endTime': '2023-12-31T15:01:23Z',
        }

        try:
            # Use the native library method instead of manual requests
            ee.data.createAsset(request, full_asset_id)
            print(f'Successfully created: {asset_name}')
        except ee.EEException as e:
            print(f'Failed to create {file_name}: {e}')

    else:
        print(f'{file_name} already exists. Skipping.')
