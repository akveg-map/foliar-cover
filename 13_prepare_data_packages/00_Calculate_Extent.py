# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Calculate vector dataset extent
# Author: Timm Nawrocki
# Last Updated: 2026-06-02
# Usage: Execute in Python 3.9+.
# Description: 'Calculate vector dataset extent' aids the production of metadata by rewriting the spatial extent of an xml metadata file to include a calculated extent.
# ---------------------------------------------------------------------------

# Import packages
import os
import re
import geopandas as gpd
import shapely
import numpy as np

# Define version date
version_date = '20260415'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
output_folder = os.path.join(project_folder, f'Data_Output/data_package/FoliarCover_v2p1_{version_date}')

# Define input file
vector_input = os.path.join(output_folder, 'ancillary_data/domain_vectors/AlaskaYukon_ProjectDomain_v2p1_3338.gpkg')

#### DEFINE FUNCTIONS
####____________________________________________________

# Define a function to update the spatial extent metadata fields
def update_spatial_extents(metadata_content, west, east, south, north):
    # Convert inputs to floats and enforce exactly 5 decimal places with trailing zeros
    west_fmt = f"{float(west):.5f}"
    east_fmt = f"{float(east):.5f}"
    south_fmt = f"{float(south):.5f}"
    north_fmt = f"{float(north):.5f}"

    # Execute regex substitutions using the formatted strings and explicit group backreferences
    metadata_content = re.sub(r'(<westBoundLongitude>\s*<gco:Decimal>)[^<]+(</gco:Decimal>)', fr'\g<1>{west_fmt}\g<2>',
                              metadata_content)
    metadata_content = re.sub(r'(<eastBoundLongitude>\s*<gco:Decimal>)[^<]+(</gco:Decimal>)', fr'\g<1>{east_fmt}\g<2>',
                              metadata_content)
    metadata_content = re.sub(r'(<southBoundLatitude>\s*<gco:Decimal>)[^<]+(</gco:Decimal>)', fr'\g<1>{south_fmt}\g<2>',
                              metadata_content)
    metadata_content = re.sub(r'(<northBoundLatitude>\s*<gco:Decimal>)[^<]+(</gco:Decimal>)', fr'\g<1>{north_fmt}\g<2>',
                              metadata_content)

    return metadata_content

#### REWRITE SPATIAL EXTENT
####____________________________________________________

# Define input metadata
layer_name = os.path.splitext(os.path.split(vector_input)[1])[0]
metadata_input = os.path.join(os.path.split(vector_input)[0], layer_name + '.xml')

# Read vector bounds
vector_3338 = gpd.read_file(vector_input, layer=layer_name)
vector_4269 = vector_3338.to_crs('EPSG:4269')

# Extract all raw coordinate vertices from the geometries
xy = shapely.get_coordinates(vector_4269.geometry)
longitudes = xy[:, 0]
latitudes = xy[:, 1]

# Shift Eastern Hemisphere longitudes (> 0) into negative space to calculate extent
adjusted_longitudes = np.where(longitudes > 0, longitudes - 360, longitudes)

# Find the minimum and maximum adjusted longitudes
min_adj_lon = np.min(adjusted_longitudes)
max_adj_lon = np.max(adjusted_longitudes)

# Calculate min and max longitude in standard notation
west_4269 = min_adj_lon + 360 if min_adj_lon < -180 else min_adj_lon
east_4269 = max_adj_lon + 360 if max_adj_lon < -180 else max_adj_lon

# Calculate min and max latitude
south_4269 = np.min(latitudes)
north_4269 = np.max(latitudes)

# Assign EPSG:4326 bounding coordinates rounded to 5 decimal places to variables
south_coordinate = round(south_4269, 5)
north_coordinate = round(north_4269, 5)
west_coordinate = round(west_4269, 5)
east_coordinate = round(east_4269, 5)

# Read metadata from template
with open(metadata_input, 'r', encoding='utf-8') as file:
    metadata_content = file.read()

# Replace coordinates
metadata_content = update_spatial_extents(
    metadata_content,
    west_coordinate,
    east_coordinate,
    south_coordinate,
    north_coordinate
)

# Export metadata file
with open(metadata_input, 'w', encoding='utf-8') as file:
    file.write(metadata_content)

print(f'Successfully processed metadata update.')
