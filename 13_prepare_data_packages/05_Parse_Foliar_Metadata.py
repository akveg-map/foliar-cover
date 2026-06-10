# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Parse foliar metadata from template
# Author: Timm Nawrocki
# Last Updated: 2026-06-01
# Usage: Execute in Python 3.9+.
# Description: 'Parse foliar metadata from template' replaces metadata specific to each map unit for foliar cover and distribution probability maps and creates colormaps from templates.
# ---------------------------------------------------------------------------

# Import packages
import os

# Define diagnostic sets
diagnostic_sets = {'abies': 'Fir Trees',
                   'alnus': 'Alder Shrubs',
                   'bderishr': 'Tall Blueberry Shrubs',
                   'beach': 'Beach Herbaceous',
                   'betshr': 'Birch Shrubs',
                   'bettre': 'Birch Trees',
                   'bromos': 'Brown Mosses',
                   'brotre': 'Broadleaf Trees',
                   'calnoo': 'Alaska Yellow Cedar',
                   'dryas': 'Dryas Dwarf Shrubs',
                   'dsalix': 'Willow Dwarf Shrubs',
                   'empnig': 'Crowberry',
                   'erivag': 'Tussock Cottongrass',
                   'feather': 'Feathermosses',
                   'forb': 'Forbs',
                   'gramin': 'Graminoids',
                   'halgra': 'Halophytic Graminoids',
                   'larlar': 'Tamarack',
                   'lichen': 'Lichens',
                   'mwcalama': 'Mesic-Wet Calamagrostis',
                   'ndsalix': 'Willow Shrubs',
                   'neetre': 'Needleleaf Trees',
                   'nerishr': 'Needleleaf Ericaceous Shrubs',
                   'picgla': 'White Spruce',
                   'picmar': 'Black Spruce',
                   'picsit': 'Sitka Spruce',
                   'pinus': 'Pine Trees',
                   'poptre': 'Aspen',
                   'populbt': 'Poplar/Cottonwood',
                   'rhoshr': 'Rhododendron Shrubs',
                   'rubspe': 'Salmonberry',
                   'sphagn': 'Sphagnum Mosses',
                   'tsuhet': 'Western Hemlock',
                   'tsumer': 'Mountain Hemlock',
                   'vaculi': 'Low Blueberry Shrubs',
                   'vacvit': 'Lingonberry',
                   'wetforb': 'Wetland Forbs',
                   'wetgram': 'Wetland Grasses and Rushes',
                   'wetsed': 'Wetland Sedges'}

dist_list = ['abies', 'bromos', 'calnoo', 'larlar', 'pinus', 'wetgram']

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
output_folder = os.path.join(project_folder, f'Data_Output/data_package/FoliarCover_v2p1_{version_date}/foliar_rasters')

# Define input files
cover_template = os.path.join(metadata_folder, 'DiagnosticSet_cvr_10m_3338.xml')
cover_colormap = os.path.join(metadata_folder, 'DiagnosticSet_cvr_10m_3338.clr')
dist_template = os.path.join(metadata_folder, 'DiagnosticSet_dst_10m_3338.xml')
dist_colormap = os.path.join(metadata_folder, 'DiagnosticSet_dst_10m_3338.clr')

#### PARSE METADATA FROM TEMPLATE
####____________________________________________________

# Loop through regions and diagnostic sets
for map_unit, diagnostic_name in diagnostic_sets.items():
        # Define input metadata template
        if map_unit in dist_list:
            metadata_template = dist_template
            colormap_template = dist_colormap
        else:
            metadata_template = cover_template
            colormap_template = cover_colormap

        # Define output metadata file
        metadata_name = os.path.split(metadata_template)[1].replace('DiagnosticSet_', f'{map_unit}_')
        colormap_name = os.path.split(colormap_template)[1].replace('DiagnosticSet_', f'{map_unit}_')
        metadata_output = os.path.join(output_folder, metadata_name)
        colormap_output = os.path.join(output_folder, colormap_name)

        # Read metadata from template
        with open(metadata_template, 'r', encoding='utf-8') as file:
            metadata_content = file.read()

        # Replace 'diagnostic_set' with diagnostic set name
        metadata_content = metadata_content.replace('diagnostic_set', diagnostic_name)

        # Read colormap from template
        with open(colormap_template, 'r', encoding='utf-8') as file:
            colormap_content = file.read()

        # Export metadata file
        with open(metadata_output, 'w', encoding='utf-8') as file:
            file.write(metadata_content)
        with open(colormap_output, 'w', encoding='utf-8') as file:
            file.write(colormap_content)

        print(f'Successfully processed {diagnostic_name}...')
