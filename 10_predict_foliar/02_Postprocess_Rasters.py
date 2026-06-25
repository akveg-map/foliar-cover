# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Convert raster grids to cloud-optimized geotiff
# Author: Timm Nawrocki
# Last Updated: 2026-05-27
# Usage: Must be executed in a Python 3.11+ installation with GDAL 3.9+.
# Description: 'Convert raster grids to cloud-optimized geotiff' compiles raster grids and creates a cloud-optimized geotiff version.
# ---------------------------------------------------------------------------

# Define model targets
group = 'alnus'
destination = 'rasters_final'
nodata_value = -128

# Import packages
import glob
import os
import shutil
import time
import numpy as np
from osgeo import gdal
from osgeo.gdalconst import GDT_Int8
import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
from google.cloud import storage
from akutils import *

# Configure GDAL
gdal.UseExceptions()

# Define diagnostic species lists
barren_retain = ['beach', 'dryas', 'dsalix', 'empnig', 'forb', 'gramin', 'halgra', 'lichen', 'nerishr', 'vacvit']
water_retain = ['beach', 'bromos', 'halgra', 'mwcalama', 'sphagn', 'wetforb', 'wetgram', 'wetsed']
dist_list = ['abies', 'bromos', 'calnoo', 'larlar', 'pinus', 'wetgram']

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Initialize GCS Client
storage_client = storage.Client()

# Define GCS base name
gcs_base = 'gs://akveg-data/foliar_cover_v2p1'

# Define final GCS path for the output
if group in dist_list:
    output_name = f'{group}_dst_10m_3338.tif'
else:
    output_name = f'{group}_cvr_10m_3338.tif'
final_gcs_output = f'{gcs_base}/{destination}/{output_name}'

# Set root directory
drive = '/home'
root_folder = 'twnawrocki'

# Define folder structure
input_folder = os.path.join(drive, root_folder, f'Data_Output/rasters_gridded', group)
range_folder = os.path.join(drive, root_folder, 'Data_Input/range_data/processed')
region_folder = os.path.join(drive, root_folder, 'Data_Input/region_data')
ancillary_folder = os.path.join(drive, root_folder, 'Data_Input/ancillary_data')
intermediate_folder = os.path.join(drive, root_folder, f'Data_Output/rasters_intermediate')
output_folder = os.path.join(drive, root_folder, f'Data_Output/rasters_final')

# Make output directories
if os.path.exists(input_folder):
    shutil.rmtree(input_folder)
if not os.path.exists(input_folder):
    os.mkdir(input_folder)
if not os.path.exists(intermediate_folder):
    os.mkdir(intermediate_folder)
if not os.path.exists(output_folder):
    os.mkdir(output_folder)

# Define input files
area_input = os.path.join(region_folder, 'AlaskaYukon_MapDomain_v2p1_10m_3338.tif')
esa_input = os.path.join(ancillary_folder, 'AlaskaYukon_ESAWorldCover2_10m_3338.tif')
range_input = os.path.join(range_folder, f'range_{group}_3338.shp')

# Define intermediate files
range_intermediate = os.path.join(intermediate_folder, f'range_{group}_10m_3338.tif')
vrt_intermediate = os.path.join(intermediate_folder, f'{group}_merged.vrt')
merged_intermediate = os.path.join(intermediate_folder, f'{group}_merged.tif')

# Define output files
foliar_output = os.path.join(output_folder, output_name)

#### CONVERT RANGE TO RASTER
####____________________________________________________

# Read area bounds
area_bounds = raster_bounds(area_input)

# Set output raster options
range_options = gdal.RasterizeOptions(
    format='GTiff',
    outputType=gdal.GDT_Int8,
    creationOptions=[
        'COMPRESS=LZW',
        'TILED=YES',
        'BIGTIFF=YES',
        'NUM_THREADS=ALL_CPUS'
    ],
    outputBounds=area_bounds,
    xRes=10,
    yRes=10,
    initValues=[0],
    burnValues=[1],
    noData= nodata_value,
    allTouched=False
)

# Convert the range to raster if the range exists but the raster does not
if os.path.exists(range_input):
    if not os.path.exists(range_intermediate):
        print(f'Converting {group} range to raster...')
        start_time = time.time()
        gdal.Rasterize(range_intermediate, range_input, options=range_options)
        end_timing(start_time)
else:
    range_intermediate = area_input

#### DOWNLOAD RASTER TILES
####____________________________________________________

# Identify all raster tiles in target folder on Google Cloud Storage
raster_tiles = gcs_list_files(f'{gcs_base}/rasters_gridded/{group}', storage_client, extension='.tif')

# Download each raster tile to local folder
tile_count = 1
print('Downloading raster tiles...')
start_time = time.time()
for raster_uri in raster_tiles:
    if tile_count % 1000 == 0 or tile_count == len(raster_tiles):
        print(f'\tDownloading tile {tile_count} of {len(raster_tiles)}...')
    # Extract filename from uri
    file_name = os.path.split(raster_uri)[1]
    # Define the local download path
    raster_file = os.path.join(input_folder, file_name)
    # Download raster tile
    download_from_gcs(raster_uri, raster_file, storage_client)
    # Check and update nodata value if it does not match the specified nodata value
    with rasterio.open(raster_file, 'r+') as src:
        current_nodata = src.nodata
        if current_nodata != nodata_value:
            # Read the pixel array
            data = src.read(1)
            # Replace erroneous nodata values
            data = np.where(data == current_nodata, nodata_value, data)
            # Write the updated array back to disk
            src.write(data, 1)
            # Update the file's internal metadata
            src.nodata = nodata_value
    # Increase count
    tile_count += 1

# Report outcome
end_timing(start_time)

#### MERGE RASTER TILES
####____________________________________________________

# Define input files
input_files = glob.glob(f'{input_folder}/*.tif')

# Merge tiles
print(f'Merging {len(input_files)} tiles...')
start_time = time.time()
# Merge raster tiles
gdal.BuildVRT(vrt_intermediate,
              input_files,
              outputSRS='EPSG:3338',
              xRes=10,
              yRes=10,
              srcNodata=nodata_value,
              VRTNodata=nodata_value,
              outputBounds=area_bounds)
end_timing(start_time)

# Prepare output data profile
print(f'Applying post-processing corrections...')
start_time = time.time()
area_raster = rasterio.open(area_input)
output_profile = area_raster.profile.copy()
output_profile.update({
    'count': 1,
    'nodata': nodata_value,
    'dtype': 'int8',
    'compress': 'lzw',
    'bigtiff': 'YES',
    'tiled': True,
    'blockxsize': 512,
    'blockysize': 512
})

# Prepare raster data
foliar_raster = rasterio.open(vrt_intermediate)
esa_raster = rasterio.open(esa_input)
range_raster = rasterio.open(range_intermediate)

# Post-process foliar cover raster
with rasterio.open(merged_intermediate, 'w', **output_profile) as dst:
    # Find number of raster blocks
    window_list = []
    for block_index, window in area_raster.block_windows(1):
        window_list.append(window)
    # Iterate processing through raster blocks
    count = 1
    progress = 0
    for block_index, window in area_raster.block_windows(1):

        # Load area block
        area_block = area_raster.read(1, window=window, masked=False)

        # Compute bounds of the current output window
        window_bounds = rasterio.windows.bounds(window, area_raster.transform)

        # Load raster blocks
        foliar_block = read_raster_block(foliar_raster, window_bounds, pad_value=nodata_value)
        esa_block = read_raster_block(esa_raster, window_bounds)

        # Set no data to zero
        raster_block = np.where(foliar_block == nodata_value, 0, foliar_block)

        # Remove snow/ice
        raster_block = np.where(esa_block == 70, 0, raster_block)

        # Remove barren
        if group not in barren_retain:
            raster_block = np.where(esa_block == 60, 0, raster_block)

        # Remove water
        if group not in water_retain:
            raster_block = np.where(esa_block == 80, 0, raster_block)

        # Enforce range
        if os.path.exists(range_input):
            range_block = read_raster_block(range_raster, window_bounds)
            raster_block = np.where(range_block == 1, raster_block, 0)

        # Enforce study area boundary
        raster_block = np.where(area_block == 1, raster_block, nodata_value)

        # Write results
        dst.write(raster_block.astype('int8'), 1, window=window)

        # Report progress
        count, progress = raster_block_progress(100, len(window_list), count, progress)
end_timing(start_time)

# Close rasters
for raster in [area_raster, foliar_raster, esa_raster, range_raster]:
    raster.close()

#### PROCESS CLOUD-OPTIMIZED GEOTIFFS
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
        'RESAMPLING=BILINEAR',
        'OVERVIEW_RESAMPLING=AVERAGE'
    ]
)

# Translate raster to cloud-optimized geotiff
print(f'Creating cloud-optimized raster using GDAL...')
start_time = time.time()
gdal.Translate(foliar_output, merged_intermediate, options=cog_options)
end_timing(start_time)

# Upload post-processed raster to GCS
upload_to_gcs(foliar_output, final_gcs_output, storage_client)

# Create finished file
print('Writing final output message...')
finished_output = os.path.join(output_folder, f'{group}_Finished.txt')
with open(finished_output, "w") as file:
    file.write("finished")
final_gcs_output = f'{gcs_base}/{destination}/{group}_Finished.txt'
upload_to_gcs(finished_output, final_gcs_output, storage_client)
print('Processing finished.')
