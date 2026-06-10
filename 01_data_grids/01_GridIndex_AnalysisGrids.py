# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Create analysis grids
# Author: Timm Nawrocki
# Last Updated: 2026-06-09
# Usage: Must be executed in a Python 3.12+ installation.
# Description: 'Create analysis grids' creates major and minor grid indices and overlapping grid tiles from a manually-generated study area polygon.
# ---------------------------------------------------------------------------

# Import packages
import os
import time
import geopandas as gpd
from shapely.geometry import box
from akutils import *

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
region_folder = os.path.join(project_folder, 'Data_Input/region_data')
grid_folder = os.path.join(project_folder, 'Data_Input/grid_data')

# Define input raster datasets
domain_input = os.path.join(region_folder, 'AlaskaYukon_ProjectDomain_v2p1_3338.shp')

# Define output grid datasets
akyuk_400 = os.path.join(grid_folder, 'AlaskaYukon_400_Tiles_3338.shp')
akyuk_100 = os.path.join(grid_folder, 'AlaskaYukon_100_Tiles_3338.shp')
akyuk_050 = os.path.join(grid_folder, 'AlaskaYukon_050_Tiles_3338.shp')
akyuk_010 = os.path.join(grid_folder, 'AlaskaYukon_010_Tiles_3338.shp')

#### CONFIGURE ENVIRONMENT & ITERATION PARAMETERS
####____________________________________________________

# Define grid generation constants
origin_x = -2199995.0
origin_y = 5.0
height_km = 2400
length_km = 4000
grid_distances = [400, 100, 50, 10]

# Read the map domain
domain_data = gpd.read_file(domain_input)
crs_3338 = domain_data.crs

# Define the fields to retain in the final outputs
export_fields = ['grid_code', 'shape_leng', 'shape_area', 'geometry']

#### GENERATE GRIDS
####____________________________________________________

# Create a grid for each specified grid distance
for distance_km in grid_distances:
    print(f'Processing {distance_km} km grids...')
    start_time = time.time()
    
    # Define the output grid name
    dist_label = f'{distance_km:03}'
    grid_output = os.path.join(grid_folder, f'AlaskaYukon_{dist_label}_Tiles_3338.shp')

    # Calculate the number of rows and columns
    number_rows = int(height_km / distance_km)
    number_columns = int(length_km / distance_km)
    distance_m = distance_km * 1000

    # Create the full grid
    grid_records = []

    # Loop through columns (H) and rows (V)
    for h in range(1, number_columns + 1):
        for v in range(1, number_rows + 1):

            # Calculate v from north to south
            v_from_south = number_rows - v + 1

            # Calculate geometric bounds
            xmin = origin_x + ((h - 1) * distance_m)
            ymin = origin_y + ((v_from_south - 1) * distance_m)
            xmax = origin_x + (h * distance_m)
            ymax = origin_y + (v_from_south * distance_m)

            # Create polygon geometry
            poly = box(xmin, ymin, xmax, ymax)

            # Format grid code strings
            grid_code = f'AK{dist_label}H{h:03}V{v:03}'

            # Append attributes and geometry
            grid_records.append({
                'grid_code': grid_code,
                'geometry': poly
            })

    # Convert records to a GeoDataFrame
    grid_data = gpd.GeoDataFrame(grid_records, crs=crs_3338)

    # Calculate geometric length (perimeter) and area
    grid_data['shape_leng'] = grid_data.geometry.length
    grid_data['shape_area'] = grid_data.geometry.area

    # Perform spatial join to retain grids that intersect the map domain
    grid_data = gpd.sjoin(grid_data, domain_data, how='inner', predicate='intersects')

    # Restrict fields for export
    grid_data = grid_data[export_fields]

    # Save selected grids to shapefile
    grid_data.to_file(grid_output)
    end_timing(start_time)