# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Query benchmark data from AKVEG Database
# Author: Timm Nawrocki, Amanda Droghini, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Query benchmark data from AKVEG Database" pulls data from the AKVEG Database for selected datasets. The script connects to the AKVEG database, executes queries, and performs simple spatial analyses (i.e., subset the data to specific study areas, extract raster values to surveyed plots). The outputs are a series of CSV files (one for each non-metadata table in the database) whose results are restricted to the study area in the script.
# ---------------------------------------------------------------------------

# Import required libraries
library(dplyr)
library(fs)
library(janitor)
library(lubridate)
library(readr)
library(readxl)
library(writexl)
library(RPostgres)
library(sf)
library(stringr)
library(terra)
library(tibble)
library(tidyr)

# Set round date
round_date = 'round_20241124'

# Define indicators
indicators = c('alnus', 'betshr', 'bettre', 'brotre', 'dryas', 'dsalix', 'empnig', 'erivag', 'mwcalama',
               'ndsalix', 'nerishr', 'picgla', 'picmar', 'picsit', 'poptre', 'populbt', 'rhoshr', 'rubspe',
               'sphagn', 'tsumer', 'vaculi', 'vacvit', 'wetsed')

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory (modify to your folder structure)
drive = 'C:'
root_folder = 'ACCS_Work'

# Define input folders (modify to your folder structure)
database_repository = path(drive, root_folder, 'Repositories/akveg-database-public')
credentials_folder = path(drive, root_folder, 'Credentials/akveg_private_read')
project_folder = path(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
results_folder = path(project_folder, 'Data_Output/model_results', round_date)
raster_folder = path(project_folder, 'Data_Output/data_package/version_2.0_20250103')
output_folder = path(project_folder, 'Data_Input/ordination_data')

# Define input files
domain_input = path(project_folder, 'Data_Input/region_data/AlaskaYukon_ProjectDomain_v2.0_3338.shp')
region_input = path(project_folder, 'Data_Input/region_data/AlaskaYukon_Regions_v2.0_3338.shp')
ecoregion_input = path(project_folder, 'Data_Input/region_data/AlaskaYukon_UnifiedEcoregions_3338.shp')
mlra_input = path(project_folder, 'Data_Input/region_data/Alaska_MajorLandResourceArea_v2022_3338.shp')
zone_input = path(project_folder, 'Data_Input/region_data/Ordination_CustomZones_3338.shp')
fireyear_input = path(project_folder, 'Data_Input/ancillary_data/processed/AlaskaYukon_FireYear_10m_3338.tif')
coast_input = path(project_folder, 'Data_Input/ancillary_data/processed/CoastDist_10m_3338.tif')
elevation_input = path(project_folder, 'Data_Input/ancillary_data/processed/Elevation_10m_3338.tif')
alpine_input = path(project_folder, 'Data_Input/ancillary_data/processed/AlpineBinary_10m_3338.tif')
akvwc_input = path(project_folder, 'Data_Input/ancillary_data/processed',
                   'AlaskaVegetationWetlandComposite_Fine_30m_3338_v20180412.tif')
landfire_input = path(project_folder, 'Data_Input/ancillary_data/processed', 'LA23_EVT_240.tif')

# Define output files
taxa_output = path(output_folder, '00_taxonomy.csv')
project_output = path(output_folder, '01_project.csv')
site_visit_output = path(output_folder, '03_site_visit.csv')
site_point_output = path(output_folder, '03_site_point_3338.shp')
vegetation_output = path(output_folder, '05_vegetation.csv')
subregion_output = path(output_folder, 'subregion_summary.xlsx')

# Define queries
taxa_file = path(database_repository, 'queries/00_taxonomy.sql')
project_file = path(database_repository, 'queries/01_project.sql')
site_visit_file = path(database_repository, 'queries/03_site_visit.sql')
vegetation_file = path(database_repository, 'queries/05_vegetation.sql')
abiotic_file = path(database_repository, 'queries/06_abiotic_top_cover.sql')

#### READ LOCAL DATA
####____________________________________________________

# Read domain shape
domain_shape = st_read(domain_input)

# Read region shape and select fields
region_shape = st_read(region_input) %>%
  select(biome, region)

# Read ecoregion shape and select fields
ecoregion_shape = st_read(ecoregion_input) %>%
  select(COMMONER) %>%
  rename(ecoregion = COMMONER)

# Read MLRA shape and select fields
mlra_shape = st_read(mlra_input) %>%
  select(MLRA_NAME) %>%
  rename(mlra = MLRA_NAME)

# Read zone shape and select fields
zone_shape = st_read(zone_input) %>%
  select(zone)

# Read fire year raster
fireyear_raster = rast(fireyear_input)

# Read distance to coast raster
coast_raster = rast(coast_input)

# Read elevation raster
elevation_raster = rast(elevation_input)

# Read alpine distribution raster
alpine_raster = rast(alpine_input)

# Read Alaska Vegetation and Wetland Composite raster
akvwc_raster = rast(akvwc_input)

# Read Landfire 2023 Existing Vegetation Types raster
landfire_raster = rast(landfire_input)

#### QUERY AKVEG DATABASE
####____________________________________________________

# Import database connection function
connection_script = path(database_repository, 'pull_functions', 'connect_database_postgresql.R')
source(connection_script)

# Create a connection to the AKVEG PostgreSQL database
authentication = path(credentials_folder, 'authentication_akveg_private.csv')
database_connection = connect_database_postgresql(authentication)

# Read taxonomy standard from AKVEG Database
taxa_query = read_file(taxa_file)
taxa_data = as_tibble(dbGetQuery(database_connection, taxa_query))

# Read site visit data from AKVEG Database
site_visit_query = read_file(site_visit_file)
site_visit_data = as_tibble(dbGetQuery(database_connection, site_visit_query)) %>%
  # Convert geometries to points with EPSG:4269
  st_as_sf(x = ., coords = c('longitude_dd', 'latitude_dd'), crs = 4269, remove = FALSE) %>%
  # Reproject coordinates to EPSG 3338
  st_transform(crs = st_crs(3338)) %>%
  # Add EPSG:3338 centroid coordinates
  mutate(cent_x = st_coordinates(.$geometry)[,1],
         cent_y = st_coordinates(.$geometry)[,2]) %>%
  # Subset points to map domain (example to subset using a feature class)
  st_intersection(st_geometry(domain_shape)) %>%
  # Extract raster data to points
  mutate(fire_year = terra::extract(fireyear_raster, ., raw=TRUE)[,2]) %>%
  mutate(coast_dist = terra::extract(coast_raster, ., raw=TRUE)[,2]) %>%
  mutate(elevation = terra::extract(elevation_raster, ., raw=TRUE)[,2]) %>%
  mutate(alpine = terra::extract(alpine_raster, ., raw=TRUE)[,2]) %>%
  mutate(akvwc_fine = terra::extract(akvwc_raster, ., raw=TRUE)[,2]) %>%
  mutate(landfire_evt = terra::extract(landfire_raster, ., raw=TRUE)[,2]) %>%
  mutate(akvwc_fine = paste('m', akvwc_fine, sep = ''),
         landfire_evt = paste('m', landfire_evt, sep = '')) %>%
  # Spatial join region and ecoregion
  st_join(., region_shape) %>%
  st_join(., ecoregion_shape) %>%
  st_join(., mlra_shape) %>%
  st_join(., zone_shape) %>%
  # Drop geometry
  st_zm(drop = TRUE, what = "ZM") %>%
  # Filter by observation year
  filter(year(observe_date) >= 2000) %>%
  # Filter by perspective
  filter(perspective == 'ground') %>%
  # Filter by scope
  filter((scope_vascular == 'exhaustive') | (scope_vascular == 'non-trace species')) %>%
  # Remove sites that burned after observation
  filter(year(observe_date) >= fire_year) %>%
  # Drop geometry
  st_drop_geometry()

# Omit coastal sites
coastal_sites = site_visit_data %>%
  filter((coast_dist < 100) & (elevation < 20))
site_visit_data = site_visit_data %>%
  anti_join(coastal_sites, by = 'site_visit_code')

# Omit all but the most recent site revisit
site_data = site_visit_data %>%
  group_by(site_code) %>%
  summarize(site_visit_n = n(),
            max_year = max(year(observe_date)))
site_visit_data = site_visit_data %>%
  left_join(site_data, by = 'site_code') %>%
  filter(max_year == year(observe_date)) %>%
  select(-site_visit_n, -max_year)

# Write where statement for site visits to apply site visit codes obtained in the spatial intersection above to the SQL queries to restrict data from other tables to only those sites that are within the area of interest 
input_sql = site_visit_data %>%
  select(site_visit_code) %>%
  # Format site visit codes
  mutate(site_visit_code = paste('\'', site_visit_code, '\'', sep = '')) %>%
  # Collapse rows
  summarize(site_visit_code = paste(site_visit_code, collapse=", ")) %>%
  # Pull result out of dataframe
  pull(site_visit_code)
where_statement = paste('\r\nWHERE site_visit.site_visit_code IN (',
                        input_sql,
                        ');',
                        sep = '')

# Read project data from AKVEG Database for selected site visits
project_query = read_file(project_file) %>%
  # Modify query with where statement
  str_replace(., ';', where_statement)
project_data = as_tibble(dbGetQuery(database_connection, project_query)) %>%
  arrange(project_code)

# Read vegetation cover data from AKVEG Database for selected site visits
vegetation_query = read_file(vegetation_file) %>%
  # Modify query with where statement
  str_replace(., ';', where_statement)
vegetation_data = as_tibble(dbGetQuery(database_connection, vegetation_query)) %>%
  # Convert trace values to 0.1%
  mutate(cover_percent = case_when(cover_percent == 0 ~ 0.1,
                                   TRUE ~ cover_percent)) %>%
  # Select absolute foliar cover observations
  filter(cover_type == 'absolute foliar cover') %>%
  # Merge all infraspecies to species
  left_join(taxa_data, by = join_by('code_accepted' == 'code_akveg')) %>%
  mutate(taxon_revised = case_when(grepl('ssp.', name_accepted) ~ str_replace(name_accepted, " ssp..*", ""),
                                   grepl('var.', name_accepted) ~ str_replace(name_accepted, ' var..*', ''),
                                   TRUE ~ name_accepted)) %>%
  # For non-vascular life forms, merge all species to genera
  mutate(taxon_revised = case_when(taxon_category %in% c('hornwort', 'liverwort', 'moss', 'lichen') ~ taxon_genus,
                                   TRUE ~ taxon_revised)) %>%
  # Convert dead vegetation to unique names
  select(site_visit_code, taxon_revised, dead_status, cover_type, cover_percent) %>%
  left_join(taxa_data, by = join_by('taxon_revised' == 'taxon_name')) %>%
  mutate(taxon_code = case_when(dead_status == TRUE ~ paste(code_akveg, 'dead', sep='#'),
                                TRUE ~ code_akveg)) %>%
  select(site_visit_code, taxon_code, cover_percent) %>%
  # Summarize cover data
  group_by(site_visit_code, taxon_code) %>%
  summarize(cover_percent = sum(cover_percent))

# Check number of cover observations per project
project_check = vegetation_data %>%
  left_join(site_visit_data, join_by('site_visit_code')) %>%
  group_by(project_code) %>%
  summarize(obs_n = n())
site_visit_check = vegetation_data %>%
  group_by(site_visit_code) %>%
  summarize(obs_n = n())

# Add tree summary data
tree_list = taxa_data %>%
  filter(taxon_status == 'accepted') %>%
  filter(taxon_habit %in% c('deciduous tree', 'coniferous tree')) %>%
  filter(taxon_accepted != 'Alnus rubra') %>%
  filter(taxon_genus != 'Prunus') %>%
  distinct(code_akveg) %>%
  pull(code_akveg)
summary_data = vegetation_data %>%
  left_join(taxa_data, by = join_by('taxon_code' == 'code_akveg')) %>%
  mutate(tree_percent = case_when(taxon_code %in% tree_list ~ cover_percent,
                                  TRUE ~ 0)) %>%
  mutate(vascular_percent = case_when(taxon_category %in% c('eudicot', 'fern', 'forb', 'gymnosperm',
                                                            'horsetail', 'lycophyte', 'monocot') ~ cover_percent,
                                      TRUE ~ 0)) %>%
  group_by(site_visit_code) %>%
  summarize(tree_percent = sum(tree_percent),
            vascular_percent = sum(vascular_percent),
            total_percent = sum(cover_percent)) %>%
  ungroup()
site_visit_data = site_visit_data %>%
  left_join(summary_data, by = 'site_visit_code')

# Omit sparse & barren sites
sparse_barren = site_visit_data %>%
  filter(vascular_percent <= 20)
site_visit_data = site_visit_data %>%
  anti_join(sparse_barren, by = 'site_visit_code')
vegetation_data = vegetation_data %>%
  anti_join(sparse_barren, by = 'site_visit_code')

#### ASSIGN ANALYSIS GROUPS
####____________________________________________________

# Assign analysis subregions
site_visit_data = site_visit_data %>%
  mutate(subregion = case_when((region == 'Arctic Northern' &
                                mlra == 'Arctic Coastal Plain') ~ 'Arctic Coastal Plain',
                             (region == 'Arctic Northern' &
                                mlra %in% c('Arctic Foothills',
                                            'Northern Brooks Range Mountains',
                                            'Interior Brooks Range Mountains',
                                            'Western Brooks Range Mountains')) ~ 'Arctic Foothills & Mountains',
                             (region == 'Arctic Western' &
                                mlra %in% c('Northern Seward Peninsula-Selawik Lowlands',
                                            'Seward Peninsula Highlands',
                                            'Nulato Hills-Southern Seward Peninsula Highlands')) ~ 'Seward Peninsula',
                             (region == 'Aleutian-Kamchatka' &
                                ecoregion == 'Alaska Peninsula') ~ 'Alaska Peninsula Mountains',
                             (region == 'Aleutian-Kamchatka' &
                                ecoregion == 'Kodiak Island') ~ 'Kodiak Southwest',
                             (region == 'Alaska Southwest' &
                                mlra == 'Bristol Bay-Northern Alaska Peninsula Lowlands') ~ 'Bristol Bay',
                             (region == 'Alaska Southwest' &
                                mlra %in% c('Southern Alaska Peninsula Mountains',
                                            'Interior Alaska Mountains')) ~ 'Southwest Mountains',
                             region == 'Alaska Western' ~ 'Alaska Western',
                             (region == 'Alaska-Yukon Northern' &
                                mlra %in% c('Northern Seward Peninsula-Selawik Lowlands',
                                            'Western Brooks Range Mountains, Foothills, and Valleys')) ~ 'Alaska-Yukon Northwest',
                             (region == 'Alaska-Yukon Central' &
                                mlra == 'Yukon Flats Lowlands') ~ 'Yukon Flats',
                             (region == 'Alaska-Yukon Central' &
                                mlra == 'Interior Alaska Highlands' &
                                ecoregion %in% c('North Ogilvie Mountains',
                                                 'Yukon-Tanana Uplands')) ~ 'Eastern Interior',
                             zone == 'Wrangell-Tetlin' ~ 'Wrangell-Tetlin',
                             zone == 'Denali North' ~ 'Denali North',
                             zone == 'Wrangell-St. Elias' ~ 'Wrangell-St. Elias',
                             zone == 'Denali South' ~ 'Denali South',
                             project_code == 'abr_susitna_2013' ~ 'Susitna Valley',
                             project_code == 'accs_nelchina_2023' ~ 'Nelchina Uplands',
                             (region == 'Alaska Pacific' &
                                project_code %in% c('nps_kenai_2004',
                                                    'nps_kenai_2013',
                                                    'nrcs_soils_2022',
                                                    'accs_chenega_2022')) ~ 'Alaska Pacific Western',
                             TRUE ~ 'unassigned')) %>%
  # Assign focal unit
  mutate(focal_unit = case_when((subregion == 'Bristol Bay' & tree_percent >= 10) ~ 'forest',
                                (subregion == 'Bristol Bay' & tree_percent < 10) ~ 'non-forest',
                                (subregion == 'Eastern Interior' & tree_percent >= 10) ~ 'forest',
                                (subregion == 'Eastern Interior' & tree_percent < 10) ~ 'non-forest',
                                (subregion == 'Denali North' & tree_percent >= 10) ~ 'forest',
                                (subregion == 'Denali North' & tree_percent < 10) ~ 'non-forest',
                                (subregion == 'Alaska Pacific Western' & tree_percent >= 10) ~ 'forest',
                                (subregion == 'Alaska Pacific Western' & tree_percent < 10) ~ 'non-forest',
                                TRUE ~ 'all')) %>%
  # Assign analysis group code
  mutate(group_id = case_when(subregion == 'Arctic Coastal Plain' ~
                                1,
                              subregion == 'Arctic Foothills & Mountains' ~
                                2,
                              subregion == 'Seward Peninsula' ~
                                3,
                              subregion == 'Alaska Peninsula Mountains' ~
                                4,
                              subregion == 'Kodiak Southwest' ~
                                5,
                              subregion == 'Southwest Mountains' ~
                                6,
                              (subregion == 'Bristol Bay' & focal_unit == 'forest') ~
                                7,
                              (subregion == 'Bristol Bay' & focal_unit == 'non-forest') ~
                                8,
                              subregion == 'Alaska Western' ~
                                9,
                              subregion == 'Alaska-Yukon Northwest' ~
                                10,
                              subregion == 'Yukon Flats' ~
                                11,
                              (subregion == 'Eastern Interior' & focal_unit == 'forest') ~
                                12,
                              (subregion == 'Eastern Interior' & focal_unit == 'non-forest') ~
                                13,
                              subregion == 'Wrangell-Tetlin' ~
                                14,
                              (subregion == 'Denali North' & focal_unit == 'forest') ~
                                15,
                              (subregion == 'Denali North' & focal_unit == 'non-forest') ~
                                16,
                              subregion == 'Wrangell-St. Elias' ~
                                17,
                              subregion == 'Denali South' ~
                                18,
                              subregion == 'Nelchina Uplands' ~
                                19,
                              subregion == 'Susitna Valley' ~
                                20,
                              (subregion == 'Alaska Pacific Western' & focal_unit == 'forest') ~
                                21,
                              (subregion == 'Alaska Pacific Western' & focal_unit == 'non-forest') ~
                                22,
                              TRUE ~ -999)) %>%
  # Select columns
  dplyr::select(site_visit_code, project_code, site_code, data_tier, observe_date, scope_vascular,
                scope_bryophyte, scope_lichen, perspective, cover_method, structural_class,
                fire_year, coast_dist, elevation, alpine, akvwc_fine, landfire_evt, biome, region,
                ecoregion, mlra, zone, group_id, subregion, focal_unit, tree_percent, vascular_percent,
                total_percent, homogeneous, plot_dimensions_m, latitude_dd, longitude_dd, cent_x, cent_y)

#### ADD CROSS-VALIDATION AND PREDICTION RESULTS
####____________________________________________________

# Read data frame of combined results
for (indicator in indicators) {
  # Set input files
  validation_input = path(results_folder, indicator, paste(indicator, '_results.csv', sep = ''))
  raster_input = path(raster_folder, indicator, paste(indicator, '_10m_3338.tif', sep = ''))
  
  # Read raster
  indicator_raster = rast(raster_input)
  
  # Read results
  results_data = read_csv(validation_input) %>%
    select(st_vst, prediction) %>%
    rename(site_visit_code = st_vst)
  
  # Left join results to site data
  site_visit_data = site_visit_data %>%
    # Join validation results
    left_join(results_data, by = 'site_visit_code') %>%
    # Convert to spatial points
    st_as_sf(x = ., coords = c('cent_x', 'cent_y'), crs = 3338, remove = FALSE) %>%
    # Extract raster data
    mutate(raster_value = terra::extract(indicator_raster, ., raw=TRUE)[,2]) %>%
    # Fill missing predictions using raster values
    mutate(prediction = case_when(is.na(prediction) ~ raster_value,
                                   TRUE ~ prediction)) %>%
    # Rename values
    rename(!!indicator := prediction) %>%
    # Remove raster values
    select(-raster_value) %>%
    # Drop geometry
    st_zm(drop = TRUE, what = "ZM") %>%
    st_drop_geometry()
}

# Ensure that all site visits have vegetation data
vegetation_sites = vegetation_data %>%
  distinct(site_visit_code)
site_visit_data = site_visit_data %>%
  inner_join(vegetation_sites, by = 'site_visit_code')

#### EXPORT DATA
####____________________________________________________

# Export site visit data to shapefile
site_visit_data %>%
  # Convert geometries to points with EPSG:3338
  st_as_sf(x = ., coords = c('cent_x', 'cent_y'), crs = 3338, remove = FALSE) %>%
  # Rename fields so that they are within the character length limits
  rename(st_vst = site_visit_code,
         prjct_cd = project_code,
         st_code = site_code,
         obs_date = observe_date,
         scp_vasc = scope_vascular,
         scp_bryo = scope_bryophyte,
         scp_lich = scope_lichen,
         perspect = perspective,
         cvr_mthd = cover_method,
         strc_class = structural_class,
         elevat = elevation,
         tree_pct = tree_percent,
         vasc_pct = vascular_percent,
         total_pct = total_percent,
         lndfr_evt = landfire_evt,
         hmgneous = homogeneous,
         plt_dim_m = plot_dimensions_m,
         lat_dd = latitude_dd,
         long_dd = longitude_dd) %>%
  st_write(site_point_output, append = FALSE)

# Prepare region summary
subregion_data = site_visit_data %>%
  # Summarize subregion sites
  group_by(group_id, subregion, focal_unit) %>%
  summarize(original_n = n(),
            min_year = min(year(observe_date)),
            max_year = max(year(observe_date))) %>%
  # Summarize year ranges
  group_by(group_id, subregion, focal_unit) %>%
  mutate(obs_years = paste(toString(min_year), toString(max_year), sep = '-')) %>%
  select(-min_year, -max_year)

# Export data to csv files
taxa_data %>%
  write_csv(., file = taxa_output)
project_data %>%
  write_csv(., file = project_output)
site_visit_data %>%
  write_csv(., file = site_visit_output)
vegetation_data %>%
  write_csv(., file = vegetation_output)

# Export data to xlsx
sheets = list('subregions' = subregion_data)
write_xlsx(sheets, subregion_output, format_headers = FALSE)
