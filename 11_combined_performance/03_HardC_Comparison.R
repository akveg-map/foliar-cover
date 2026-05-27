# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Hard-c medoids comparison
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-05-27
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Hard-c medoids cluster comparison" creates comparison tables by subregions and focal units for performance metrics from hard-c medoid clustering results with different numbers of clusters. This script also identifies outlier plots from a selected cluster number from fuzzy noise clustering.
# ---------------------------------------------------------------------------

# Import required libraries
library(dplyr)
library(fs)
library(ggplot2)
library(metR)
library(janitor)
library(lubridate)
library(readr)
library(readxl)
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
results_folder = path(project_folder, 'Data_Output/ordination_results', round_date)

# Define input files
taxonomy_input = path(database_folder, '00_taxonomy.csv')
site_visit_input = path(input_folder, 'site_visit_data.csv')
vegetation_input = path(input_folder, 'vegetation_data.csv')

# Source function for hard-c cluster comparison
function_script = path(drive, root_folder,
                       'Repositories/foliar-cover/11_combined_performance/00_Function_HardC_Cluster_Compare.R')
source(function_script)

# Read cluster centers
#cluster_centers = read_xlsx(centers_input, sheet = 'noise') # Centers should be set manually be evaluating cluster comparisons

# Identify group number
site_data = read_csv(site_visit_input)
group_number = max(site_data$group_id)

#### COMPARE PERFORMANCE FOR EACH GROUP
####____________________________________________________

count = 1
while (count <= group_number) {
  
  # Define input and output files
  if (count < 10) {
    noise_input = path(results_folder, paste('0', toString(count), '_noise_clusters.xlsx', sep = ''))
    noise_output = path(results_folder, paste('0', toString(count), '_noise_membership.xlsx', sep = ''))
    hardc_output = path(results_folder, paste('0', toString(count), '_hardc_clusters.xlsx', sep = ''))
  } else {
    noise_input = path(results_folder, paste(toString(count), '_noise_clusters.xlsx', sep = ''))
    noise_output = path(results_folder, paste(toString(count), '_noise_membership.xlsx', sep = ''))
    hardc_output = path(results_folder, paste(toString(count), '_hardc_clusters.xlsx', sep = ''))
  }
  
  if (!file.exists(hardc_output)) {
    
    #### CONDUCT CLUSTERING
    ####____________________________________________________
    
    # Identify noise cluster number
    noise_cluster_n = read_excel(noise_input, sheet = 'noise') %>%
      select(cluster_n, mean_sil, mean_variance) %>%
      mutate(
        sil_rank = min_rank(desc(mean_sil)), # Descending ordinal ranks for silhouette width
        var_rank = min_rank(mean_variance), # Ascending ordinal ranks for within-cluster variance
        combined_rank = sil_rank + var_rank # Combine the ordinal ranks
      ) %>%
      # Sort by lowest combined rank with ties broken by smaller cluster number
      arrange(combined_rank, cluster_n) %>% 
      # Keep only the top performing row
      slice(1) %>%                               
      # Extract just the numerical value of the best cluster
      pull(cluster_n)
    
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
    
    # Conduct clustering with n clusters
    print(paste('Noise cluster number for group ', toString(count), ': ', toString(noise_cluster_n)))
    print(paste('Conducting noise clustering for group ', toString(count), '...', sep = ''))
    nc_results = vegclust(x = initial_normalized,
                          mobileCenters = noise_cluster_n, 
                          method = 'NC',
                          m = 1.2,
                          dnoise = 0.8,
                          nstart = 50)
    
    # Extract noise cluster membership
    nc_membership = tibble(nc_results$memb) %>%
      mutate_if(is.numeric, round, 2)
    
    # Identify outlier sites from noise cluster
    noise_data = initial_normalized %>%
      rownames_to_column('site_visit_code') %>%
      select('site_visit_code') %>%
      cbind(., tibble(nc_membership)) %>%
      select('site_visit_code', 'N')
    outlier_data = noise_data %>%
      filter(N >= 0.85)
    
    # Bind clusters and membership to site data
    ordination_data = site_data %>%
      anti_join(outlier_data, by = 'site_visit_code')
    vegetation_subset = vegetation_data %>%
      anti_join(outlier_data, by = 'site_visit_code')
    
    #### CONDUCT HARD C CLUSTERING
    ####____________________________________________________
    
    # Convert vegetation data to matrix
    revised_matrix = vegetation_subset %>%
      # Convert to wide format
      pivot_wider(names_from = taxon_code, values_from = cover_percent) %>%
      # Convert NA values to zero
      replace(is.na(.), 0) %>%
      # Arrange data
      arrange(site_visit_code) %>%
      # Convert st_vst column to row names
      column_to_rownames(var='site_visit_code')
    
    # Normalize vegetation matrix
    revised_normalized = decostand(revised_matrix, method='normalize')
    
    # Compare hard-c clustering with different cluster numbers
    maximum_value = round(sqrt(nrow(ordination_data)), 0) * 2
    if (maximum_value > 30) {
      maximum_value = 30
    }
    cluster_results = hardc_compare(revised_normalized, 10, maximum_value)
    
    # Format cluster results
    cluster_variance = cluster_results %>%
      select(cluster, variance, cluster_n) %>%
      pivot_wider(names_from = cluster, values_from = variance)
    hardc_comparison = cluster_results %>%
      group_by(cluster_n) %>%
      summarize(mean_variance = mean(variance),
                mean_sil = mean(avg_sil)) %>%
      ungroup() %>%
      left_join(cluster_variance, by = 'cluster_n') %>%
      arrange(cluster_n)
    
    # Export data to xlsx
    hardc_sheets = list('hardc' = hardc_comparison)
    noise_sheets = list('noise' = noise_data)
    write_xlsx(hardc_sheets, hardc_output)
    write_xlsx(noise_sheets, noise_output)
  }
  
  count = count + 1
  
}
