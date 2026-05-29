# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Performance comparison
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-05-28
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Performance comparison" creates a 3-axis NMDS ordination of plant community composition data and models the deviance explained across the three ordination axes relative to the results of a selected set of clusters. The deviance explained by the clusters then provides a baseline to compare the deviance predicted by the AKVEG foliar cover maps, the Alaska Vegetation and Wetland Composite, and the Landfire 2023 EVT.
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

# Identify group number
site_data = read_csv(site_visit_input)
group_number = max(site_data$group_id)

#### COMPARE PERFORMANCE FOR EACH GROUP
####____________________________________________________

# Initialize an empty list to store the results
cluster_results_list = list()

count = 1
while (count <= group_number) {
  
  # Define input and output files
  if (count < 10) {
    noise_input = path(results_folder, paste('0', toString(count), '_noise_membership.xlsx', sep = ''))
    hardc_input = path(results_folder, paste('0', toString(count), '_hardc_clusters.xlsx', sep = ''))
    performance_output = path(results_folder, paste('0', toString(count), '_performance.xlsx', sep = ''))
    stress_output = path(results_folder, paste('0', toString(count), '_stress.jpg', sep = ''))
  } else {
    noise_input = path(results_folder, paste(toString(count), '_noise_membership.xlsx', sep = ''))
    hardc_input = path(results_folder, paste(toString(count), '_hardc_clusters.xlsx', sep = ''))
    performance_output = path(results_folder, paste(toString(count), '_performance.xlsx', sep = ''))
    stress_output = path(results_folder, paste(toString(count), '_stress.jpg', sep = ''))
  }
  
  if (!file.exists(performance_output)) {
    print(count)
    
    #### CONDUCT CLUSTERING
    ####____________________________________________________
    
    # Identify noise cluster number
    hardc_cluster_n = read_excel(hardc_input, sheet = 'hardc') %>%
      # Select summary columns
      select(cluster_n, mean_sil, mean_variance) %>%
      # Retain only the largest 50% of silhouette widths to avoid indistinct clusters
      slice_max(order_by = mean_sil, prop = 0.66) %>%
      # Retain silhouette widths that are greater than 75% of the maximum silhouette width
      filter(mean_sil >= (max(mean_sil, na.rm = TRUE) * 0.75)) %>%
      # Retain silhoette widths larger than 0.11
      filter(mean_sil >= 0.11) %>%
      # Assign ordinal ranks
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
    
    # Conduct clustering with n clusters
    print(paste('Hard c-medoid cluster number for group ', toString(count), ': ', toString(hardc_cluster_n)))
    
    # Store the result for this group as a tibble inside the list
    cluster_results_list[[count]] = tibble(group_id = count, hardc_cluster_n = hardc_cluster_n)
    
  }
  count = count + 1
}

# Bind all the list elements into a single, clean dataframe
final_cluster_df = bind_rows(cluster_results_list)