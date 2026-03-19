# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Ingest tree model to GEE
# Author: Timm Nawrocki, Matt Macander
# Last Updated: 2026-02-26
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Ingest tree model to GEE" parses the tree strings from a text file (exported during the model training process) and initiates a task in GEE to upload the tree strings as a table asset.
# ---------------------------------------------------------------------------

# Define model targets
group = 'wetsed'
version_date = '20260212'

# Import packages
import ee
import os
from akutils import parse_treestring_text

#### SET UP ENVIRONMENT
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work/Projects/VegetationEcology/AKVEG_Map/Data'

# Define folder structure
input_folder = os.path.join(drive, root_folder,
                             f'Data_Output/model_results/version_{version_date}/{group}')

# Define input files
classifier_input = os.path.join(input_folder, f'{group}_classifier_treestring.txt')
regressor_input = os.path.join(input_folder, f'{group}_regressor_treestring.txt')

# Define paths
ee_project = 'akveg-map'

# Authenticate with Earth Engine
print('Requesting information from server...')
ee.Authenticate()
ee.Initialize(project=ee_project)

# Define paths for the model asset
classifier_asset = f'projects/{ee_project}/assets/models/foliar_cover/{group}_classifier'
regressor_asset = f'projects/{ee_project}/assets/models/foliar_cover/{group}_regressor'

# Delete classifier asset if it already exists
try:
    ee.data.getAsset(classifier_asset)
    print(f'Asset {classifier_asset} already exists. Deleting...')
    ee.data.deleteAsset(classifier_asset)
except ee.EEException:
    pass

# Delete regressor asset if it already exists
try:
    ee.data.getAsset(regressor_asset)
    print(f'Asset {regressor_asset} already exists. Deleting...')
    ee.data.deleteAsset(regressor_asset)
except ee.EEException:
    pass

#### INGEST CLASSIFIER TO GEE ASSET
####____________________________________________________

# Load treestrings from text file
classifier_strings = parse_treestring_text(classifier_input)
regressor_strings = parse_treestring_text(regressor_input)

# Create empty features and dummy geometry
classifier_features = []
regressor_features = []
dummy_geom = ee.Geometry.Point([0, 0])

# Parse the tree strings for the classifier
for i, tree_str in enumerate(classifier_strings):
    # Split the tree string into lines and join with # for GEE ingestion
    tree_lines = tree_str.splitlines()
    formatted_tree = "#".join(tree_lines)
    # Appends the tree strings with dummy geometry to a table
    classifier_features.append(ee.Feature(dummy_geom, {
        'tree': formatted_tree,
        'tree_index': i
    }))

# Parse the tree strings for the regressor
for i, tree_str in enumerate(regressor_strings):
    # Split the tree string into lines and join with # for GEE ingestion
    tree_lines = tree_str.splitlines()
    formatted_tree = "#".join(tree_lines)
    # Appends the tree strings with dummy geometry to a table
    regressor_features.append(ee.Feature(dummy_geom, {
        'tree': formatted_tree,
        'tree_index': i
    }))

# Export the classifier features to asset
task = ee.batch.Export.table.toAsset(
    collection=ee.FeatureCollection(classifier_features),
    description=f'ingest_classifier_{group}',
    assetId=classifier_asset
)
task.start()
print(f"Export task started for asset: {classifier_asset}")

# Export the regressor features to asset
task = ee.batch.Export.table.toAsset(
    collection=ee.FeatureCollection(regressor_features),
    description=f'ingest_regressor_{group}',
    assetId=regressor_asset
)
task.start()
print(f"Export task started for asset: {regressor_asset}")
