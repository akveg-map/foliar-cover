# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Compile most recent fire year
# Author: Timm Nawrocki
# Last Updated: 2025-12-16
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Compile most recent fire year" combines exported tiles to a single raster.
# ---------------------------------------------------------------------------

# Import packages
import os
import glob
import time
from osgeo import gdal
from osgeo.gdalconst import GDT_Int16
from akutils import end_timing
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
input_files = glob.glob(f'{input_folder}/AlaskaYukon_FireYear*.tif')

# Define output files
fire_output = os.path.join(output_folder, 'AlaskaYukon_FireYear_10m_3338.tif')

#### PROCESS RASTER DATA
####____________________________________________________

# Merge tiles
print(f'Merging {len(input_files)} tiles...')
iteration_start = time.time()
# Resample and reproject
area_bounds = raster_bounds(area_input)
gdal.Warp(fire_output,
          input_files,
          srcSRS='EPSG:3338',
          dstSRS='EPSG:3338',
          outputType=GDT_Int16,
          workingType=GDT_Int16,
          xRes=10,
          yRes=-10,
          srcNodata=nodata,
          dstNodata=nodata,
          outputBounds=area_bounds,
          resampleAlg = 'bilinear',
          targetAlignedPixels=False,
          creationOptions = ['COMPRESS=LZW', 'BIGTIFF=YES'])
end_timing(iteration_start)
