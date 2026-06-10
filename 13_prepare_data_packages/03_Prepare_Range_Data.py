# ---------------------------------------------------------------------------
# Prepare range data packages
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-06-01
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Prepare range data packages" converts the range vector data to geopackages after ensuring geometry validity.
# ---------------------------------------------------------------------------

# Import packages
import os
import glob
import time
import geopandas as gpd
from akutils import *

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set version date
version_date = '20260415'

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
range_folder = os.path.join(project_folder, 'Data_Input/range_data/processed')
output_folder = os.path.join(project_folder, f'Data_Output/data_package/FoliarCover_v2p1_{version_date}')

# Define input file
range_inputs = glob.glob(range_folder + '/*.shp')

#### CONVERT DOMAIN VECTORS TO GEOPACKAGES
####____________________________________________________

for vector_input in range_inputs:
    start_time = time.time()

    # Define layer name
    layer_name = os.path.splitext(os.path.split(vector_input)[1])[0]
    layer_name = layer_name.replace('range_', '')
    layer_name = layer_name.replace('_3338', '')
    layer_name = layer_name + '_rng_3338'
    print(f'Packaging {layer_name}...')

    # Define output path
    output_path = os.path.join(output_folder, 'range_vectors')

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
