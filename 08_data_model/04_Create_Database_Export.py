# ---------------------------------------------------------------------------
# Create database export
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-03-26
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Create database export" compiles a local copy of a static database export saved as csv tables. The static database copy provides a stable reference and archive version.
# ---------------------------------------------------------------------------

# Import libraries
import os
from datetime import datetime
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from akutils import connect_database_postgresql
from akutils import query_to_dataframe

# Set version date
version_date = '20260415'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
database_repository = os.path.join(drive, root_folder, 'Repositories/akveg-database')
credentials_folder = os.path.join(drive, root_folder, 'Administrative/Credentials/akveg_private_read')
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
site_folder = os.path.join(project_folder, 'Data/Data_Input/site_data', f'version_{version_date}')
output_folder = os.path.join(project_folder, 'Data/Data_Input/database_archive', f'version_{version_date}')

# Define input files
absence_input = os.path.join(project_folder,
                             f'Data/Data_Input/absence_data/version_{version_date}',
                             'AlaskaYukon_Absences_3338.shp')
absence_picea_input = os.path.join(project_folder,
                                   f'Data/Data_Input/absence_data/version_{version_date}',
                                   'WesternAlaska_Absences_picea_3338.shp')
absence_bettre_input = os.path.join(project_folder,
                                    f'Data/Data_Input/absence_data/version_{version_date}',
                                    'WesternAlaska_Absences_bettre_3338.shp')
domain_input = os.path.join(project_folder,
                            'Data/Data_Input/region_data',
                            'AlaskaYukon_MapDomain_v2p1_3338.shp')
region_input = os.path.join(project_folder,
                            'Data/Data_Input/region_data',
                            'AlaskaYukon_USNVC_ZonesRegions_v2p1_3338.shp')
validation_input = os.path.join(project_folder,
                                'Data/Data_Input/grid_data',
                                'AlaskaYukon_100_Tiles_3338.tif')
coast_input = os.path.join(drive,
                           root_folder,
                           'Data/hydrography/CoastDist_10m_3338.tif')
esa_input = os.path.join(project_folder,
                         'Data/Data_Input/ancillary_data/processed',
                         'AlaskaYukon_ESAWorldCover2_10m_3338.tif')
fire_input = os.path.join(project_folder,
                          'Data/Data_Input/ancillary_data/processed',
                          'AlaskaYukon_FireYear_10m_3338.tif')

# Define queries
taxa_file = os.path.join(database_repository, 'queries/00_taxonomy.sql')
project_file = os.path.join(database_repository, 'queries/01_project.sql')
site_visit_file = os.path.join(database_repository, 'queries/03_site_visit.sql')
vegetation_file = os.path.join(database_repository, 'queries/05_vegetation.sql')
abiotic_file = os.path.join(database_repository, 'queries/06_abiotic_top_cover.sql')
tussock_file = os.path.join(database_repository, 'queries/07_whole_tussock_cover.sql')
ground_file = os.path.join(database_repository, 'queries/08_ground_cover.sql')
structural_file = os.path.join(database_repository, 'queries/09_structural_group_cover.sql')
shrub_file = os.path.join(database_repository, 'queries/11_shrub_structure.sql')
environment_file = os.path.join(database_repository, 'queries/12_environment.sql')
soilmetrics_file = os.path.join(database_repository, 'queries/13_soil_metrics.sql')
soilhorizons_file = os.path.join(database_repository, 'queries/14_soil_horizons.sql')

# Define output files
taxa_output = os.path.join(output_folder, '00_taxonomy.csv')
project_output = os.path.join(output_folder, '01_project.csv')
site_visit_output = os.path.join(output_folder, '03_site_visit.csv')
site_point_output = os.path.join(site_folder, 'AKVEG_Site_Visits_3338.shp')
site_buffer_output = os.path.join(site_folder, 'AKVEG_Site_Visits_Buffered_3338.shp')
vegetation_output = os.path.join(output_folder, '05_vegetation_cover.csv')
abiotic_output = os.path.join(output_folder, '06_abiotic_cover.csv')
tussock_output = os.path.join(output_folder, '07_whole_tussock_cover.csv')
ground_output = os.path.join(output_folder, '08_ground_cover.csv')
structural_output = os.path.join(output_folder, '09_structural_cover.csv')
shrub_output = os.path.join(output_folder, '11_shrub_structure.csv')
environment_output = os.path.join(output_folder, '12_environment.csv')
soilmetrics_output = os.path.join(output_folder, '13_soil_metrics.csv')
soilhorizons_output = os.path.join(output_folder, '14_soil_horizons.csv')

#### PROCESS ABSENCE DATA
####------------------------------

# Read and format absences
absence_data = gpd.read_file(absence_input)
absence_data = absence_data.to_crs(crs='EPSG:4269')
absence_data['longitude_dd'] = absence_data.geometry.x
absence_data['latitude_dd'] = absence_data.geometry.y
absence_data = absence_data.drop(columns=['geometry', 'CID'])
absence_data['scope_vascular'] = 'absence'
absence_data['scope_bryophyte'] = 'absence'
absence_data['scope_lichen'] = 'absence'

# Read and format betula tree absences
absence_bettre_data = gpd.read_file(absence_bettre_input)
absence_bettre_data = absence_bettre_data.to_crs(crs='EPSG:4269')
absence_bettre_data['longitude_dd'] = absence_bettre_data.geometry.x
absence_bettre_data['latitude_dd'] = absence_bettre_data.geometry.y
absence_bettre_data = absence_bettre_data.drop(columns=['geometry', 'CID'])
absence_bettre_data['scope_vascular'] = 'bettre'
absence_bettre_data['scope_bryophyte'] = 'bettre'
absence_bettre_data['scope_lichen'] = 'bettre'

# Read and format picea absences
absence_picea_data = gpd.read_file(absence_picea_input)
absence_picea_data = absence_picea_data.to_crs(crs='EPSG:4269')
absence_picea_data['longitude_dd'] = absence_picea_data.geometry.x
absence_picea_data['latitude_dd'] = absence_picea_data.geometry.y
absence_picea_data = absence_picea_data.drop(columns=['geometry', 'CID'])
absence_picea_data['scope_vascular'] = 'picea'
absence_picea_data['scope_bryophyte'] = 'picea'
absence_picea_data['scope_lichen'] = 'picea'

# Merge absence data
absence_merged = pd.concat([absence_data, absence_bettre_data, absence_picea_data], axis=0)
absence_merged = absence_merged.reset_index().drop(columns=['index']).reset_index().copy()
absence_merged['index'] = absence_merged['index'] + 1

# Create site codes
absence_merged['site_code'] = 'ABS2026_0000' + absence_merged['index'].astype(str)
absence_merged['site_code'] = np.where(absence_merged['index'] >= 10,
                                     'ABS2026_000' + absence_merged['index'].astype(str),
                                     absence_merged['site_code'])
absence_merged['site_code'] = np.where(absence_merged['index'] >= 100,
                                     'ABS2026_00' + absence_merged['index'].astype(str),
                                     absence_merged['site_code'])
absence_merged['site_code'] = np.where(absence_merged['index'] >= 1000,
                                     'ABS2026_0' + absence_merged['index'].astype(str),
                                     absence_merged['site_code'])
absence_merged['site_code'] = np.where(absence_merged['index'] >= 10000,
                                     'ABS2026_' + absence_merged['index'].astype(str),
                                     absence_merged['site_code'])

# Add observation dates
absence_date = datetime.strptime(version_date, '%Y%m%d')
absence_merged['observe_date'] = absence_date.strftime('%Y-%m-%d')

# Add metadata fields
absence_merged['site_visit_code'] = absence_merged['site_code'] + '_' + version_date
absence_merged['project_code'] = 'akveg_absences'
absence_merged['cover_method'] = 'image interpretation'
absence_merged['perspective'] = 'aerial'
absence_merged['plot_dimensions_m'] = '10 radius'
absence_merged['data_tier'] = 'map development & verification'
absence_merged['structural_class'] = 'not assessed'
absence_merged['homogeneous'] = True

# Remove extra columns
absence_merged = absence_merged.drop(columns=['index']).copy()

#### QUERY AND PROCESS AKVEG SITE VISITS
####------------------------------

# Create a connection to the AKVEG PostgreSQL database
authentication_file = os.path.join(credentials_folder, 'authentication_akveg_private.csv')
database_connection = connect_database_postgresql(authentication_file)

# Read taxonomy standard from AKVEG Database
taxa_read = open(taxa_file, 'r')
taxa_query = taxa_read.read()
taxa_read.close()
taxa_data = query_to_dataframe(database_connection, taxa_query)

# Read site visit data from AKVEG Database
site_visit_read = open(site_visit_file, 'r')
site_visit_query = site_visit_read.read()
site_visit_read.close()
site_visit_data = query_to_dataframe(database_connection, site_visit_query)

# Merge site visits and absence data
site_visit_data = pd.concat([site_visit_data, absence_merged], axis=0)

# Assign observation year
site_visit_data['observe_datetime'] = pd.to_datetime(site_visit_data['observe_date'])
site_visit_data['observe_year'] = site_visit_data['observe_datetime'].dt.year

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
domain_shape = gpd.read_file(domain_input)
site_visit_data = gpd.clip(site_visit_data, domain_shape)

# Extract bioclimatic zone and vegetation region
region_shape = gpd.read_file(region_input)[['geometry', 'biome', 'region']]
site_visit_data = gpd.sjoin(site_visit_data, region_shape, how="left", predicate="within")
if 'index_right' in site_visit_data.columns:
    site_visit_data = site_visit_data.drop(columns=['index_right'])

# Identify coordinates from site visit data
coordinates = [(x, y) for x, y in zip(site_visit_data.geometry.x, site_visit_data.geometry.y)]

# Extract validation raster to sites
with rasterio.open(validation_input) as src:
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['valid'] = [x[0] for x in extracted_values]

# Extract coast raster to sites
with rasterio.open(coast_input) as src:
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['coast'] = [x[0] for x in extracted_values]

# Extract ESA raster to sites
with rasterio.open(esa_input) as src:
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['esa_type'] = [x[0] for x in extracted_values]

# Extract fire raster to sites
with rasterio.open(fire_input) as src:
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['fire_year'] = [x[0] for x in extracted_values]

# Parse plot radius
site_visit_data['plot_radius_m'] = 0
site_visit_data['plot_radius_m'] = np.where((site_visit_data['perspective'] == 'aerial')
                                            & (site_visit_data['plot_dimensions_m'] == 'unknown'),
                                            20, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where((site_visit_data['perspective'] == 'aerial')
                                            & (site_visit_data['plot_dimensions_m'] == '100×100'),
                                            20, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where((site_visit_data['perspective'] == 'ground')
                                            & (site_visit_data['plot_dimensions_m'] == 'unknown'),
                                            5, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'] == '1×1',
                                            0.5, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['1 radius', '1×7', '1×8', '1×10', '1×12', '2×2', '2×5', '2×7', '2×10', '2×12', '2×20',
     '3×6', '3×7', '3×8', '3×10', '3×12', '3×15', '3×20', '3×25']),
    1, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['2 radius', '4×4', '4×8', '4×25', '5×5', '5×8', '5×10', '5×15', '5×20', '5×30',
     '5×15', '5×20', '5×30']),
    2, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['3 radius', '4 radius', '6×6', '6×10', '6×12', '7×8', '7×10', '8×8', '8×10', '8×12']),
    3, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['5 radius', '10×10', '10×12', '10×20', '10×30', '10×40']),
    4, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['6 radius', '12×12']),
    5, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['7 radius']),
    6, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['8 radius', '15×15', '15×18', '15×30', '15×100']),
    7, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['10 radius', '11.6 radius', '18×18', '20×20', '20×40', '20×80', '20×100']),
    8, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['12.5 radius', '25×100', '25×25']),
    10, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['15 radius', '30×80', '30×30']),
    12, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['20 radius']),
    15, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['23 radius', '25 radius', '50×50']),
    20, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['30 radius']),
    25, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['34.7 radius']),
    30, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'] == '55 radius',
                                            50, site_visit_data['plot_radius_m'])

# Check that no plot dimensions remain unassigned
missing_dimensions = site_visit_data[site_visit_data['plot_radius_m'] == 0]['plot_dimensions_m'].unique()
if len(missing_dimensions) > 0:
    quit()

# Select columns
site_visit_data = site_visit_data[[
    'site_visit_code', 'project_code', 'site_code', 'data_tier',
    'observe_date', 'observe_year', 'perspective', 'cover_method',
    'scope_vascular', 'scope_bryophyte', 'scope_lichen',
    'structural_class', 'homogeneous', 'plot_dimensions_m', 'plot_radius_m',
    'biome', 'region', 'fire_year', 'esa_type', 'coast', 'valid',
    'latitude_dd', 'longitude_dd', 'cent_x', 'cent_y'
]]

# Rename fields for export as shapefile to meet shapefile field character length constraint
export_point_data = site_visit_data.rename(columns={'site_visit_code': 'st_vst',
                                                    'project_code': 'prjct_cd',
                                                    'site_code': 'st_code',
                                                    'observe_date': 'obs_date',
                                                    'observe_year': 'obs_year',
                                                    'perspective': 'perspect',
                                                    'cover_method': 'cvr_mthd',
                                                    'scope_vascular': 'scp_vasc',
                                                    'scope_bryophyte': 'scp_bryo',
                                                    'scope_lichen': 'scp_lich',
                                                    'structural_class': 'strc_class',
                                                    'homogeneous': 'hmgneous',
                                                    'plot_dimensions_m': 'plt_dim_m',
                                                    'plot_radius_m': 'plt_rad_m',
                                                    'latitude_dd': 'lat_dd',
                                                    'longitude_dd': 'long_dd'
                                                    }).copy()

# Create geometries for the export points
export_point_data = gpd.GeoDataFrame(
    export_point_data,
    geometry=gpd.points_from_xy(export_point_data.cent_x,
                                export_point_data.cent_y),
    crs='EPSG:3338')


# Buffer the site visit points
export_buffer_data = export_point_data.copy()
export_buffer_data['geometry'] = export_buffer_data.geometry.buffer(export_buffer_data['plt_rad_m'])

# Export site visit points and buffers to shapefiles
export_point_data.to_file(site_point_output)
export_buffer_data.to_file(site_buffer_output)

#### QUERY AKVEG COVER DATA AND CHECK SITES
####------------------------------

# Read vegetation cover data from AKVEG Database for selected site visits
vegetation_read = open(vegetation_file, 'r')
vegetation_query = vegetation_read.read()
vegetation_read.close()
vegetation_data = query_to_dataframe(database_connection, vegetation_query)

# Read abiotic top cover data from AKVEG Database for selected site visits
abiotic_read = open(abiotic_file, 'r')
abiotic_query = abiotic_read.read()
abiotic_read.close()
abiotic_data = query_to_dataframe(database_connection, abiotic_query)

# Create list of unique site visits
vegetation_site_visits = vegetation_data['site_visit_code']
abiotic_site_visits = abiotic_data['site_visit_code']
site_visit_check = pd.concat([vegetation_site_visits, abiotic_site_visits], axis=0).to_frame()
site_visit_check = site_visit_check['site_visit_code'].unique()

# Check that all site visits in the site visit data have corresponding data in either vegetation or abiotic cover
missing_cover_sites = site_visit_data[~site_visit_data['site_visit_code'].isin(site_visit_check)]
missing_cover_sites = missing_cover_sites[missing_cover_sites['project_code'] != 'akveg_absences']
if len(missing_cover_sites) > 0:
    quit()

# Check that all site visits in vegetation or abiotic cover have corresponding data in the site visit table
veg_sites = pd.concat([vegetation_site_visits, abiotic_site_visits], axis=0).to_frame()
missing_site_visits = veg_sites[~veg_sites['site_visit_code'].isin(site_visit_data['site_visit_code'].unique())]
missing_site_visits = missing_site_visits['site_visit_code'].unique()

# Troubleshoot missing sites
site_visit_full = query_to_dataframe(database_connection, site_visit_query)
missing_site_visits = site_visit_full[site_visit_full['site_visit_code'].isin(missing_site_visits)]

#### QUERY OTHER AKVEG DATA
####------------------------------

# Read project data from AKVEG Database for selected site visits
project_read = open(project_file, 'r')
project_query = project_read.read()
project_read.close()
project_data = query_to_dataframe(database_connection, project_query).sort_values('project_code')

# Read whole tussock cover data from AKVEG Database for selected site visits
tussock_read = open(tussock_file, 'r')
tussock_query = tussock_read.read()
tussock_read.close()
tussock_data = query_to_dataframe(database_connection, tussock_query)

# Read ground cover data from AKVEG Database for selected site visits
ground_read = open(ground_file, 'r')
ground_query = ground_read.read()
ground_read.close()
ground_data = query_to_dataframe(database_connection, ground_query)

# Read structural group cover data from AKVEG Database for selected site visits
structural_read = open(structural_file, 'r')
structural_query = structural_read.read()
structural_read.close()
structural_data = query_to_dataframe(database_connection, structural_query)

# Read shrub structure data from AKVEG Database for selected site visits
shrub_read = open(shrub_file, 'r')
shrub_query = shrub_read.read()
shrub_read.close()
shrub_data = query_to_dataframe(database_connection, shrub_query)

# Read environment data from AKVEG Database for selected site visits
environment_read = open(environment_file, 'r')
environment_query = environment_read.read()
environment_read.close()
environment_data = query_to_dataframe(database_connection, environment_query)

# Read soil metrics data from AKVEG Database for selected site visits
soilmetrics_read = open(soilmetrics_file, 'r')
soilmetrics_query = soilmetrics_read.read()
soilmetrics_read.close()
soilmetrics_data = query_to_dataframe(database_connection, soilmetrics_query)

# Read soil horizons data from AKVEG Database for selected site visits
soilhorizons_read = open(soilhorizons_file, 'r')
soilhorizons_query = soilhorizons_read.read()
soilhorizons_read.close()
soilhorizons_data = query_to_dataframe(database_connection, soilhorizons_query)

# Export data to csv files
taxa_data.to_csv(taxa_output, header=True, index=False, sep=',', encoding='utf-8')
project_data.to_csv(project_output, header=True, index=False, sep=',', encoding='utf-8')
site_visit_data.to_csv(site_visit_output, header=True, index=False, sep=',', encoding='utf-8')
vegetation_data.to_csv(vegetation_output, header=True, index=False, sep=',', encoding='utf-8')
abiotic_data.to_csv(abiotic_output, header=True, index=False, sep=',', encoding='utf-8')
tussock_data.to_csv(tussock_output, header=True, index=False, sep=',', encoding='utf-8')
ground_data.to_csv(ground_output, header=True, index=False, sep=',', encoding='utf-8')
structural_data.to_csv(structural_output, header=True, index=False, sep=',', encoding='utf-8')
shrub_data.to_csv(shrub_output, header=True, index=False, sep=',', encoding='utf-8')
environment_data.to_csv(environment_output, header=True, index=False, sep=',', encoding='utf-8')
soilmetrics_data.to_csv(soilmetrics_output, header=True, index=False, sep=',', encoding='utf-8')
soilhorizons_data.to_csv(soilhorizons_output, header=True, index=False, sep=',', encoding='utf-8')
