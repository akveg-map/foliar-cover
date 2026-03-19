# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Convert raster grids to cloud-optimized geotiff
# Author: Timm Nawrocki
# Last Updated: 2025-01-03
# Usage: Must be executed in a Python 3.11+ installation with GDAL 3.9+.
# Description: "Convert raster grids to cloud-optimized geotiff" compiles raster grids and creates a cloud-optimized geotiff version.
# ---------------------------------------------------------------------------

# Define model targets
group = 'picsit'
range_boolean = True
barren_boolean = True
water_boolean = True
round_date = 'round_20241204_rf'
presence_threshold = 3
nodata = 255

# Import packages
import glob
import os
import time
import numpy as np
from osgeo import gdal
from osgeo.gdalconst import GDT_Byte
import rasterio
from akutils import *

# Configure GDAL
gdal.UseExceptions()

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work/Projects/VegetationEcology/AKVEG_Map/Data'

# Define folder structure
postprocess_folder = os.path.join(drive, root_folder, 'Data_Input/postprocess_v20241230')
input_folder = os.path.join(drive, root_folder, 'Data_Output/rasters_gridded', round_date, group)
intermediate_folder = os.path.join(drive, root_folder, 'Data_Output/rasters_intermediate/round_20241124')
output_folder = os.path.join(drive, root_folder, 'Data_Output/rasters_final/round_20241124')
cog_folder = os.path.join(drive, root_folder, 'Data_Output/rasters_cog/round_20241124')
if os.path.exists(intermediate_folder) == 0:
    os.mkdir(intermediate_folder)
if os.path.exists(output_folder) == 0:
    os.mkdir(output_folder)
if os.path.exists(cog_folder) == 0:
    os.mkdir(cog_folder)

# Define input files
area_input = os.path.join(postprocess_folder, 'AKVEG_FoliarCover_v2_ModelArea_3338.tif')
esa_input = os.path.join(postprocess_folder, 'AlaskaYukon_ESAWorldCover2_v2_10m_3338.tif')
if range_boolean == True:
    range_input = os.path.join(postprocess_folder, f'range_{group}_v20241226.tif')
else:
    range_input = area_input
input_files = glob.glob(f'{input_folder}/*.tif')

# Define intermediate files
merged_vrt = os.path.join(intermediate_folder, f'{group}_merged.vrt')
merged_file = os.path.join(intermediate_folder, f'{group}_merged.tif')

# Define output files
foliar_output = os.path.join(output_folder, f'{group}_10m_3338.tif')
cog_output = os.path.join(cog_folder, f'{group}_10m_3338.tif')

# Read area bounds
area_bounds = raster_bounds(area_input)

# Merge tiles
if os.path.exists(merged_file) == 0:
    print(f'Merging {len(input_files)} tiles...')
    iteration_start = time.time()
    # Merge raster tiles
    gdal.BuildVRT(merged_vrt,
                  input_files,
                  outputSRS='EPSG:3338',
                  xRes=10,
                  yRes=10,
                  srcNodata=nodata,
                  VRTNodata=nodata,
                  outputBounds=area_bounds)
    gdal.Translate(merged_file,
                   merged_vrt,
                   creationOptions=['COMPRESS=LZW', 'BIGTIFF=YES'])
    end_timing(iteration_start)
else:
    print('Merged dataset already exists.')
    print('---------')

# Apply model corrections
if os.path.exists(foliar_output) == 0:
    print(f'Enforcing model domain...')
    iteration_start = time.time()
    merged_raster = rasterio.open(merged_file)
    raster_profile = merged_raster.profile.copy()
    area_raster = rasterio.open(area_input)
    esa_raster = rasterio.open(esa_input)
    if range_boolean == True:
        range_raster = rasterio.open(range_input)
    else:
        range_raster = area_raster
    with rasterio.open(foliar_output, 'w', **raster_profile) as dst:
        # Find number of raster blocks
        window_list = []
        for block_index, window in area_raster.block_windows(1):
            window_list.append(window)
        # Iterate processing through raster blocks
        count = 1
        progress = 0
        for block_index, window in area_raster.block_windows(1):
            area_block = area_raster.read(window=window,
                                          masked=True)
            esa_block = esa_raster.read(window=window,
                                        masked=True)
            raster_block = merged_raster.read(window=window,
                                              masked=True)
            if range_boolean == True:
                range_block = range_raster.read(window=window,
                                                masked=True)
            # Set no data to zero
            raster_block = np.where((raster_block >= presence_threshold) & (raster_block <= 100), raster_block, 0)
            # Remove snow/ice
            raster_block = np.where(esa_block == 70, 0, raster_block)
            # Remove anthropogenic
            raster_block = np.where(esa_block == 50, 0, raster_block)
            # Remove barren
            if barren_boolean == True:
                raster_block = np.where(esa_block == 60, 0, raster_block)
            # Remove water
            if water_boolean == True:
                raster_block = np.where(esa_block == 80, 0, raster_block)
            # Enforce range
            if range_boolean == True:
                raster_block = np.where(range_block == 1, raster_block, 0)
            # Enforce study area boundary
            raster_block = np.where(area_block == 1, raster_block, nodata)
            # Write results
            dst.write(raster_block,
                      window=window)
            # Report progress
            count, progress = raster_block_progress(100, len(window_list), count, progress)
    end_timing(iteration_start)
else:
    print('Model domain already enforced.')
    print('----------')

# Create cloud-optimized geotiff if it does not already exist
if os.path.exists(cog_output) == 0:
    print(f'Creating cloud-optimized raster...')
    iteration_start = time.time()
    # Execute GDAL translate
    gdal.Translate(cog_output,
                   foliar_output,
                   format='COG',
                   creationOptions=['BLOCKSIZE=256',
                                    'COMPRESS=DEFLATE',
                                    'LEVEL=9',
                                    'PREDICTOR=STANDARD',
                                    'BIGTIFF=YES'])
    end_timing(iteration_start)
else:
    print(f'Cloud-optimized raster already exists.')
    print('----------')

# Build pyramids
print('Building pyramids...')
iteration_start = time.time()
foliar_raster = gdal.Open(foliar_output, 0)  # 0 = read-only, 1 = read-write.
gdal.SetConfigOption('COMPRESS_OVERVIEW', 'LZW')
gdal.SetConfigOption('BIGTIFF_OVERVIEW', 'YES')
foliar_raster.BuildOverviews('BILINEAR', [2, 4, 8, 16, 32, 64, 128, 256], gdal.TermProgress_nocb)
del foliar_raster  # close the dataset (Python object and pointers)
end_timing(iteration_start)
