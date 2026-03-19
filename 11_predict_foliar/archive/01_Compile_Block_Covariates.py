# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Compile block covariates
# Author: Timm Nawrocki
# Last Updated: 2024-10-14
# Usage: Must be executed in an Anaconda Python 3.12+ installation.
# Description: "Compile block covariates" creates tables stored on disk for covariates from each block window of each grid raster.
# ---------------------------------------------------------------------------

# Import packages
import os
import pandas as pd
import time
import numpy as np
import rasterio
from akutils import *

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set processor
processor = 1

# Set root directory
drive = '/home'
root_folder = 'twnawrocki'

# Define folder structure
script_folder = os.path.join(drive, root_folder, 'scripts')
covariate_folder = os.path.join(drive, root_folder, 'data_input/covariates_050')
grid_folder = os.path.join(drive, root_folder, 'data_input/grid_050')
table_folder = os.path.join(drive, root_folder, 'data_output/covariate_parquet')

# Define input files
covariate_input = os.path.join(script_folder, '00_Covariates.csv')
list_input = os.path.join(script_folder, '00_PredictionGrid_050_v20241127.csv')

# Define grid list
grid_list = pd.read_csv(list_input)
grid_list = grid_list[grid_list['processor'] == processor]

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

# Export covariate tables for each grid in grid list
grid_count = 1
for grid in grid_list['grid_code']:
    # Define input grid file
    grid_input = os.path.join(grid_folder, f'{grid}_10m_3338.tif')
    print(f'Processing covariate tables for {grid} ({grid_count} out of {len(grid_list)})...')
    iteration_start = time.time()

    # Define output folder
    output_folder = os.path.join(table_folder, grid)
    if os.path.exists(output_folder) == 0:
        os.mkdir(output_folder)

    # Read covariate input
    covariate_metadata = pd.read_csv(covariate_input)
    covariate_metadata['raster'] = np.where(
        covariate_metadata['alt_grid'] == 0,
        covariate_metadata['raster_prefix'] + grid + covariate_metadata['raster_suffix'],
        covariate_metadata['raster_prefix']
        + grid.replace('H0', 'H').replace('V0', 'V')
        + covariate_metadata['raster_suffix'])

    # Prepare raster data
    grid_raster = rasterio.open(grid_input)

    # Find number of raster blocks
    window_list = []
    for block_index, window in grid_raster.block_windows(1):
        window_list.append(window)

    # Iterate processing through raster blocks
    count = 1
    progress = 0
    for block_index, window in grid_raster.block_windows(1):

        # Define output table
        if count < 10:
            table_output = os.path.join(output_folder, grid + f'_00{count}.parquet')
        elif count < 100:
            table_output = os.path.join(output_folder, grid + f'_0{count}.parquet')
        else:
            table_output = os.path.join(output_folder, grid + f'_{count}.parquet')

        # Process covariate data for block if it does not already exist
        if os.path.exists(table_output) == 0:
            print(f'\tProcessing {grid} block {count} of {len(window_list)}...')

            # Define block shape
            block_shape = grid_raster.read(1, window=window, masked=False).shape

            # Define empty data structures
            data_block = []
            predictor_list = []

            # Add each covariate to data block
            covariate_count = 1
            while covariate_count <= len(covariate_metadata):
                raster_input = os.path.join(covariate_folder,
                                        covariate_metadata.query(f'order=={covariate_count}')['raster'].item())
                raster_band = int(covariate_metadata.query(f'order=={covariate_count}')['band'].item())
                covariate_name = covariate_metadata.query(f'order=={covariate_count}')['covariate'].item()
                raster_open = rasterio.open(raster_input)
                raster_block = raster_open.read(raster_band, window=window, masked=False).flatten()
                raster_open.close()
                data_block.append(raster_block)
                predictor_list.append(covariate_name)
                covariate_count += 1

            # Transpose data block
            X_array = np.asarray(data_block).T

            # Convert to dataframe
            covariate_data = pd.DataFrame(data=X_array, columns=predictor_list)
            covariate_data = foliar_cover_predictors(covariate_data, predictor_all)
            export_data = covariate_data[predictor_all].copy()

            # Write result
            export_data.to_parquet(table_output, compression='brotli')

        else:
            print(f'\tCovariate table {grid} block {count} of {len(window_list)} already exists.')

        # Increase count
        count += 1
    # Increase count
    grid_count += 1
    end_timing(iteration_start)
