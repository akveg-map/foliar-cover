# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Predict abundance model
# Author: Timm Nawrocki
# Last Updated: 2024-11-27
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Predict abundance model" predicts a classifier and regressor to raster outputs.
# ---------------------------------------------------------------------------

# Define model targets
group = 'poptre'
block = 1
round_date = 'round_20241204_rf'
presence_threshold = 3

# Import packages
import os
import pandas as pd
import time
import numpy as np
import rasterio
from akutils import *
import joblib

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'D:/'
root_folder = 'ACCS_Work/Projects/VegetationEcology/AKVEG_Map/Data'

# Define folder structure
covariate_folder = os.path.join(drive, root_folder, 'Data_Output/covariate_tables')
grid_folder = os.path.join(drive, root_folder, 'Data_Input/grid_050')
model_folder = os.path.join(drive, root_folder, 'Data_Output/model_results', round_date, group)
output_folder = os.path.join(drive, root_folder, 'Data_Output/rasters_gridded', round_date, group)
if os.path.exists(output_folder) == 0:
    os.mkdir(output_folder)

# Define input files
threshold_input = os.path.join(model_folder, f'{group}_threshold_final.txt')
classifier_input = os.path.join(model_folder, f'{group}_classifier.joblib')
regressor_input = os.path.join(model_folder, f'{group}_regressor.joblib')
table_input = os.path.join(covariate_folder, '00_PredictionGrid_050_v20241127.csv')

# Define variable sets
predictor_all = ['summer', 'january', 'precip',
                 'coast', 'stream', 'river', 'wetness',
                 'elevation', 'exposure', 'heatload', 'position',
                 'aspect', 'relief', 'roughness', 'slope',
                 's1_1_vha', 's1_1_vhd', 's1_1_vva', 's1_1_vvd',
                 's1_2_vha', 's1_2_vhd', 's1_2_vva', 's1_2_vvd',
                 's1_3_vha', 's1_3_vhd', 's1_3_vva', 's1_3_vvd',
                 's2_1_blue', 's2_1_green', 's2_1_red', 's2_1_redge1', 's2_1_redge2',
                 's2_1_redge3', 's2_1_nir', 's2_1_redge4', 's2_1_swir1', 's2_1_swir2',
                 's2_1_nbr', 's2_1_ngrdi', 's2_1_ndmi', 's2_1_ndsi', 's2_1_ndvi', 's2_1_ndwi',
                 's2_2_blue', 's2_2_green', 's2_2_red', 's2_2_redge1', 's2_2_redge2',
                 's2_2_redge3', 's2_2_nir', 's2_2_redge4', 's2_2_swir1', 's2_2_swir2',
                 's2_2_nbr', 's2_2_ngrdi', 's2_2_ndmi', 's2_2_ndsi', 's2_2_ndvi', 's2_2_ndwi',
                 's2_3_blue', 's2_3_green', 's2_3_red', 's2_3_redge1', 's2_3_redge2',
                 's2_3_redge3', 's2_3_nir', 's2_3_redge4', 's2_3_swir1', 's2_3_swir2',
                 's2_3_nbr', 's2_3_ngrdi', 's2_3_ndmi', 's2_3_ndsi', 's2_3_ndvi', 's2_3_ndwi',
                 's2_4_blue', 's2_4_green', 's2_4_red', 's2_4_redge1', 's2_4_redge2',
                 's2_4_redge3', 's2_4_nir', 's2_4_redge4', 's2_4_swir1', 's2_4_swir2',
                 's2_4_nbr', 's2_4_ngrdi', 's2_4_ndmi', 's2_4_ndsi', 's2_4_ndvi', 's2_4_ndwi',
                 's2_5_blue', 's2_5_green', 's2_5_red', 's2_5_redge1', 's2_5_redge2',
                 's2_5_redge3', 's2_5_nir', 's2_5_redge4', 's2_5_swir1', 's2_5_swir2',
                 's2_5_nbr', 's2_5_ngrdi', 's2_5_ndmi', 's2_5_ndsi', 's2_5_ndvi', 's2_5_ndwi']

# Read grid table
grid_data = pd.read_csv(table_input)

# Pull grid list
grid_data = grid_data[grid_data['processor'] == block]
if group in ['bettre', 'picgla', 'picmar', 'poptre']:
    grid_data = grid_data[grid_data['dist_boreal'] == True]
elif group in ['picsit', 'tsumer']:
    grid_data = grid_data[grid_data['dist_temp'] == True]
elif group == 'rubspe':
    grid_data = grid_data[grid_data['dist_south'] == True]
print(f'Predicting {len(grid_data)} grids...')
grid_list = grid_data['grid_code'].tolist()

# Read threshold
threshold_reader = open(threshold_input, "r")
threshold = float(threshold_reader.readlines()[0])
threshold_reader.close()

# Import models
classifier = joblib.load(classifier_input)
regressor = joblib.load(regressor_input)

# Export model predictions for each grid in grid list
grid_count = 1
for grid in grid_list:
    # Define output file
    grid_input = os.path.join(grid_folder, f'{grid}_10m_3338.tif')
    predict_output = os.path.join(output_folder, f'{group}_{grid}_10m_3338.tif')

    # Create output raster if it does not already exist
    if os.path.exists(predict_output) == 0:
        print(f'Predicting raster for {grid} ({grid_count} of {len(grid_list)})...')
        iteration_start = time.time()

        # Define input folder
        input_folder = os.path.join(covariate_folder, grid)

        # Prepare raster data
        grid_raster = rasterio.open(grid_input)
        input_profile = grid_raster.profile.copy()
        input_profile.update(count=1)
        with rasterio.open(predict_output, 'w', **input_profile, BIGTIFF='YES') as dst:
            # Find number of raster blocks
            window_list = []
            for block_index, window in grid_raster.block_windows(1):
                window_list.append(window)
            # Iterate processing through raster blocks
            count = 1
            progress = 0
            for block_index, window in grid_raster.block_windows(1):

                # Define input file
                if count < 10:
                    covariate_input = os.path.join(input_folder, grid + f'_00{count}.parquet')
                elif count < 100:
                    covariate_input = os.path.join(input_folder, grid + f'_0{count}.parquet')
                else:
                    covariate_input = os.path.join(input_folder, grid + f'_{count}.parquet')

                # Define block shape
                block_shape = grid_raster.read(1, window=window, masked=False).shape

                # Convert to dataframe
                covariate_data = pd.read_parquet(covariate_input)
                covariate_data = covariate_data[predictor_all]

                # Predict response
                response_probability = np.array(classifier.predict_proba(covariate_data)[:, 1])
                response_abundance = np.array(regressor.predict(covariate_data))
                response_output = np.where(response_probability >= threshold, response_abundance, 0)
                response_output = np.where(response_output < presence_threshold, 0, response_output)
                response_output = np.where(response_output > 100, 100, response_output)
                response_output = np.round(response_output, 0)
                response_2d = response_output.reshape(block_shape[0], block_shape[1])

                # Write results
                dst.write(response_2d,
                          window=window,
                          indexes=1)
                # Report progress
                count, progress = raster_block_progress(100, len(window_list), count, progress)
        end_timing(iteration_start)
    else:
        print(f'Raster for {grid} ({grid_count} of {len(grid_list)}) already exists.')
        print('----------')
    # Increase grid count
    grid_count += 1
