# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Parse range metadata from template
# Author: Timm Nawrocki
# Last Updated: 2026-06-01
# Usage: Execute in Python 3.9+.
# Description: 'Parse range metadata from template' replaces metadata specific to each map unit and dataset extent.
# ---------------------------------------------------------------------------

# Import packages
import os
import geopandas as gpd
import shapely
import numpy as np

# Define diagnostic sets
diagnostic_sets = {'abies': 'Fir Trees',
                   'alnus': 'Alder Shrubs',
                   'bderishr': 'Tall Blueberry Shrubs',
                   'beach': 'Beach Herbaceous',
                   'betshr': 'Birch Shrubs',
                   'bettre': 'Birch Trees',
                   'brotre': 'Broadleaf Trees',
                   'calnoo': 'Alaska Yellow Cedar',
                   'dryas': 'Dryas Dwarf Shrubs',
                   'empnig': 'Crowberry',
                   'erivag': 'Tussock Cottongrass',
                   'halgra': 'Halophytic Graminoids',
                   'larlar': 'Tamarack',
                   'neetre': 'Needleleaf Trees',
                   'picgla': 'White Spruce',
                   'picmar': 'Black Spruce',
                   'picsit': 'Sitka Spruce',
                   'pinus': 'Pine Trees',
                   'poptre': 'Aspen',
                   'populbt': 'Poplar/Cottonwood',
                   'rhoshr': 'Rhododendron Shrubs',
                   'rubspe': 'Salmonberry',
                   'tsuhet': 'Western Hemlock',
                   'tsumer': 'Mountain Hemlock'}

# Define version date
version_date = '20260415'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
metadata_folder = os.path.join(project_folder, 'Data_Output/metadata')
output_folder = os.path.join(project_folder, f'Data_Output/data_package/FoliarCover_v2p1_{version_date}/range_vectors')

# Define input files
range_template = os.path.join(metadata_folder, 'DiagnosticSet_rng_3338.xml')

#### PARSE METADATA FROM TEMPLATE
####____________________________________________________

# Loop through regions and diagnostic sets
for map_unit, diagnostic_name in diagnostic_sets.items():
        # Define input vector dataset
        vector_input = os.path.join(output_folder, f'{map_unit}_rng_3338.gpkg')
        layer_name = os.path.join(f'{map_unit}_rng_3338')

        # Define output metadata file
        metadata_name = os.path.split(range_template)[1].replace('DiagnosticSet_', f'{map_unit}_')
        metadata_output = os.path.join(output_folder, metadata_name)

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
        with open(range_template, 'r', encoding='utf-8') as file:
            metadata_content = file.read()

        # Replace 'diagnostic_set' with diagnostic set name
        metadata_content = metadata_content.replace('diagnostic_set', diagnostic_name)

        # Replace west coordinate
        metadata_content = metadata_content.replace('<gco:Decimal>172.44459</gco:Decimal>',
                                                    f'<gco:Decimal>{west_coordinate}</gco:Decimal>')

        # Replace east coordinate
        metadata_content = metadata_content.replace('<gco:Decimal>-129.99545</gco:Decimal>',
                                                    f'<gco:Decimal>{east_coordinate}</gco:Decimal>')

        # Replace south coordinate
        metadata_content = metadata_content.replace('<gco:Decimal>51.21576</gco:Decimal>',
                                                    f'<gco:Decimal>{south_coordinate}</gco:Decimal>')

        # Replace north coordinate
        metadata_content = metadata_content.replace('<gco:Decimal>71.38949</gco:Decimal>',
                                                    f'<gco:Decimal>{north_coordinate}</gco:Decimal>')

        # Export metadata file
        with open(metadata_output, 'w', encoding='utf-8') as file:
            file.write(metadata_content)

        print(f'Successfully processed {diagnostic_name}...')
