# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Compile covariate rasters
# Author: Timm Nawrocki
# Last Updated: 2026-04-15
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Compile covariate rasters" creates a prediction grid of covariate rasters to simplify the prediction step.
# ---------------------------------------------------------------------------

# Set execution parameters
grid_range = slice(0, 1000, 1)

# Set environment
import os
os.environ['GDAL_GCS_BINARY_READ'] = 'YES'

# Import packages
import geopandas as gpd
import time
import math
import numpy as np
from osgeo import gdal
import rasterio
from rasterio.enums import Resampling
from google.cloud import storage
from akutils import *

# Initialize GCS Client
storage_client = storage.Client()

# Configure GDAL
gdal.UseExceptions()

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = '/home'
root_folder = 'twnawrocki'

# Define folder structure
vrt_folder = os.path.join(drive, root_folder, 'Data_Input/vrt_data')
covariate_folder = os.path.join(drive, root_folder, 'Data_Input/covariate_data')
region_folder = os.path.join(drive, root_folder, 'Data_Input/region_data')

# Define input files
area_input = os.path.join(region_folder, 'AlaskaYukon_MapDomain_v2p1_10m_3338.tif')
grid_input = os.path.join(region_folder, 'AlaskaYukon_MapTiles_v2p1_3338.shp')

# Define intermediate files
s1_seasonal_vrt = os.path.join(vrt_folder, 's1_seasonal.vrt')
s2_seasonal_vrt = os.path.join(vrt_folder, 's2_seasonal.vrt')
s2_median_vrt = os.path.join(vrt_folder, 's2_median.vrt')

# Define covariate sets
predictor_clim = ['summer', 'january', 'precip']
predictor_s1 = ['s1_1_vha', 's1_1_vhd', 's1_1_vva', 's1_1_vvd',
                's1_2_vha', 's1_2_vhd', 's1_2_vva', 's1_2_vvd',
                's1_3_vha', 's1_3_vhd', 's1_3_vva', 's1_3_vvd']
predictor_s2 = [f's2_{i}_{band}' for i in range(1, 6) for band in
                ['blue', 'green', 'red', 'redge1', 'redge2', 'redge3', 'nir',
                 'redge4', 'swir1', 'swir2', 'nbr', 'ngrdi', 'ndmi', 'ndsi',
                 'ndvi', 'ndwi']]
predictor_topo = ['coast', 'stream', 'river', 'wetness',
                  'elevation', 'exposure', 'heatload', 'position',
                  'aspect', 'relief', 'roughness', 'slope']

# Dynamically build predictor_all list from input arguments
predictor_names = ['clim', 'topo', 's1', 's2']
predictor_map = {
    'clim': predictor_clim, 's1': predictor_s1, 's2': predictor_s2, 'topo': predictor_topo
}
predictor_all = []
for name in predictor_names:
    if name in predictor_map:
        predictor_all.extend(predictor_map[name])
    else:
        print(f'Warning: Predictor set {name} not recognized and will be skipped.')
if not predictor_all:
    raise ValueError('No valid predictor sets were provided. Exiting.')

# Create band map
band_map = {name: i for i, name in enumerate(predictor_all, start=1)}

#### DEFINE FUNCTIONS
####____________________________________________________

# Define a function to calculate normalized difference indices and scale by 10000
def calc_normalized_index(b1, b2, nodata=-32768):
    # Convert to float32 for math operations
    b1_f = b1.astype(np.float32)
    b2_f = b2.astype(np.float32)
    # Ignore divide-by-zero warnings during array math
    with np.errstate(divide='ignore', invalid='ignore'):
        denominator = b1_f + b2_f
        # Calculate index, defaulting to 0 where denominator is 0
        index = np.where(denominator == 0, 0, (b1_f - b2_f) / denominator) * 10000.0
    # Handle NaN values
    index = np.nan_to_num(index, nan=0.0, posinf=10000.0, neginf=-10000.0)
    # Clamp to limits and convert back to int16
    index_int = np.clip(index, -10000, 10000).astype(np.int16)
    # Apply nodata mask where either input band was missing
    mask = (b1 == nodata) | (b2 == nodata)
    index_int[mask] = nodata
    # Return value
    return index_int

#### IDENTIFY PREDICTION GRIDS
####____________________________________________________

# Read grid data
grid_data = gpd.read_file(grid_input)

# Define grid list
grid_list = grid_data['grid_code'].tolist()

# Override grid list for test purposes (uncomment lines below)
#target_grids = ['AK010H208V008']
#grid_list = [code for code in grid_list if code in target_grids]

# Partition grid list for spatially parallel processing
grid_list = grid_list[grid_range]

# Create final grid data
grid_data = grid_data[grid_data['grid_code'].isin(grid_list)]
print(f'Compiling {len(grid_data)} grids...')

#### PREPARE RASTER COVARIATES
####____________________________________________________

# Set VRT configuration
vrt_options = gdal.BuildVRTOptions(resampleAlg='bilinear', resolution='highest')

# Define storage bucket
storage_bucket = storage_client.get_bucket('akveg-data')

# Define raster paths for environmental covariates
coast_path = 'gs://akveg-data/covariates_v20240711/CoastDist_10m_3338.tif'
stream_path = 'gs://akveg-data/covariates_v20240711/StreamDist_10m_3338.tif'
river_path = 'gs://akveg-data/covariates_v20240711/RiverDist_10m_3338.tif'
wetness_path = 'gs://akveg-data/covariates_v20240711/Wetness_10m_3338.tif'
elevation_path = 'gs://akveg-data/covariates_v20240711/Elevation_10m_3338.tif'
exposure_path = 'gs://akveg-data/covariates_v20240711/Exposure_10m_3338.tif'
heatload_path = 'gs://akveg-data/covariates_v20240711/HeatLoad_10m_3338.tif'
position_path = 'gs://akveg-data/covariates_v20240711/Position_10m_3338.tif'
aspect_path = 'gs://akveg-data/covariates_v20240711/RadiationAspect_10m_3338.tif'
relief_path = 'gs://akveg-data/covariates_v20240711/Relief_10m_3338.tif'
roughness_path = 'gs://akveg-data/covariates_v20240711/Roughness_10m_3338.tif'
slope_path = 'gs://akveg-data/covariates_v20240711/Slope_10m_3338.tif'
summer_path = 'gs://akveg-data/covariates_v20260118/SummerWarmth_2006_2015_10m_3338.tif'
january_path = 'gs://akveg-data/covariates_v20260118/JanuaryMinimum_2006_2015_10m_3338.tif'
precip_path = 'gs://akveg-data/covariates_v20260118/Precipitation_2006_2015_10m_3338.tif'

# Get paths to S1 and S2 tiles
print('Compiling network paths for Sentinel-1 and -2 tiles...')
s1_paths = get_vsi_paths('akveg-data', 's1_2022_v20230326/', storage_client)
s2_seasonal_paths = get_vsi_paths('akveg-data', 's2_sr_2019_2023_gMedian_v20240713d/', storage_client)
s2_median_paths = get_vsi_paths('akveg-data', 's2_sr_2019_2023_median_v20240724/', storage_client)

# Create virtual raster for S1 covariates
if not os.path.exists(s1_seasonal_vrt):
    print('Building virtual raster for S1 covariates...')
    gdal.BuildVRT(s1_seasonal_vrt, s1_paths, options=vrt_options)

# Create virtual raster for S2 seasonal covariates
if not os.path.exists(s2_seasonal_vrt):
    print('Building virtual raster for S2 seasonal covariates...')
    gdal.BuildVRT(s2_seasonal_vrt, s2_seasonal_paths, options=vrt_options)

# Create virtual raster for S2 growing season median covariates
if not os.path.exists(s2_median_vrt):
    print('Building virtual raster for S2 median covariates...')
    gdal.BuildVRT(s2_median_vrt, s2_median_paths, options=vrt_options)

#### COMPILE COVARIATE RASTERS
####____________________________________________________

# Define single band data sources
single_band_sources = {
    'coast': coast_path.replace('gs://', '/vsigs/'),
    'stream': stream_path.replace('gs://', '/vsigs/'),
    'river': river_path.replace('gs://', '/vsigs/'),
    'wetness': wetness_path.replace('gs://', '/vsigs/'),
    'elevation': elevation_path.replace('gs://', '/vsigs/'),
    'exposure': exposure_path.replace('gs://', '/vsigs/'),
    'heatload': heatload_path.replace('gs://', '/vsigs/'),
    'position': position_path.replace('gs://', '/vsigs/'),
    'aspect': aspect_path.replace('gs://', '/vsigs/'),
    'relief': relief_path.replace('gs://', '/vsigs/'),
    'roughness': roughness_path.replace('gs://', '/vsigs/'),
    'slope': slope_path.replace('gs://', '/vsigs/'),
    'summer': summer_path.replace('gs://', '/vsigs/'),
    'january': january_path.replace('gs://', '/vsigs/'),
    'precip': precip_path.replace('gs://', '/vsigs/')
}

# Define grid alignment from area_input
print('Defining grid alignment...')
with rasterio.open(area_input) as area_raster:
    area_transform = area_raster.transform
    align_x = area_transform[2]
    align_y = area_transform[5]
    res_x = area_transform[0]
    res_y = abs(area_transform[4])

# Export covariate raster for each grid in grid list
grid_count = 1
for index, row in grid_data.iterrows():
    # Define grid code
    grid = row['grid_code']
    
    # Define output paths
    covariate_output = os.path.join(covariate_folder, f'{grid}_10m_3338.tif')
    gcs_output = f'gs://akveg-data/foliar_cover_v2p1/rasters_covariates/{grid}_10m_3338.tif'

    # Create output raster if it does not already exist in GCS
    if not gcs_blob_exists(gcs_output, storage_client):
        print(f'Compiling raster for {grid} ({grid_count} of {len(grid_list)})...')
        iteration_start = time.time()

        # Define geometry and window
        grid_geom = row['geometry'].buffer(20)
        raw_left, raw_bottom, raw_right, raw_top = grid_geom.bounds

        # Snap coordinates to the area_input grid alignment
        left = align_x + math.floor((raw_left - align_x) / res_x) * res_x
        bottom = align_y + math.floor((raw_bottom - align_y) / res_y) * res_y
        right = align_x + math.ceil((raw_right - align_x) / res_x) * res_x
        top = align_y + math.ceil((raw_top - align_y) / res_y) * res_y

        # Define the output profile based on master resolutions
        dst_transform = rasterio.transform.from_origin(left, top, res_x, res_y)
        dst_width = int(round((right - left) / res_x))
        dst_height = int(round((top - bottom) / res_y))

        # Define output profile
        output_profile = {
            'driver': 'GTiff',
            'height': dst_height,
            'width': dst_width,
            'count': len(predictor_all),
            'dtype': 'int16',
            'crs': 'EPSG:3338',
            'transform': dst_transform,
            'nodata': -32768,
            'compress': 'lzw',
            'tiled': True,
            'blockxsize': 256,
            'blockysize': 256
        }

        # Write covariate raster
        with rasterio.open(covariate_output, 'w', **output_profile) as dst:
            # Match covariate names to bands
            dst.descriptions = tuple(predictor_all)

            # ---------------------------------------------------------
            # Process single band rasters
            # ---------------------------------------------------------
            print('\tCompiling single band rasters...')
            for name, path in single_band_sources.items():
                if name in band_map:
                    with rasterio.open(path) as src:
                        # Ensure alignment with grid tile by casting as warped virtual raster
                        with rasterio.vrt.WarpedVRT(src, crs='EPSG:3338', resampling=Resampling.bilinear) as vrt:
                            # Define read window
                            window = vrt.window(left, bottom, right, top)
                            # Read data
                            data = vrt.read(1, window=window, out_shape=(dst_height, dst_width))
                            # Write data to disk
                            dst.write(data.astype(np.int16), band_map[name])

            # ---------------------------------------------------------
            # Process Sentinel-1 rasters
            # ---------------------------------------------------------

            # Define band names for S1 data
            s1_translation = {
                'VH_p50_grow_asc': 's1_1_vha',
                'VH_p50_fall_asc': 's1_2_vha',
                'VH_p50_froz_asc': 's1_3_vha',
                'VV_p50_grow_asc': 's1_1_vva',
                'VV_p50_fall_asc': 's1_2_vva',
                'VV_p50_froz_asc': 's1_3_vva',
                'VH_p50_grow_desc': 's1_1_vhd',
                'VH_p50_fall_desc': 's1_2_vhd',
                'VH_p50_froz_desc': 's1_3_vhd',
                'VV_p50_grow_desc': 's1_1_vvd',
                'VV_p50_fall_desc': 's1_2_vvd',
                'VV_p50_froz_desc': 's1_3_vvd'
            }

            # Fetch band names from the first S1 tile
            with rasterio.open(s1_paths[0]) as src0:
                s1_descriptions = src0.descriptions

            # Read S1 data to memory
            print('\tReading and filling S1 data...')
            s1_stack = {}
            with rasterio.open(s1_seasonal_vrt) as s1_seasonal_raster:
                for i, band in enumerate(s1_descriptions, start=1):
                    if band:
                        # Translate the band name
                        std_name = s1_translation.get(band, band)
                        # Define read window
                        window = s1_seasonal_raster.window(left, bottom, right, top)
                        # Read band data
                        s1_stack[std_name] = s1_seasonal_raster.read(i, window=window,
                                                                     out_shape=(dst_height, dst_width))

            # Fill missing data in S1 bands by polarity and season
            for season in ['1', '2', '3']:
                for pol in ['vh', 'vv']:
                    # Identify ascending and descending season-polarity combinations
                    asc_name = f's1_{season}_{pol}a'
                    desc_name = f's1_{season}_{pol}d'

                    # Check data validity and extract data as arrays
                    if asc_name in s1_stack and desc_name in s1_stack:
                        asc_data = s1_stack[asc_name]
                        desc_data = s1_stack[desc_name]

                        # Fill data where nodata value is present
                        asc_filled = np.where(asc_data == -32768, desc_data, asc_data)
                        desc_filled = np.where(desc_data == -32768, asc_data, desc_data)

                        # Write filled data to disk
                        if asc_name in band_map:
                            dst.write(asc_filled, band_map[asc_name])
                        if desc_name in band_map:
                            dst.write(desc_filled, band_map[desc_name])
                    else:
                        if asc_name in s1_stack and asc_name in band_map:
                            dst.write(s1_stack[asc_name], band_map[asc_name])
                        if desc_name in s1_stack and desc_name in band_map:
                            dst.write(s1_stack[desc_name], band_map[desc_name])

            # ---------------------------------------------------------
            # Process Sentinel-2 rasters
            # ---------------------------------------------------------

            # Define standardized band names for S2 data
            base_s2_bands = ['blue', 'green', 'red', 'redge1', 'redge2',
                             'redge3', 'nir', 'redge4', 'swir1', 'swir2']

            # Define band names for S2 backup
            s2_median_translation = {
                'B2': 's2_blue',
                'B3': 's2_green',
                'B4': 's2_red',
                'B5': 's2_redge1',
                'B6': 's2_redge2',
                'B7': 's2_redge3',
                'B8': 's2_nir',
                'B8A': 's2_redge4',
                'B11': 's2_swir1',
                'B12': 's2_swir2'
            }

            # Fetch band names from the first S2 backup tile
            with rasterio.open(s2_median_paths[0]) as src0:
                s2_backup_descriptions = src0.descriptions

            # Read and process S2 backup data (growing season median)
            print('\tReading S2 backup data...')
            s2_backup_stack = {}
            with rasterio.open(s2_median_vrt) as s2_median_raster:
                for i, band in enumerate(s2_backup_descriptions, start=1):
                    if band:
                        # Translate the band name
                        std_name = s2_median_translation.get(band, band)
                        # Define read window
                        window = s2_median_raster.window(left, bottom, right, top)
                        # Read band data
                        s2_backup_stack[std_name] = s2_median_raster.read(i, window=window,
                                                                          out_shape=(dst_height, dst_width))

            # Fetch descriptions from the first S2 tile
            with rasterio.open(s2_seasonal_paths[0]) as src0:
                s2_seasonal_descriptions = src0.descriptions

            # Build a band map and replace 'rededge' with 'redge'
            s2_map = {}
            for i, band in enumerate(s2_seasonal_descriptions, start=1):
                if band:
                    band = band.replace('rededge', 'redge')
                    band = band.replace('s2_seas1spring_', 's2_1_')
                    band = band.replace('s2_seas2earlySummer_', 's2_2_')
                    band = band.replace('s2_seas3midSummer_', 's2_3_')
                    band = band.replace('s2_seas4lateSummer_', 's2_4_')
                    band = band.replace('s2_seas5fall_', 's2_5_')
                    s2_map[band] = i
            
            # Compile S2 seasonal data, fill missing data with backup, and calculate spectral indices
            with rasterio.open(s2_seasonal_vrt) as s2_seasonal_raster:
                # Process data by season
                print('\tReading and filling S2 data...')
                for season in range(1, 6):
                    s2_stack = {}
                    for band in base_s2_bands:
                        # Define band names
                        name_seasonal = f's2_{season}_{band}'
                        name_backup = f's2_{band}'

                        # Read S2 seasonal data
                        if name_seasonal in s2_map:
                            # Define read window
                            window = s2_seasonal_raster.window(left, bottom, right, top)
                            # Read 
                            s2_data = s2_seasonal_raster.read(s2_map[name_seasonal], window=window,
                                                              out_shape=(dst_height, dst_width))
                        else:
                            s2_data = np.full((dst_height, dst_width), -32768, dtype=np.int16)

                        # Retrieve backup data
                        s2_backup_data = s2_backup_stack.get(name_backup,
                                                             np.full((dst_height, dst_width), -32768, dtype=np.int16))

                        # Fill missing seasonal pixels with the backup median
                        s2_filled_data = np.where(s2_data == -32768, s2_backup_data, s2_data)
                        s2_stack[band] = s2_filled_data

                        # Write band data to disk
                        if name_seasonal in band_map:
                            dst.write(s2_filled_data, band_map[name_seasonal])

                    # Calculate spectral indices using the filled bands
                    indices = {
                        'nbr': calc_normalized_index(s2_stack['nir'], s2_stack['swir2']),
                        'ngrdi': calc_normalized_index(s2_stack['green'], s2_stack['red']),
                        'ndmi': calc_normalized_index(s2_stack['nir'], s2_stack['swir1']),
                        'ndsi': calc_normalized_index(s2_stack['green'], s2_stack['swir1']),
                        'ndvi': calc_normalized_index(s2_stack['nir'], s2_stack['red']),
                        'ndwi': calc_normalized_index(s2_stack['green'], s2_stack['nir'])
                    }

                    # Write spectral indices to disk
                    for idx_name, idx_arr in indices.items():
                        band_name = f's2_{season}_{idx_name}'
                        if band_name in band_map:
                            dst.write(idx_arr, band_map[band_name])

        # Upload and Clean Up
        print('\tUploading raster dataset to Google Cloud Storage...')
        upload_to_gcs(covariate_output, gcs_output, storage_client)
        os.remove(covariate_output)
        end_timing(iteration_start)
    else:
        print(f'{grid} already exists.')

    # Increase count
    grid_count += 1
