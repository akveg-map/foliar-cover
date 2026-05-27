# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Predict probability model
# Author: Timm Nawrocki
# Last Updated: 2026-04-16
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Predict probability model" predicts a classifier probability to raster outputs.
# ---------------------------------------------------------------------------

# Set execution parameters
processors = 2
processor = 1
group = 'larlar'
version_date = '20260415'

# Import packages
import os
import pandas as pd
import geopandas as gpd
import time
import numpy as np
import rasterio
import joblib
from google.cloud import storage
from akutils import *

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Initialize GCS Client
storage_client = storage.Client()

# Define GCS base name
gcs_base = 'gs://akveg-data/foliar_cover_v2p1'

# Set root directory
drive = '/home'
root_folder = 'twnawrocki'

# Define folder structure
covariate_folder = os.path.join(drive, root_folder, 'Data_Input/covariate_data')
range_folder = os.path.join(drive, root_folder, 'Data_Input/range_data/processed')
region_folder = os.path.join(drive, root_folder, 'Data_Input/region_data')
model_folder = os.path.join(drive, root_folder,
                             f'Data_Output/model_results/version_{version_date}/{group}')
output_folder = os.path.join(drive, root_folder, f'Data_Output/rasters_gridded/version_{version_date}/{group}')

# Make output directories
if os.path.exists(model_folder) == 0:
    os.mkdir(model_folder)
if os.path.exists(output_folder) == 0:
    os.mkdir(output_folder)

# Define input files
grid_input = os.path.join(region_folder, 'AlaskaYukon_MapTiles_v2p1_3338.shp')
range_input = os.path.join(range_folder, f'range_{group}_3338.shp')
classifier_input = os.path.join(model_folder, f'{group}_classifier.joblib')

# Define covariate sets
validation = ['valid']
predictor_clim = ['summer', 'january', 'precip']
predictor_s1 = ['s1_1_vha', 's1_1_vhd', 's1_1_vva', 's1_1_vvd',
                's1_2_vha', 's1_2_vhd', 's1_2_vva', 's1_2_vvd',
                's1_3_vha', 's1_3_vhd', 's1_3_vva', 's1_3_vvd']
predictor_s2 = [f's2_{i}_{band}' for i in range(1, 6) for band in
                ['blue', 'green', 'red', 'redge1', 'redge2', 'redge3', 'nir',
                 'redge4', 'swir1', 'swir2', 'nbr', 'ngrdi', 'ndmi', 'ndsi',
                 'ndvi', 'ndwi']]
predictor_topo = ['coast', 'stream', 'river', 'wetness',
                  'elevation', 'exposure', 'heatload', 'position',
                  'aspect', 'relief', 'roughness', 'slope']

# Dynamically build predictor_all list from input arguments
predictor_names = ['clim', 'topo', 's1', 's2']
predictor_map = {
    'clim': predictor_clim, 's1': predictor_s1, 's2': predictor_s2, 'topo': predictor_topo
}
predictor_all = []
for name in predictor_names:
    if name in predictor_map:
        predictor_all.extend(predictor_map[name])
    else:
        print(f'Warning: Predictor set {name} not recognized and will be skipped.')
if not predictor_all:
    raise ValueError('No valid predictor sets were provided. Exiting.')

#### IDENTIFY PREDICTION GRIDS
####____________________________________________________

# Read grid data
grid_data = gpd.read_file(grid_input)

# Restrict the prediction grid if range dataset exists
if os.path.exists(range_input):
    # Read range data
    range_data = gpd.read_file(range_input)
    # Extract grid data to range
    grid_subset = gpd.clip(grid_data, range_data)
else:
    grid_subset = grid_data

# Define grid list
grid_list = grid_subset['grid_code'].tolist()

# Override grid list for test purposes (uncomment lines below)
#target_grids = ['AK010H199V083', 'AK010H200V083', 'AK010H199V084', 'AK010H200V084']
#grid_list = [code for code in grid_list if code in target_grids]

# Partition grid list for spatially parallel processing
total_number = len(grid_list)
processor_number = int(round((total_number / processors), 0))
slice_end = processor * processor_number
slice_start = slice_end - processor_number
grid_range = slice(slice_start, slice_end, 1)
grid_list = grid_list[grid_range]

# Create final grid data
grid_data = grid_data[grid_data['grid_code'].isin(grid_list)]
print(f'Predicting {len(grid_data)} grids...')

#### RUN MODEL PREDICTIONS
####____________________________________________________

# Download files
print('Downloading model files...')
download_from_gcs(f'{gcs_base}/model_results/{group}/{group}_classifier.joblib',
                  classifier_input, storage_client)

# Import models
classifier = joblib.load(classifier_input)

# Export model predictions for each grid in grid list
grid_count = 1
for index, row in grid_data.iterrows():
    grid = row['grid_code']
    iteration_start = time.time()
    # Define local file paths
    covariate_input = os.path.join(covariate_folder, f'{grid}_10m_3338.tif')
    probability_output = os.path.join(output_folder, f'{group}_{grid}_10m_3338.tif')

    # Define final GCS path for the output
    final_gcs_output = f'{gcs_base}/rasters_gridded/{group}/{group}_{grid}_10m_3338.tif'

    # Create output raster if it does not already exist in GCS
    if not gcs_blob_exists(final_gcs_output, storage_client):
        print(f'Predicting raster for {grid} ({grid_count} of {len(grid_list)})...')
        iteration_start = time.time()

        # Download covariate raster from Google Cloud Storage
        download_from_gcs(f'{gcs_base}/rasters_covariates/{grid}_10m_3338.tif',
                          covariate_input, storage_client)

        # Prepare raster data
        with rasterio.open(covariate_input) as covariate_raster:

            # Extract band names from covariate raster
            band_names = covariate_raster.descriptions

            # Ensure no missing bands
            missing_bands = [band for band in predictor_all if band not in band_names]
            if missing_bands:
                raise ValueError(f'\tError in {grid}: Raster missing required bands: {missing_bands}')

            # Prepare output profile
            output_profile = covariate_raster.profile.copy()
            output_profile.update({
                'count': 1,
                'nodata': -128,
                'dtype': 'int8',
                'compress': 'lzw',
                'bigtiff': 'YES',
                'tiled': True,
                'blockxsize': 512,
                'blockysize': 512
            })

            # Predict probability raster
            with rasterio.open(probability_output, 'w', **output_profile) as dst:
                # Iterate processing through raster blocks
                for block_index, window in covariate_raster.block_windows(1):
                    # Read covariate data block
                    covariate_block = covariate_raster.read(window=window, masked=False)
                    bands, rows, cols = covariate_block.shape

                    # Flatten 3D array (bands, rows, cols) to 2D tabular data (pixels, bands)
                    X_array = covariate_block.reshape(bands, -1).T
                    X_data = pd.DataFrame(X_array, columns=band_names)

                    # Reorder columns to match the covariate order
                    X_data = X_data[predictor_all]

                    # Fill null or na values
                    X_data = X_data.fillna(0)

                    # Predict response using the explicitly ordered DataFrame
                    response_probability = np.array(classifier.predict_proba(X_data)[:, 1])
                    response_probability = response_probability * 100

                    # Reshape 1D prediction back to 2D spatial block
                    response_2d = np.round(response_probability, 0).reshape(rows, cols).astype(np.int8)

                    # Write results
                    dst.write(response_2d, window=window, indexes=1)

        # Upload prediction result to GCS
        upload_to_gcs(probability_output, final_gcs_output, storage_client)

        # Remove processing datasets
        os.remove(covariate_input)
        os.remove(probability_output)
        end_timing(iteration_start)
    else:
        print(f'Raster for {grid} ({grid_count} of {len(grid_list)}) already exists.')
        print('----------')

    # Increase grid count
    grid_count += 1

# Create finished file
print('Writing final output message...')
finished_output = os.path.join(output_folder, f'0{processor}_Finished.txt')
with open(finished_output, "w") as file:
    file.write("finished")
final_gcs_output = f'{gcs_base}/rasters_gridded/{group}/0{processor}_Finished.txt'
upload_to_gcs(finished_output, final_gcs_output, storage_client)
print('Processing finished.')
