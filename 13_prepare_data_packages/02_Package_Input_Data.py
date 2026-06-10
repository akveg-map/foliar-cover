# ---------------------------------------------------------------------------
# Prepare input data packages
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-06-02
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Prepare input data packages" converts the input and ancillary vector data to geopackages after ensuring geometry validity.
# ---------------------------------------------------------------------------

# Import packages
import os
import time
import geopandas as gpd
from osgeo import gdal
from osgeo.gdalconst import GDT_Int16
from akutils import *

# Configure GDAL
gdal.UseExceptions()

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set version date
version_date = '20260415'

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
region_folder = os.path.join(project_folder, 'Data_Input/region_data')
absence_folder = os.path.join(project_folder, f'Data_Input/absence_data/version_{version_date}')
ancillary_folder = os.path.join(project_folder, 'Data_Input/ancillary_data/processed')
grid_folder = os.path.join(project_folder, 'Data_Input/grid_data')
domain_folder = os.path.join(project_folder, 'Data_Input')
output_folder = os.path.join(project_folder, f'Data_Output/data_package/FoliarCover_v2p1_{version_date}')
raster_folder = os.path.join(project_folder, 'Data_Output/data_package/raster_temp')

# Define input file
domain_input = os.path.join(region_folder, 'AlaskaYukon_MapDomain_v2p1_3338.shp')
project_input = os.path.join(region_folder, 'AlaskaYukon_ProjectDomain_v2p1_3338.shp')
tile010_input = os.path.join(region_folder, 'AlaskaYukon_MapTiles_010_v2p1_3338.shp')
subregion_input = os.path.join(region_folder, 'AlaskaYukon_CustomSubregions_3338.shp')
absence_input = os.path.join(absence_folder, 'AlaskaYukon_Absences_3338.shp')
bettre_input = os.path.join(absence_folder, 'WesternAlaska_Absences_bettre_3338.shp')
picea_input = os.path.join(absence_folder, 'WesternAlaska_Absences_picea_3338.shp')
fireyear_input = os.path.join(ancillary_folder, 'AlaskaYukon_FireYear_10m_3338.tif')
tile100_input = os.path.join(grid_folder, 'AlaskaYukon_100_Tiles_3338.tif')
domain_raster_input = os.path.join(domain_folder, 'AlaskaYukon_MapDomain_v2p1_10m_3338.tif')
project_raster_input = os.path.join(domain_folder, 'AlaskaYukon_ProjectDomain_v2p1_10m_3338.tif')

#### CONVERT DOMAIN VECTORS TO GEOPACKAGES
####____________________________________________________

for vector_input in [domain_input, project_input]:
    start_time = time.time()

    # Define layer name
    layer_name = os.path.splitext(os.path.split(vector_input)[1])[0]
    print(f'Packaging {layer_name}...')

    # Define output path
    output_path = os.path.join(output_folder, 'ancillary_data/domain_vectors')

    # Ensure the destination folder exists
    os.makedirs(output_path, exist_ok=True)

    # Define output file name
    vector_output = os.path.join(output_path, layer_name + '.gpkg')

    # Convert vector to geopackage
    vector_data = gpd.read_file(vector_input)[['geometry']]

    # Calculate shape length and shape area
    vector_data['shape_length'] = vector_data.geometry.length
    vector_data['shape_area'] = vector_data.geometry.area

    # Determine validity
    reasons = vector_data[~vector_data.geometry.is_valid].geometry.is_valid_reason
    print(reasons)

    # Repair all geometries in geodataframe
    vector_data.geometry = vector_data.geometry.make_valid()

    # Export data to geopackage
    vector_data.to_file(vector_output, layer=layer_name, driver='GPKG')
    end_timing(start_time)

#### CONVERT TILES VECTOR TO GEOPACKAGE
####____________________________________________________

# Define layer name
layer_name = os.path.splitext(os.path.split(tile010_input)[1])[0]
start_time = time.time()
print(f'Packaging {layer_name}...')

# Define output path
output_path = os.path.join(output_folder, 'ancillary_data/ancillary_vectors')

# Ensure the destination folder exists
os.makedirs(output_path, exist_ok=True)

# Define output file name
vector_output = os.path.join(output_path, layer_name + '.gpkg')

# Convert vector to geopackage
vector_data = gpd.read_file(tile010_input)[['grid_code', 'geometry']]

# Calculate shape length and shape area
vector_data['shape_length'] = vector_data.geometry.length
vector_data['shape_area'] = vector_data.geometry.area

# Determine validity
reasons = vector_data[~vector_data.geometry.is_valid].geometry.is_valid_reason
print(reasons)

# Repair all geometries in geodataframe
vector_data.geometry = vector_data.geometry.make_valid()

# Export data to geopackage
vector_data.to_file(vector_output, layer=layer_name, driver='GPKG')
end_timing(start_time)

#### CONVERT CUSTOM SUBREGIONS VECTOR TO GEOPACKAGE
####____________________________________________________

# Define layer name
layer_name = os.path.splitext(os.path.split(subregion_input)[1])[0]
start_time = time.time()
print(f'Packaging {layer_name}...')

# Define output path
output_path = os.path.join(output_folder, 'ancillary_data/ancillary_vectors')

# Ensure the destination folder exists
os.makedirs(output_path, exist_ok=True)

# Define output file name
vector_output = os.path.join(output_path, layer_name + '.gpkg')

# Convert vector to geopackage
vector_data = gpd.read_file(subregion_input)[['zone', 'geometry']].rename(columns={'zone': 'subregion'})

# Ensure that features do not overlap
geometries = []
for i, row in vector_data.iterrows():
    geom = row.geometry
    if i > 0:
        # Union all previously processed geometries
        previous_union = gpd.GeoSeries(geometries).union_all()
        # Subtract the union from the current geometry
        geom = geom.difference(previous_union)
    geometries.append(geom)

# Assign the cleaned geometries back to the GeoDataFrame
vector_data.geometry = geometries

# Remove any polygons that were completely erased (empty geometries)
vector_data = vector_data[~vector_data.is_empty].reset_index(drop=True)

# Calculate shape length and shape area
vector_data['shape_length'] = vector_data.geometry.length
vector_data['shape_area'] = vector_data.geometry.area

# Determine validity
reasons = vector_data[~vector_data.geometry.is_valid].geometry.is_valid_reason
print(reasons)

# Repair all geometries in geodataframe
vector_data.geometry = vector_data.geometry.make_valid()

# Export data to geopackage
vector_data.to_file(vector_output, layer=layer_name, driver='GPKG')
end_timing(start_time)

#### CONVERT ABSENCE VECTORS TO GEOPACKAGES
####____________________________________________________

for vector_input in [absence_input, bettre_input, picea_input]:
    start_time = time.time()

    # Define layer name
    layer_name = os.path.splitext(os.path.split(vector_input)[1])[0]
    print(f'Packaging {layer_name}...')

    # Define output path
    output_path = os.path.join(output_folder, 'ancillary_data/absence_vectors')

    # Ensure the destination folder exists
    os.makedirs(output_path, exist_ok=True)

    # Define output file name
    vector_output = os.path.join(output_path, layer_name + '.gpkg')

    # Convert vector to geopackage
    vector_data = gpd.read_file(vector_input)[['geometry']]

    # Add absence scope field
    if vector_input == absence_input:
        vector_data['scope_absence'] = 'all'
    elif vector_input == bettre_input:
        vector_data['scope_absence'] = 'bettre'
    elif vector_input == picea_input:
        vector_data['scope_absence'] = 'picea'

    # Determine validity
    reasons = vector_data[~vector_data.geometry.is_valid].geometry.is_valid_reason
    print(reasons)

    # Repair all geometries in geodataframe
    vector_data.geometry = vector_data.geometry.make_valid()

    # Export data to geopackage
    vector_data.to_file(vector_output, layer=layer_name, driver='GPKG')
    end_timing(start_time)

#### CONVERT MAP DOMAIN RASTER TO CLOUD-OPTIMIZED GEOTIFF
####____________________________________________________

# Define output file
domain_raster_output = os.path.join(raster_folder, os.path.split(domain_raster_input)[1])

# Process output raster if it does not already exist
if not os.path.exists(domain_raster_output):
    print('Processing map domain raster...')
    start_time = time.time()

    # Set translation options for GDAL COG driver
    cog_options = gdal.TranslateOptions(
        format='COG',
        creationOptions=[
            'COMPRESS=DEFLATE',
            'PREDICTOR=1',
            'BLOCKSIZE=512',
            'NUM_THREADS=ALL_CPUS',
            'BIGTIFF=YES',
            'RESAMPLING=BILINEAR',
            'OVERVIEW_RESAMPLING=AVERAGE'
        ]
    )

    # Translate raster to cloud-optimized geotiff
    gdal.Translate(domain_raster_output, domain_raster_input, options=cog_options)
    end_timing(start_time)

#### CONVERT PROJECT DOMAIN RASTER TO CLOUD-OPTIMIZED GEOTIFF
####____________________________________________________

# Define output file
project_raster_output = os.path.join(raster_folder, os.path.split(project_raster_input)[1])

# Process output raster if it does not already exist
if not os.path.exists(project_raster_output):
    print('Processing project domain raster...')
    start_time = time.time()

    # Set translation options for GDAL COG driver
    cog_options = gdal.TranslateOptions(
        format='COG',
        creationOptions=[
            'COMPRESS=DEFLATE',
            'PREDICTOR=1',
            'BLOCKSIZE=512',
            'NUM_THREADS=ALL_CPUS',
            'BIGTIFF=YES',
            'RESAMPLING=BILINEAR',
            'OVERVIEW_RESAMPLING=AVERAGE'
        ]
    )

    # Translate raster to cloud-optimized geotiff
    gdal.Translate(project_raster_output, project_raster_input, options=cog_options)
    end_timing(start_time)

#### CONVERT FIRE YEAR TO CLOUD-OPTIMIZED GEOTIFF
####____________________________________________________

# Define output file
fireyear_output = os.path.join(raster_folder, os.path.split(fireyear_input)[1])

# Process output raster if it does not already exist
if not os.path.exists(fireyear_output):
    print('Processing fire year raster...')
    start_time = time.time()

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
    gdal.Translate(fireyear_output, fireyear_input, options=cog_options)
    end_timing(start_time)

#### CONVERT VALIDATION TILES RASTER TO CLOUD-OPTIMIZED GEOTIFF
####____________________________________________________

# Define output file
tile100_output = os.path.join(raster_folder, os.path.split(tile100_input)[1])

# Process output raster if it does not already exist
if not os.path.exists(tile100_output):
    print('Processing validation tiles raster...')
    start_time = time.time()

    # Set warp options for GDAL COG driver
    cog_options = gdal.WarpOptions(
        format='COG',
        outputType=GDT_Int16,
        srcNodata=65535,
        dstNodata=-32768,
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

    # Warp raster to cloud-optimized geotiff
    gdal.Warp(tile100_output, tile100_input, options=cog_options)
    end_timing(start_time)
