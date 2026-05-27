# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Noise cluster comparison
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-05-26
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Noise cluster comparison" creates comparison tables by subregions and focal units for performance metrics from fuzzy noise clustering results with different numbers of clusters.
# ---------------------------------------------------------------------------

# Import required libraries
library(dplyr)
library(fs)
library(ggplot2)
library(metR)
library(janitor)
library(lubridate)
library(readr)
library(writexl)
library(stringr)
library(tibble)
library(tidyr)
library(sf)
library(cluster)
library(vegan)
library(vegan3d)
library(vegclust)
library(rgl)
library(indicspecies)
library(viridis)
library(mgcv)

# Set random seed
set.seed(314)

# Set round date
round_date = 'version_20260415'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory (modify to your folder structure)
drive = 'C:'
root_folder = 'ACCS_Work'

# Define input folders (modify to your folder structure)
project_folder = path(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
database_folder = path(project_folder, 'Data_Input/database_archive', round_date)
input_folder = path(project_folder, 'Data_Input/ordination_data', round_date)

# Define input files
taxonomy_input = path(database_folder, '00_taxonomy.csv')
site_visit_input = path(input_folder, 'site_visit_data.csv')
vegetation_input = path(input_folder, 'vegetation_data.csv')

# Source function for noise cluster comparison (fuzzy_nc_compare)
function_script = path(drive, root_folder,
                       'Repositories/foliar-cover/11_combined_performance/00_Function_Noise_Cluster_Compare.R')
source(function_script)

# Identify group number
site_data = read_csv(site_visit_input)
group_number = max(site_data$group_id)

#### COMPARE CLUSTER SOLUTIONS FOR EACH GROUP
####____________________________________________________

count = 1
while (count <= group_number) {
  print(paste('Processing group ', count, ' of ', group_number, '...'))
  
  # Define output file
  if (count < 10) {
    nc_output = path(project_folder, 'Data_Output/ordination_results', round_date,
                     paste('0', toString(count), '_noise_clusters.xlsx', sep = ''))
  } else {
    nc_output = path(project_folder, 'Data_Output/ordination_results', round_date,
                     paste(toString(count), '_noise_clusters.xlsx', sep = ''))
  }
  
  
  if (!file.exists(nc_output)) {
    print(count)
    
    # Read site visit data
    site_data = read_csv(site_visit_input) %>%
      filter(group_id == count) %>%
      arrange(site_visit_code)
    
    # Create list of site visits
    site_visit_list = site_data %>%
      distinct(site_visit_code) %>%
      pull(site_visit_code)
    
    # Read and select vegetation data
    vegetation_data = read_csv(vegetation_input) %>%
      filter(site_visit_code %in% site_visit_list) %>%
      select(site_visit_code, taxon_code, cover_percent)
    
    # Convert vegetation data to matrix
    initial_matrix = vegetation_data %>%
      # Convert to wide format
      pivot_wider(names_from = taxon_code, values_from = cover_percent) %>%
      # Convert NA values to zero
      replace(is.na(.), 0) %>%
      # Arrange data
      arrange(site_visit_code) %>%
      # Convert st_vst column to row names
      column_to_rownames(var='site_visit_code')
    
    # Normalize vegetation matrix
    initial_normalized = decostand(initial_matrix, method='normalize')
    
    # Compare noise clustering with different cluster numbers
    noise_results = fuzzy_nc_compare(initial_normalized, 4, 12)
    
    # Format cluster results
    cluster_variance = noise_results %>%
      select(cluster, variance, cluster_n) %>%
      pivot_wider(names_from = cluster, values_from = variance)
    nc_comparison = noise_results %>%
      filter(cluster != 'N') %>%
      group_by(cluster_n) %>%
      summarize(mean_variance = mean(variance),
                mean_sil = mean(avg_sil)) %>%
      ungroup() %>%
      left_join(cluster_variance, by = 'cluster_n') %>%
      arrange(cluster_n) %>%
      relocate(N, .after = last_col())
    
    # Export data to xlsx
    nc_sheets = list('noise' = nc_comparison)
    write_xlsx(nc_sheets, nc_output)
  }
  
  count = count + 1
  
}
