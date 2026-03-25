# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Create cloud-optimized geotiffs for climate covariates
# Author: Timm Nawrocki
# Last Updated: 2026-01-18
# Usage: Must be executed in a Python 3.12+ installation.
# Description: 'Create cloud-optimized geotiffs for climate covariates' creates cloud-optimized geotiff versions of climate covariates for use as COG-backed assets in Google Earth Engine.
# ---------------------------------------------------------------------------

# Import packages
import glob
import os
import time
from rio_cogeo.cogeo import cog_translate
from akutils import *

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
input_folder = os.path.join(drive, root_folder, 'Data/climatology/processed')
output_folder = os.path.join(drive, root_folder, 'Data/climatology/cog')

# Define input files
input_files = sorted(glob.glob(f'{input_folder}/*10m_3338.tif'))

# Print selection
print('Processing the following rasters:')
for input_file in input_files:
    print(f'\t{os.path.split(input_file)[1]}')

#### PROCESS CLOUD-OPTIMIZED GEOTIFFS
####____________________________________________________


# Define GDAL configuration for COG creation
gdal_config = {
    'GDAL_NUM_THREADS': 'ALL_CPUS',
    'GDAL_TIFF_INTERNAL_MASK': 'YES',
    'GDAL_TIFF_OVR_BLOCKSIZE': '512'
}

# Define cog profile (customized for Google Earth Engine)
cog_profile = {
    'driver': 'GTiff',
    'interleave': 'band',
    'tiled': True,
    'blockxsize': 512,
    'blockysize': 512,
    'compress': 'DEFLATE',
    'predictor': 2, # 2=int, 3=float
    'bigtiff': 'YES'
}

# Convert each raster to cloud-optimized geotiff
count = 1
for input_file in input_files:
    # Define output file
    output_file = os.path.join(output_folder, os.path.split(input_file)[1])

    # Create cloud-optimized geotiff if it does not already exist
    if not os.path.exists(output_file):
        print(f'Creating cloud-optimized raster {count} of {len(input_files)}...')
        iteration_start = time.time()

        # Translate to COG
        cog_translate(
            input_file,
            output_file,
            cog_profile,
            config=gdal_config,
            in_memory=False,
            overview_level=9,
            resampling='nearest',
            web_optimized=False,
            quiet=True
        )

        end_timing(iteration_start)

    else:
        print(f'Cloud-optimized raster {count} of {len(input_files)} already exists.')
        print('----------')
    count += 1
