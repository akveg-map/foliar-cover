# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Prepare benchmark data
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-05-26
# Usage: Must be executed in a Python 3.12+ installation.
# Description: 'Prepare benchmark data' identifies the subset of site visits appropriate to ordination and clustering for the combined performance assessment and parses the data to subregions.
# ---------------------------------------------------------------------------

# Import packages
import os
import re
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

# Set version date
version_date = '20260415'

# Define diagnostic species sets
#### ADD FEATHERMOSS!!!
diagnostic_sets = ['alnus', 'bderishr', 'beach', 'betshr', 'bettre', 'brotre',
                   'dryas', 'dsalix', 'empnig', 'erivag', 'forb', 'gramin',
                   'halgra', 'lichen', 'mwcalama', 'ndsalix', 'neetre', 'nerishr',
                   'picgla', 'picmar', 'picsit', 'poptre', 'populbt', 'rhoshr', 'rubspe',
                   'sphagn', 'tsuhet', 'tsumer', 'vaculi', 'vacvit', 'wetforb', 'wetsed']

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
site_folder = os.path.join(project_folder, f'Data_Input/site_data/version_{version_date}')
database_folder = os.path.join(project_folder, f'Data_Input/database_archive/version_{version_date}')
region_folder = os.path.join(project_folder, 'Data_Input/region_data')
ancillary_folder = os.path.join(project_folder, 'Data_Input/ancillary_data/processed')
results_folder = os.path.join(project_folder, f'Data_Output/model_results/version_{version_date}')
raster_folder = os.path.join(project_folder, f'Data_Output/rasters_final/version_{version_date}')
ordination_folder = os.path.join(project_folder, f'Data_Input/ordination_data/version_{version_date}')

# Define input files
taxonomy_input = os.path.join(database_folder, '00_taxonomy.csv')
site_visit_input = os.path.join(site_folder, 'akveg_site_visits_3338.csv')
vegetation_input = os.path.join(database_folder, '05_vegetation_cover.csv')
domain_input = os.path.join(region_folder, 'AlaskaYukon_MapDomain_v2p1_3338.shp')
ecoregion_input = os.path.join(region_folder, 'AlaskaYukon_UnifiedEcoregions_3338.shp')
mlra_input = os.path.join(region_folder, 'Alaska_MajorLandResourceArea_v2022_3338.shp')
zone_input = os.path.join(region_folder, 'Ordination_CustomZones_3338.shp')
akvwc_input = os.path.join(ancillary_folder, 'AlaskaVegetationWetlandComposite_Fine_30m_3338_v20180412.tif')
landfire_input = os.path.join(ancillary_folder, 'LA23_EVT_240.tif')

# Define output files
site_visit_output = os.path.join(ordination_folder, 'site_visit_data.csv')
vegetation_output = os.path.join(ordination_folder, 'vegetation_data.csv')

#### PROCESS SITE VISIT DATA
####____________________________________________________
print('Preparing site visit data...')

# Read input site visit data
site_visit_data = pd.read_csv(site_visit_input)

# Read input shapefiles
domain_shape = gpd.read_file(domain_input)
ecoregion_shape = gpd.read_file(ecoregion_input)[['COMMONER', 'geometry']].rename(
    columns={'COMMONER': 'ecoregion'}
)
mlra_shape = gpd.read_file(mlra_input)[['MLRA_NAME', 'geometry']].rename(
    columns={'MLRA_NAME': 'mlra'}
)
zone_shape = gpd.read_file(zone_input)[['zone', 'geometry']]

# Remove exclusion sites
site_visit_data = site_visit_data[site_visit_data['exclude'] == 0].copy()

# Create geodataframe
site_visit_data = gpd.GeoDataFrame(
    site_visit_data,
    geometry=gpd.points_from_xy(site_visit_data.longitude_dd,
                                site_visit_data.latitude_dd),
    crs='EPSG:4269')

# Convert geodataframe to EPSG:3338
site_visit_data = site_visit_data.to_crs(crs='EPSG:3338')

# Extract coordinates in EPSG:3338
site_visit_data['cent_x'] = site_visit_data.geometry.x
site_visit_data['cent_y'] = site_visit_data.geometry.y

# Subset points to map domain
site_visit_data = gpd.clip(site_visit_data, domain_shape)

# Identify coordinates from site visit data
coordinates = [(x, y) for x, y in zip(site_visit_data.geometry.x, site_visit_data.geometry.y)]

# Extract AKVWC fine classes from raster to sites
print('\tExtracting AKVWC fine classes...')
with rasterio.open(akvwc_input) as src:
    # Capture the AKVWC nodata value
    akvwc_nodata = src.nodata
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['akvwc_fine'] = [x[0] for x in extracted_values]

# Extract Landfire classes from raster to sites
print('\tExtracting Landfire classes...')
with rasterio.open(landfire_input) as src:
    # Capture the Landfire nodata value
    landfire_nodata = src.nodata
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['landfire_evt'] = [x[0] for x in extracted_values]

# Remove sites that do not have valid data in the AKVWC or Landfire maps
site_visit_data = site_visit_data[(site_visit_data['akvwc_fine'] != akvwc_nodata)
                                  & (site_visit_data['landfire_evt'] != landfire_nodata)
                                  & (site_visit_data['landfire_evt'] != -9999)].copy()

# Prepend 'm' prefix to valid raster extractions (ignore NA values)
site_visit_data['akvwc_fine'] = site_visit_data['akvwc_fine'].apply(
    lambda x: f'm{int(x)}' if pd.notna(x) and x != 0 else np.nan
)
site_visit_data['landfire_evt'] = site_visit_data['landfire_evt'].apply(
    lambda x: f'm{int(x)}' if pd.notna(x) and x != 0 else np.nan
)

# Sequentially execute spatial left joins
print('\tJoining subregional data...')
site_visit_data = gpd.sjoin(site_visit_data, ecoregion_shape, how='left', predicate='intersects').drop(
    columns='index_right'
)
site_visit_data = gpd.sjoin(site_visit_data, mlra_shape, how='left', predicate='intersects').drop(
    columns='index_right'
)
site_visit_data = gpd.sjoin(site_visit_data, zone_shape, how='left', predicate='intersects').drop(
    columns='index_right'
)

# Drop geometry array to return object to standard Pandas dataframe
site_visit_data = site_visit_data.drop(columns='geometry')

#### PREPARE VEGETATION DATA
####____________________________________________________
print('Preparing vegetation data...')

# Read input taxonomy and vegetation data
taxa_data = pd.read_csv(taxonomy_input)
vegetation_data = pd.read_csv(vegetation_input)

# Prepare unique site visit codes
site_visits = site_visit_data['site_visit_code'].unique()

# Subset the vegetation data to match the site visits
vegetation_data = vegetation_data[
    vegetation_data['site_visit_code'].isin(site_visits)
].copy()

# Convert trace values to 0.1%
vegetation_data['cover_percent'] = vegetation_data['cover_percent'].replace(0, 0.1)

# Select absolute cover observations
vegetation_data = vegetation_data[vegetation_data['cover_type'].isin(
    ['absolute foliar cover', 'absolute canopy cover'])]

# Join taxon names to codes
vegetation_data = vegetation_data.merge(
    taxa_data, left_on='code_accepted', right_on='code_akveg', how='left'
)

# Define a function to generalize infraspecies to species
def clean_infraspecies(name):
    if pd.isna(name):
        return name
    if 'ssp.' in name:
        return re.sub(r' ssp\..*', '', name)
    if 'var.' in name:
        return re.sub(r' var\..*', '', name)
    return name

# Generalize infraspecies to species
vegetation_data['taxon_revised'] = vegetation_data['name_accepted'].apply(
    clean_infraspecies
)

# For non-vascular life forms, merge all species to genera
non_vascular = ['hornwort', 'liverwort', 'moss', 'lichen']
non_vasc_mask = vegetation_data['taxon_category'].isin(non_vascular)
vegetation_data.loc[non_vasc_mask, 'taxon_revised'] = vegetation_data.loc[
    non_vasc_mask, 'taxon_genus'
]

# Subset columns and join taxa data to revised names
vegetation_data = vegetation_data[['site_visit_code', 'taxon_revised', 'dead_status',
                              'cover_type', 'cover_percent']].copy()
vegetation_data = vegetation_data.merge(taxa_data, left_on='taxon_revised', right_on='taxon_name', how='left')

# Append identifier to taxon codes for dead vegetation
vegetation_data['taxon_code'] = np.where(vegetation_data['dead_status'] == True,
                                         vegetation_data['code_akveg'] + '#dead',
                                         vegetation_data['code_akveg'])

# Summarize cover data to updated taxa
vegetation_data = (vegetation_data.groupby(['site_visit_code', 'taxon_code'])['cover_percent']
                   .sum()
                   .reset_index()
                   )

# Check number of cover observations per project
project_check = (
    vegetation_data.merge(site_visit_data, on='site_visit_code')
    .groupby('project_code')
    .size()
    .reset_index(name='obs_n')
)
site_visit_check = (
    vegetation_data.groupby('site_visit_code')
    .size()
    .reset_index(name='obs_n')
)

# Create list of tree taxa
tree_list = taxa_data[
    (taxa_data['taxon_status'] == 'accepted')
    & (taxa_data['taxon_habit'].isin(['deciduous tree', 'coniferous tree']))
    & (taxa_data['taxon_accepted'] != 'Alnus rubra')
    & (taxa_data['taxon_genus'] != 'Prunus')
]['code_akveg'].unique()

# Prepare tree cover
summary_data = vegetation_data.merge(taxa_data, left_on='taxon_code', right_on='code_akveg', how='left')
summary_data['tree_percent'] = np.where(summary_data['taxon_code'].isin(tree_list),
                                        summary_data['cover_percent'], 0)

# Prepare vascular cover
vascular_categories = ['eudicot', 'fern', 'forb', 'gymnosperm', 'horsetail', 'lycophyte', 'monocot']
summary_data['vascular_percent'] = np.where(summary_data['taxon_category'].isin(vascular_categories),
                                            summary_data['cover_percent'], 0)

# Summarize tree cover, vascular cover, and total vegetation cover
summary_data = (summary_data.groupby('site_visit_code')
                .agg(tree_percent=('tree_percent', 'sum'),
                     vascular_percent=('vascular_percent', 'sum'),
                     total_percent=('cover_percent', 'sum'))
                .reset_index())

# Join summary data to site visit data
site_visit_data = site_visit_data.merge(summary_data, on='site_visit_code', how='left')

# Omit sparse & barren sites
sparse_barren_visits = site_visit_data[site_visit_data['vascular_percent'] <= 20]['site_visit_code']
site_visit_data = site_visit_data[~site_visit_data['site_visit_code'].isin(sparse_barren_visits)]
vegetation_data = vegetation_data[~vegetation_data['site_visit_code'].isin(sparse_barren_visits)]

#### ASSIGN ANALYSIS GROUPS
####____________________________________________________
print('Assigning analysis groups...')

# Initialize subregion with default value
site_visit_data['subregion'] = 'unassigned'

# Assign Arctic Foothills & Mountains
site_visit_data['subregion'] = np.where((site_visit_data['region'] == 'Arctic Northern')
                                        & (site_visit_data['ecoregion'] != 'Beaufort Coastal Plain'),
                                        'Arctic Foothills & Mountains', site_visit_data['subregion'])

# Assign Arctic Coastal Plain
site_visit_data['subregion'] = np.where((site_visit_data['region'] == 'Arctic Northern')
                                        & ((site_visit_data['ecoregion'] == 'Beaufort Coastal Plain')
                                           | (site_visit_data['zone'] == 'Arctic Coastal Plain')),
                                        'Arctic Coastal Plain', site_visit_data['subregion'])

# Assign Seward Peninsula
site_visit_data['subregion'] = np.where((site_visit_data['region'] == 'Arctic Western')
                                        & (site_visit_data['mlra'].isin
                                           (['Northern Seward Peninsula-Selawik Lowlands',
                                             'Seward Peninsula Highlands',
                                             'Nulato Hills-Southern Seward Peninsula Highlands'])),
                                        'Seward Peninsula', site_visit_data['subregion'])

# Assign Bering Sea Islands
site_visit_data['subregion'] = np.where(site_visit_data['ecoregion'] == 'Bering Sea Islands',
                                        'Bering Sea Islands', site_visit_data['subregion'])

# Assign Alaska Peninsula
site_visit_data['subregion'] = np.where((site_visit_data['region'] == 'Aleutian-Kamchatka')
                                        & (site_visit_data['ecoregion'] == 'Alaska Peninsula'),
                                        'Alaska Peninsula', site_visit_data['subregion'])

# Assign Kodiak Southwest
site_visit_data['subregion'] = np.where((site_visit_data['region'] == 'Aleutian-Kamchatka')
                                        & (site_visit_data['ecoregion'] == 'Kodiak Island'),
                                        'Kodiak Southwest', site_visit_data['subregion'])

# Assign Southwest Mountains
site_visit_data['subregion'] = np.where((site_visit_data['region'] == 'Alaska Southwest')
                                        & ((site_visit_data['mlra'].isin
                                            (['Southern Alaska Peninsula Mountains',
                                              'Interior Alaska Mountains']))
                                           | (site_visit_data['ecoregion'].isin
                                              (['Kuskokwim Mountains',
                                                'Lime Hills']))),
                                        'Southwest Mountains', site_visit_data['subregion'])

# Assign Bristol Bay
site_visit_data['subregion'] = np.where((site_visit_data['region'] == 'Alaska Southwest')
                                        & (site_visit_data['mlra'].isin
                                           (['Bristol Bay-Northern Alaska Peninsula Lowlands',
                                             'Ahklun Mountains'])),
                                        'Bristol Bay', site_visit_data['subregion'])

# Assign Alaska Western
site_visit_data['subregion'] = np.where(site_visit_data['region'] == 'Alaska Western',
                                        'Alaska Western', site_visit_data['subregion'])

# Assign Alaska-Yukon Northwest
site_visit_data['subregion'] = np.where((site_visit_data['region'] == 'Alaska-Yukon Northern')
                                        & (site_visit_data['mlra'].isin
                                           (['Upper Kobuk and Koyukuk Hills and Valleys',
                                             'Interior Brooks Range Mountains',
                                             'Western Brooks Range Mountains, Foothills, and Valleys',
                                             'Northern Seward Peninsula-Selawik Lowlands'])),
                                        'Alaska-Yukon Northwest', site_visit_data['subregion'])

# Assign Yukon Flats
site_visit_data['subregion'] = np.where((site_visit_data['region'] == 'Alaska-Yukon Central')
                                        & (site_visit_data['mlra'] == 'Yukon Flats Lowlands'),
                                        'Yukon Flats', site_visit_data['subregion'])

# Assign Eastern Interior
site_visit_data['subregion'] = np.where((site_visit_data['region'].isin
                                         (['Alaska-Yukon Central',
                                           'Alaska-Yukon Northern']))
                                        & (site_visit_data['mlra'] != 'Yukon Flats Lowlands')
                                        & (site_visit_data['ecoregion'].isin
                                           (['North Ogilvie Mountains',
                                             'Yukon-Tanana Uplands',
                                             'Yukon-Old Crow Basin'])),
                                        'Eastern Interior', site_visit_data['subregion'])

# Assign Central Interior
site_visit_data['subregion'] = np.where((site_visit_data['region'] == 'Alaska-Yukon Central') &
                                        (site_visit_data['ecoregion'].isin
                                         (['Kobuk Ridges and Valleys',
                                           'Kuskokwim Mountains',
                                           'Nulato Hills',
                                           'Ray Mountains',
                                           'Tanana-Kuskokwim Lowlands',
                                           'Yukon River Lowlands'])),
                                        'Central Interior', site_visit_data['subregion'])

# Assign Denali North
site_visit_data['subregion'] = np.where((site_visit_data['zone'] == 'Denali North'),
                                        'Denali North', site_visit_data['subregion'])

# Assign Wrangell-Copper
site_visit_data['subregion'] = np.where((site_visit_data['region'] == 'Alaska-Yukon Southern')
                                        & (site_visit_data['zone'].isin
                                           (['Wrangell-Tetlin',
                                             'Wrangell-St. Elias',
                                             'Copper River Basin'])),
                                        'Wrangell-Copper', site_visit_data['subregion'])

# Assign Nelchina Uplands
site_visit_data['subregion'] = np.where((site_visit_data['zone'] == 'Nelchina Uplands'),
                                        'Nelchina Uplands', site_visit_data['subregion'])

# Assign Denali South
site_visit_data['subregion'] = np.where((site_visit_data['zone'] == 'Denali South'),
                                        'Denali South', site_visit_data['subregion'])

# Assign Cook Inlet
site_visit_data['subregion'] = np.where((site_visit_data['region'] == 'Alaska-Yukon Southern')
                                        & (site_visit_data['ecoregion'] == 'Cook Inlet Basin'),
                                        'Cook Inlet', site_visit_data['subregion'])

# Assign Kodiak Northeast
site_visit_data['subregion'] = np.where((site_visit_data['region'] == 'Alaska Pacific')
                                        & (site_visit_data['ecoregion'] == 'Kodiak Island'),
                                        'Kodiak Northeast', site_visit_data['subregion'])

# Assign Pacific Mainland
site_visit_data['subregion'] = np.where((site_visit_data['region'] == 'Alaska Pacific')
                                        & (site_visit_data['ecoregion'] != 'Kodiak Island'),
                                        'Pacific Mainland', site_visit_data['subregion'])

#### ASSIGN FOREST & NON-FOREST UNITS
####____________________________________________________

# Initialize focal unit with default value
site_visit_data['focal_unit'] = 'all'

# Assign forest
site_visit_data['focal_unit'] = np.where((site_visit_data['subregion'].isin
                                          (['Bristol Bay',
                                            'Alaska Western',
                                            'Yukon Flats',
                                            'Eastern Interior',
                                            'Denali North',
                                            'Wrangell-Copper',
                                            'Denali South',
                                            'Kodiak Northeast',
                                            'Pacific Mainland']))
                                         & (site_visit_data['tree_percent'] >= 10),
                                         'forest', site_visit_data['focal_unit'])

# Assign non-forest
site_visit_data['focal_unit'] = np.where((site_visit_data['subregion'].isin
                                          (['Bristol Bay',
                                            'Alaska Western',
                                            'Yukon Flats',
                                            'Eastern Interior',
                                            'Denali North',
                                            'Wrangell-Copper',
                                            'Denali South',
                                            'Kodiak Northeast',
                                            'Pacific Mainland']))
                                         & (site_visit_data['tree_percent'] < 10),
                                         'non-forest', site_visit_data['focal_unit'])

#### ASSIGN NUMERICAL CODES
####____________________________________________________

# Define subregion dictionary
subregion_dictionary = {
    ('Arctic Coastal Plain', 'all'): 1,
    ('Arctic Foothills & Mountains', 'all'): 2,
    ('Seward Peninsula', 'all'): 3,
    ('Bering Sea Islands', 'all'): 4,
    ('Alaska Peninsula', 'all'): 5,
    ('Kodiak Southwest', 'all'): 6,
    ('Southwest Mountains', 'all'): 7,
    ('Bristol Bay', 'forest'): 8,
    ('Bristol Bay', 'non-forest'): 9,
    ('Alaska Western', 'forest'): 10,
    ('Alaska Western', 'non-forest'): 11,
    ('Alaska-Yukon Northwest', 'all'): 12,
    ('Yukon Flats', 'forest'): 13,
    ('Yukon Flats', 'non-forest'): 14,
    ('Eastern Interior', 'forest'): 15,
    ('Eastern Interior', 'non-forest'): 16,
    ('Central Interior', 'all'): 17,
    ('Denali North', 'forest'): 18,
    ('Denali North', 'non-forest'): 19,
    ('Wrangell-Copper', 'forest'): 20,
    ('Wrangell-Copper', 'non-forest'): 21,
    ('Nelchina Uplands', 'all'): 22,
    ('Denali South', 'forest'): 23,
    ('Denali South', 'non-forest'): 24,
    ('Cook Inlet', 'all'): 25,
    ('Kodiak Northeast', 'forest'): 26,
    ('Kodiak Northeast', 'non-forest'): 27,
    ('Pacific Mainland', 'forest'): 28,
    ('Pacific Mainland', 'non-forest'): 29
}

# Map the dictionary to the dataframe using a list comprehension for speed and readability
site_visit_data['group_id'] = [
    subregion_dictionary.get((subregion, focal_unit), -999)
    for subregion, focal_unit in zip(site_visit_data['subregion'], site_visit_data['focal_unit'])
]

final_columns = [
    'site_visit_code', 'project_code', 'site_code', 'data_tier', 'observe_date', 'scope_vascular',
    'scope_bryophyte', 'scope_lichen', 'perspective', 'cover_method', 'structural_class',
    'fire_year', 'akvwc_fine', 'landfire_evt', 'biome', 'region', 'ecoregion', 'mlra', 'zone', 'group_id',
    'subregion', 'focal_unit', 'tree_percent', 'vascular_percent', 'total_percent', 'homogeneous',
    'plot_dimensions_m', 'latitude_dd', 'longitude_dd', 'cent_x', 'cent_y'
]

# Safely select columns (ignores columns that may not exist to prevent KeyError)
site_visit_data = site_visit_data[[col for col in final_columns if col in site_visit_data.columns]]

#### EXTRACT FOLIAR COVER PREDICTIONS
####____________________________________________________
print('Extracting foliar cover predictions...')

# Loop through diagnostic datasets
count = 1
for diagnostic_set in diagnostic_sets:
    print(f'\tExtracting predictions for {diagnostic_set} ({count} of {len(diagnostic_sets)})...')
    # Set input files
    validation_input = os.path.join(results_folder, diagnostic_set, f'{diagnostic_set}_results.csv')
    raster_input = os.path.join(raster_folder, f'{diagnostic_set}_Cvr_10m_3338.tif')

    # Read cross-validation results and subset columns
    results_data = pd.read_csv(validation_input)[['site_visit_code', 'prediction']]

    # Left join results to site visit data
    site_visit_data = site_visit_data.merge(results_data, on='site_visit_code', how='left')

    # Prepare point coordinates for raster data extraction
    coords = list(zip(site_visit_data['cent_x'], site_visit_data['cent_y']))

    # Extract raster values
    with rasterio.open(raster_input) as src:
        extracted = src.sample(coords)
        raster_vals = [val[0] for val in extracted]
    site_visit_data['raster_value'] = raster_vals

    # Fill missing predictions using raster values, then map to diagnostic set name
    site_visit_data[diagnostic_set] = site_visit_data['prediction'].fillna(site_visit_data['raster_value'])

    # Clean up temporary columns for the next iteration
    site_visit_data.drop(columns=['prediction', 'raster_value'], inplace=True)

    # Increase count
    count += 1

#### EXPORT DATA
####____________________________________________________
print('Exporting data...')

# Ensure that all site visits have vegetation data
valid_site_visits = vegetation_data['site_visit_code'].unique()
site_visit_data = site_visit_data[site_visit_data['site_visit_code'].isin(valid_site_visits)]

# Export data to csv files
site_visit_data.to_csv(site_visit_output, index=False)
vegetation_data.to_csv(vegetation_output, index=False)
