# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Summarize project data
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Summarize project data" creates a table for publication to display a summary of the characteristics per project of data used to train and validate foliar cover maps.
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

# Set root directory
drive = 'C:'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = path(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
extract_folder = path(project_folder, 'Data/Data_Input/database_extract', round_date)
results_folder = path(project_folder, 'Data/Data_Output/model_results', round_date)
output_folder = path(project_folder, 'Documents/Manuscript_FoliarCover_FloristicGradients/tables')

# Define input files
taxa_input = path(extract_folder, '00_taxonomy.csv')
project_input = path(extract_folder, '01_project.csv')
site_input = path(extract_folder, '03_site_visit_extract_3338.csv')
vegetation_input = path(extract_folder, '05_vegetation.csv')
abiotic_input = path(extract_folder, '06_abiotic_top_cover.csv')
fireyear_input = path(project_folder, 'Data/Data_Input/ancillary_data/processed/AlaskaYukon_FireYear_10m_3338.tif')

# Define output files
summary_output = path(output_folder, '00_Training_Data_Summary.xlsx')

#### LOAD DATABASE EXTRACTIONS
####____________________________________________________

# Read local data
fireyear_raster = rast(fireyear_input)

# Read taxonomic data
taxa_data = read_csv(taxa_input)

# Read project data from AKVEG Database
project_data = read_csv(project_input) %>%
  mutate(private = case_when(project_code == 'nps_cakn_2021' ~ FALSE,
                             TRUE ~ private))

# Read site visit data from AKVEG Database
site_visit_data = read_csv(site_input) %>%
  select(st_vst, prjct_cd, st_code, obs_date, obs_year, scp_vasc, scp_bryo, scp_lich, perspect, cvr_mthd, lat_dd, long_dd) %>%
  rename(site_visit_code = st_vst,
         project_code = prjct_cd,
         site_code = st_code,
         observe_date = obs_date,
         observe_year = obs_year,
         scope_vascular = scp_vasc,
         scope_bryophyte = scp_bryo,
         scope_lichen = scp_lich,
         perspective = perspect,
         cover_method = cvr_mthd,
         latitude_dd = lat_dd,
         longitude_dd = long_dd) %>%
  # Convert geometries to points with EPSG:4269
  st_as_sf(x = ., coords = c('longitude_dd', 'latitude_dd'), crs = 4269, remove = FALSE) %>%
  # Reproject coordinates to EPSG 3338
  st_transform(crs = st_crs(3338)) %>%
  # Extract raster data to points
  mutate(fire_year = terra::extract(fireyear_raster, ., raw=TRUE)[,2]) %>%
  # Drop geometry
  st_zm(drop = TRUE, what = "ZM") %>%
  # Drop geometry
  st_drop_geometry()
  
# Read vegetation data from AKVEG Database
vegetation_data = read_csv(vegetation_input) %>%
  rename(site_visit_code = st_vst,
         cover_type = cvr_type,
         cover_percent = cvr_pct)

# Read abiotic top cover data from AKVEG Database
abiotic_data = read_csv(abiotic_input)

# Compile sites from vegetation and abiotic cover
vegetation_sites = vegetation_data %>%
  distinct(site_visit_code)
abiotic_sites = abiotic_data %>%
  distinct(site_visit_code)
site_check = rbind(vegetation_sites, abiotic_sites) %>%
  distinct(site_visit_code)

# Check that no site visits lack data for either vegetation cover or abiotic top cover
site_visit_nodata = site_visit_data %>%
  anti_join(site_check, by = 'site_visit_code')
site_visit_data = site_visit_data %>%
  inner_join(site_check, by = 'site_visit_code')

# Identify public data
site_visit_public = site_visit_data %>%
  left_join(project_data, by = 'project_code') %>%
  filter(private == FALSE)

#### COMPILE SELECTED SITE VISITS
####____________________________________________________

# Prepare empty data frames
site_visit_selected = tibble(site_visit_code = 'a')[0,]
site_visit_count = tibble(indicator = 'a', site_visits = 1, presence = 1, absence = 1)[0,]

# Read data frame of combined selected data
for (indicator in indicators) {
  # Set input files
  indicator_input = path(results_folder, indicator, paste(indicator, '_results.csv', sep = ''))
  
  # Read results
  indicator_data = read_csv(indicator_input) %>%
    rename(site_visit_code = st_vst,
           cover_percent = cvr_pct) %>%
    select(site_visit_code, cover_percent) %>%
    mutate(indicator = indicator)
  
  # Process indicator site visits
  indicator_sites = indicator_data %>%
    distinct(site_visit_code)
  
  # Store number of site visits per indicator
  indicator_count = indicator_data %>%
    inner_join(site_visit_data, by = 'site_visit_code') %>%
    mutate(presence = case_when(cover_percent >= 3 ~ 1,
                                TRUE ~ 0)) %>%
    group_by(indicator) %>%
    summarize(site_visits = n(), presence = sum(presence))
  indicator_count = indicator_count %>%
    mutate(absence = site_visits - presence)
  
  # Bind rows
  site_visit_selected = rbind(site_visit_selected, indicator_sites)
  site_visit_count = rbind(site_visit_count, indicator_count)
  
}
site_visit_selected = site_visit_selected %>%
  distinct(site_visit_code)

# Identify unique selected sites across all indicators
absence_data = site_visit_selected %>%
  distinct(site_visit_code) %>%
  anti_join(site_visit_data, by = 'site_visit_code') %>%
  filter(grepl('ABS-', site_visit_code))
site_visit_final = site_visit_selected %>%
  anti_join(absence_data, by = 'site_visit_code') %>%
  anti_join(site_visit_nodata, by = 'site_visit_code') %>%
  left_join(site_visit_data, by = 'site_visit_code') %>%
  filter(!is.na(project_code))

#### SUMMARIZE AKVEG DATABASE
####____________________________________________________

# Summarize vegetation observations
vegetation_observations = vegetation_data %>%
  left_join(taxa_data, by = join_by('code_accepted' == 'code_akveg')) %>%
  filter(taxon_category != 'unknown')

# Summarize number of original visits and revisits
site_visit_summary = site_visit_data %>%
  group_by(site_code) %>%
  summarize(site_visit_n = n(),
            min_year = min(year(observe_date)),
            max_year = max(year(observe_date)))
original_visit_data = site_visit_data %>%
  left_join(site_visit_summary, by = 'site_code') %>%
  filter(min_year == year(observe_date)) %>%
  select(-site_visit_n, -min_year, -max_year)
revisit_data = site_visit_data %>%
  anti_join(original_visit_data, by = 'site_visit_code')

# Summarize site visits within year range
site_visit_potential = site_visit_data %>%
  filter(year(observe_date) >= 2000 & year(observe_date) <= 2024)

# Summarize site visits removed by fire
fire_remove_data = site_visit_potential %>%
  filter(year(observe_date) < fire_year)
fire_include_data = site_visit_potential %>%
  filter(year(observe_date) >= fire_year)

# Summarize number of selected sites
max_selected_number = max(site_visit_count$site_visits)
min_selected_number = min(site_visit_count$site_visits)
max_selected_indicator = site_visit_count %>%
  filter(site_visits == max_selected_number) %>%
  pull(indicator)
min_selected_indicator = site_visit_count %>%
  filter(site_visits == min_selected_number) %>%
  pull(indicator)
max_selected_indicators = ''
for (indicator in max_selected_indicator) {
  max_selected_indicators = paste(max_selected_indicators, indicator, sep = ', ')
}
max_selected_indicators = str_sub(max_selected_indicators, 3, -1)
min_selected_indicators = ''
for (indicator in min_selected_indicator) {
  min_selected_indicators = paste(min_selected_indicators, indicator, sep = ', ')
}
min_selected_indicators = str_sub(min_selected_indicators, 3, -1)

# Summarize selected projects
project_selected = site_visit_final %>%
  distinct(project_code)

#### CREATE SITE VISIT DATASET FOR PLOTTING
####____________________________________________________

# Process cover type
cover_data = vegetation_data %>%
  distinct(site_visit_code, cover_type)

# Identify unique selected sites across all indicators
site_visit_export = site_visit_final %>%
  inner_join(cover_data, by = 'site_visit_code') %>%
  mutate(cover_version = case_when((cover_type == 'absolute canopy cover' | cover_type == 'absolute foliar cover') ~ 'absolute',
                                   (cover_type == 'top canopy cover' | cover_type == 'top foliar cover') ~ 'top',
                                   TRUE ~ 'error'))

#### EXPORT SUMMARY DATA
####____________________________________________________

# Create export table
summary_data = tibble(project_total = nrow(project_data),
                      site_visit_total = nrow(site_visit_data),
                      public_percentage = round((nrow(site_visit_public)/nrow(site_visit_data)) * 100, 0),
                      public_number = nrow(site_visit_public),
                      original_visit_number = nrow(original_visit_data),
                      revisit_number = nrow(revisit_data),
                      vegetation_total = nrow(vegetation_observations),
                      potential_number = nrow(site_visit_potential),
                      fire_remove = nrow(fire_remove_data),
                      fire_include = nrow(fire_include_data),
                      other_omit = nrow(fire_include_data) - nrow(site_visit_final),
                      project_selected = nrow(project_selected),
                      combined_selected = nrow(absence_data) + nrow(site_visit_final),
                      absence_selected = nrow(absence_data),
                      site_visit_selected = nrow(site_visit_final),
                      max_selected_number = max_selected_number,
                      max_selected_indicator = max_selected_indicators,
                      min_selected_number = min_selected_number,
                      min_selected_indicator = min_selected_indicators)
summary_data = summary_data %>%
  mutate_all(as.character) %>%
  pivot_longer(colnames(summary_data), names_to = 'characteristic', values_to = 'value')

# Export data to xlsx
sheets = list('summary' = summary_data, 'site_visits' = site_visit_count, 'data' = site_visit_export)
write_xlsx(sheets, summary_output, format_headers = FALSE)
