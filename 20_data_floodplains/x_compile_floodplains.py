# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Compile floodplains
# Author: Timm Nawrocki
# Last Updated: 2026-03-24
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Compile floodplains" combines floodplains tiles into a single raster output.
# ---------------------------------------------------------------------------

# Import packages
import os
import glob
import time
import rasterio
from rasterio.windows import from_bounds, Window
from rasterio.enums import Resampling
from akutils import *

# Set nodata value
nodata_value = 255

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
floodplains_folder = os.path.join(project_folder, 'Data_Output/physiography_data/floodplains/version_20260320')
input_folder = os.path.join(floodplains_folder, 'unprocessed')
output_folder = os.path.join(floodplains_folder, 'processed')

# Define input files
area_input = os.path.join(project_folder, 'Data_Input', 'AlaskaYukon_MapDomain_10m_3338.tif')
input_files = glob.glob(f'{input_folder}/*.tif')

# Define output files
floodplain_output = os.path.join(output_folder, 'Floodplains_10m_3338_v20260320.tif')

# Calculate half of the available CPUs
total_cpus = os.cpu_count() or 1
half_cpus = max(1, total_cpus // 2)
print(half_cpus)

# Define GDAL environment configuration
rasterio_env = rasterio.Env(
    GDAL_NUM_THREADS=str(half_cpus),
    GDAL_TIFF_INTERNAL_MASK='YES',
    GDAL_TIFF_OVR_BLOCKSIZE='512'
)

#### CREATE COMPOSITE RASTER
####____________________________________________________
print(f'Merging input rasters...')
iteration_start = time.time()

# Get the transform and dimensions of the area raster
with rasterio.open(area_input) as area_raster:
    output_profile = area_raster.meta.copy()
    area_transform = area_raster.transform

# Create profile for cloud-optimized geotiff
output_profile.update({
    'driver': 'GTiff',
    'nodata': nodata_value,
    'dtype': rasterio.uint8,
    'interleave': 'band',
    'tiled': True,
    'blockxsize': 512,
    'blockysize': 512,
    'compress': 'DEFLATE',
    'predictor': 2, # 2=int, 3=float
    'bigtiff': 'YES'
})

# Write data to output raster sequentially by tile
with rasterio_env:
    with rasterio.open(floodplain_output, 'w', **output_profile) as dst:
        count = 1

        # Define the boundaries of the destination raster
        dst_window = Window(0, 0, dst.width, dst.height)

        # Write each tile
        for input_file in input_files:
            print(f'\tWriting raster tile {count} of {len(input_files)}...')
            with rasterio.open(input_file) as tile_raster:
                # Calculate the exact pixel window
                window = from_bounds(*tile_raster.bounds, transform=area_transform)
                aligned_window = window.round_offsets().round_lengths()

                # Clip the tile to the domain boundary
                try:
                    write_window = aligned_window.intersection(dst_window)
                except rasterio.errors.WindowError:
                    # If the tile does not overlap the domain, then skip it
                    print(f'\t\tTile completely outside domain bounds. Skipping.')
                    count += 1
                    continue

                # Read the current tile's data
                tile_data = tile_raster.read(1)

                # Crop the data to match the write window
                if write_window != aligned_window:
                    # Calculate how many pixels were shaved off the top or left
                    row_offset = write_window.row_off - aligned_window.row_off
                    col_offset = write_window.col_off - aligned_window.col_off

                    # Slice the numpy array to the new dimensions
                    tile_data = tile_data[
                        row_offset: row_offset + write_window.height,
                        col_offset: col_offset + write_window.width
                    ]

                # Write the cropped data directly into the safely clipped window
                dst.write(tile_data, 1, window=write_window)
            count += 1
end_timing(iteration_start)

#### BUILD RASTER PYRAMIDS (OVERVIEWS)
####____________________________________________________

# Define overview levels
overview_levels = [2, 4, 8, 16, 32, 64, 128, 256]

# Build pyramids
print(f'Building pyramids...')
iteration_start = time.time()
with rasterio.open(floodplain_output, 'r+') as dst:
    # Build pyramids with bilinear resampling
    dst.build_overviews(overview_levels, resampling=Resampling.bilinear)
    # Update metadata to indicate overviews exist
    dst.update_tags(ns='rio_overview', resampling='bilinear')
end_timing(iteration_start)
