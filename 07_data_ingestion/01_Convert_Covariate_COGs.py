# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Create cloud-optimized geotiffs for covariates
# Author: Timm Nawrocki
# Last Updated: 2025-12-16
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Create cloud-optimized geotiffs for covariates" creates cloud-optimized geotiff versions of all covariates for use as COG-backed assets in Google Earth Engine.
# ---------------------------------------------------------------------------

# Import packages
import glob
import os
import time
from osgeo import gdal

# Configure GDAL
gdal.UseExceptions()

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = '/home'
root_folder = 'twnawrocki'

# Define folder structure
input_folder = os.path.join(drive, root_folder, 'covariates')
output_folder = os.path.join(drive, root_folder, 'covariates_v20240711')

# Define input files
input_files = sorted(glob.glob(f'{input_folder}/*.tif'))
# Subset input files
input_files = [input_files[i] for i in [1, 2]]
# Print subset selection to check
print('Processing the following rasters:')
for input_file in input_files:
    print(f'\t{os.path.split(input_file)[1]}')

#### PROCESS CLOUD-OPTIMIZED GEOTIFFS
####____________________________________________________

# Convert each raster to cloud-optimized geotiff
count = 1
for input_file in input_files[:]:
    # Define output file
    output_file = os.path.join(output_folder, os.path.split(input_file)[1])

    # Create cloud-optimized geotiff if it does not already exist
    if os.path.exists(output_file) == 0:
        print(f'Creating cloud-optimized raster {count} of {len(input_files)}...')
        fmt_start = time.gmtime()
        print(f'\t{time.strftime("%D %T", fmt_start)}')
        # Execute GDAL translate
        gdal.Translate(output_file,
                       input_file,
                       format='COG',
                       creationOptions=['BLOCKSIZE=256',
                                        'COMPRESS=DEFLATE',
                                        'LEVEL=9',
                                        'PREDICTOR=STANDARD',
                                        'BIGTIFF=YES'])
        print(f'\tFinished creating cloud-optimized raster {count} of {len(input_files)}.')
        fmt_end = time.gmtime()
        print(f'\t{time.strftime("%D %T", fmt_end)}')
        print('----------')
    else:
        print(f'Cloud-optimized raster {count} of {len(input_files)} already exists.')
        print('----------')
    count += 1
