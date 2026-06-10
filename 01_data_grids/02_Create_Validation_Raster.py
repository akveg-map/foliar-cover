# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Create validation raster
# Author: Timm Nawrocki
# Last Updated: 2026-06-09
# Usage: Must be executed in a Python 3.12+ installation.
# Description: 'Create validation raster' creates major and minor grid indices and overlapping grid tiles from a manually-generated study area polygon.
# ---------------------------------------------------------------------------

# Import packages
import os
import time
import re
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from osgeo import gdal
from akutils import *

# Configure GDAL
gdal.UseExceptions()

#### SET UP DIRECTORIES AND FILES
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
grid_folder = os.path.join(project_folder, 'Data_Input/grid_data')

# Define input datasets
grid_input = os.path.join(grid_folder, 'AlaskaYukon_100_Tiles_3338.shp')

# Define output datasets
grid_intermediate = os.path.join(grid_folder, 'AlaskaYukon_100_Tiles_100m_3338_temp.tif')
grid_output = os.path.join(grid_folder, 'AlaskaYukon_100_Tiles_100m_3338.tif')

#### CONVERT 100 KM GRID TO RASTER
####____________________________________________________

print('Converting 100 km grid to raster...')
start_time = time.time()

# Read the 100 km shapefile
grid_data = gpd.read_file(grid_input)

# Parse grid_code to assign sequential raster values
def get_h_v(code):
    # Extracts the H and V integers from grid code format
    match = re.search(r'H(\d+)V(\d+)', code)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 0, 0

# Apply parsing to create sorting columns
h_v_tuples = [get_h_v(code) for code in grid_data['grid_code']]
grid_data['H'] = [t[0] for t in h_v_tuples]
grid_data['V'] = [t[1] for t in h_v_tuples]

# Sort features North to South (V ascending), West to East (H ascending)
grid_data = grid_data.sort_values(by=['V', 'H'], ascending=[True, True]).reset_index(drop=True)

# Assign a sequential integer value (1, 2, 3...)
grid_data['raster_val'] = range(1, len(grid_data) + 1)

# Define raster spatial properties
min_x, min_y, max_x, max_y = grid_data.total_bounds
resolution = 100
width = int(round((max_x - min_x) / resolution))
height = int(round((max_y - min_y) / resolution))

# Create the affine transform used by Rasterio
transform = from_bounds(min_x, min_y, max_x, max_y, width, height)

# Prepare a generator of (geometry, value) tuples for rasterio
shapes = ((geom, val) for geom, val in zip(grid_data.geometry, grid_data['raster_val']))

# Burn the polygon values into a numpy array
raster_array = rasterize(
    shapes=shapes,
    out_shape=(height, width),
    transform=transform,
    fill=-32768,
    dtype=rasterio.int16
)

# Define output raster profile with LZW compression
output_profile = {
    'driver': 'GTiff',
    'dtype': rasterio.int16,
    'nodata': -32768,
    'width': width,
    'height': height,
    'count': 1,
    'crs': grid_data.crs,
    'transform': transform,
    'compress': 'lzw',
    'tiled': True,
    'blockxsize': 512,
    'blockysize': 512
}

# Export the file
with rasterio.open(grid_intermediate, 'w', **output_profile) as dst:
    dst.write(raster_array, 1)

#### PROCESS CLOUD-OPTIMIZED GEOTIFF
####____________________________________________________

# Set translation options for GDAL COG driver
cog_options = gdal.TranslateOptions(
    format='COG',
    creationOptions=[
        'COMPRESS=DEFLATE',
        'PREDICTOR=2',
        'BLOCKSIZE=512',
        'NUM_THREADS=ALL_CPUS',
        'BIGTIFF=YES',
        'RESAMPLING=NEAREST',
        'OVERVIEW_RESAMPLING=NEAREST'
    ]
)

# Translate raster to cloud-optimized geotiff
print('Creating cloud-optimized raster using GDAL...')
start_time = time.time()
gdal.Translate(grid_output, grid_intermediate, options=cog_options)

# Clean up intermediate file
if os.path.exists(grid_intermediate):
    os.remove(grid_intermediate)
end_timing(start_time)
