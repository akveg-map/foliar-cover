# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Compile ESA World Cover 2
# Author: Timm Nawrocki
# Last Updated: 2025-12-16
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Compile ESA World Cover 2" merges exported tiles and creates a single raster where water has a value of 1 and all other types have a value of zero.
# ---------------------------------------------------------------------------

# Import packages
import os
import glob
import time
import numpy as np
import rasterio
from osgeo import gdal
from osgeo.gdalconst import GDT_Byte
from osgeo.gdalconst import GDT_Int16
from akutils import end_timing
from akutils import raster_block_progress
from akutils import raster_bounds

# Configure GDAL
gdal.UseExceptions()
conda_prefix = r'C:\ProgramData\miniconda3\pkgs\libgdal-core-3.9.2-h6b59ad6_1'
os.environ['GDAL_DATA'] = os.environ['CONDA_PREFIX'] + r'\Library\share\gdal'
os.environ['PROJ_LIB'] = os.environ['CONDA_PREFIX'] + r'\Library\share'

# Set nodata value
nodata = -32768

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'D:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
input_folder = os.path.join(project_folder, 'Data_Input/ancillary_data/unprocessed')
output_folder = os.path.join(project_folder, 'Data_Input/ancillary_data/processed')

# Define input files
area_input = os.path.join(project_folder, 'Data_Input', 'AlaskaYukon_MapDomain_10m_3338.tif')
input_files = glob.glob(f'{input_folder}/AlaskaYukon_ESAWorldCover2*.tif')

# Define output files
esa_output = os.path.join(output_folder, 'AlaskaYukon_ESAWorldCover2_10m_3338.tif')
water_output = os.path.join(output_folder, 'AlaskaYukon_ESAWorldCover2_Water_10m_3338.tif')

#### PROCESS RASTER DATA
####____________________________________________________

# Merge tiles
if os.path.exists(esa_output) == 0:
    print(f'Merging {len(input_files)} tiles...')
    iteration_start = time.time()
    # Resample and reproject
    area_bounds = raster_bounds(area_input)
    gdal.Warp(esa_output,
              input_files,
              srcSRS='EPSG:3338',
              dstSRS='EPSG:3338',
              outputType=GDT_Int16,
              workingType=GDT_Byte,
              xRes=10,
              yRes=-10,
              srcNodata=nodata,
              dstNodata=nodata,
              outputBounds=area_bounds,
              resampleAlg='bilinear',
              targetAlignedPixels=False,
              creationOptions=['COMPRESS=LZW', 'BIGTIFF=YES'])
    end_timing(iteration_start)

# Convert to binary raster
if os.path.exists(water_output) == 0:
    print('Creating water only version...')
    iteration_start = time.time()
    esa_raster = rasterio.open(esa_output)
    area_raster = rasterio.open(area_input)
    raster_profile = esa_raster.profile.copy()
    with rasterio.open(water_output, 'w', **raster_profile) as dst:
        # Find number of raster blocks
        window_list = []
        for block_index, window in esa_raster.block_windows(1):
            window_list.append(window)
        # Iterate processing through raster blocks
        count = 1
        progress = 0
        for block_index, window in esa_raster.block_windows(1):
            raster_block = esa_raster.read(window=window,
                                           masked=True)
            area_block = area_raster.read(window=window,
                                          masked=True)
            # Replace erroneous values
            raster_block = np.where(raster_block == 80, 1, 0)
            raster_block = np.where(area_block != 1, nodata, raster_block)
            # Write results
            dst.write(raster_block,
                      window=window)
            # Report progress
            count, progress = raster_block_progress(100, len(window_list), count, progress)
    end_timing(iteration_start)
