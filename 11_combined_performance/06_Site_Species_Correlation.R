# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Calculate site and species number correlations
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-05-29
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Calculate site and species number correlations" calculates the Pearson correlations between NMDS stress and number of sites or species per subregion. The script prints (rather than exports) the correlation values.
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
input_folder = path(project_folder, 'Data_Input/ordination_data', round_date)
results_folder = path(project_folder, 'Data_Output/ordination_results', round_date)
output_folder = path(project_folder, 'Data_Output/summary_results', round_date)

# Define input files
subregion_input = path(output_folder, 'Table2_Clustering_Performance.xlsx')
vegetation_input = path(input_folder, 'vegetation_data.csv')

# Identify group number
subregion_data = read_excel(subregion_input, sheet = 'Table2') %>%
  rename(count = Count,
         nmds_stress = `NMDS Stress`) %>%
  select(group_id, count, nmds_stress) %>%
  mutate(taxa_n = 0)
vegetation_data = read_csv(vegetation_input)
group_number = max(subregion_data$group_id)

#### SUMMARIZE TAXA NUMBERS
####____________________________________________________

# Calculate taxa number per group
group_count = 1
while (group_count <= group_number) {
  
  # Define input and output files
  if (group_count < 10) {
    noise_input = path(results_folder, paste('0', toString(group_count), '_noise_membership.xlsx', sep = ''))
  } else {
    noise_input = path(results_folder, paste(toString(group_count), '_noise_membership.xlsx', sep = ''))
  }
  
  # Read noise membership
  site_visit_data = read_xlsx(noise_input, sheet = 'noise') %>%
    filter(N < 0.85) # Eliminate site visits that were assigned to the noise cluster
  
  # Summarize taxa number
  taxa_unique = site_visit_data %>%
    left_join(vegetation_data, by = 'site_visit_code') %>%
    distinct(taxon_code)
  
  # Add taxon number to subregion summary
  subregion_data = subregion_data %>%
    mutate(taxa_n = case_when(group_id == group_count ~ nrow(taxa_unique),
                                TRUE ~ taxa_n))
  
  # Increase group count
  group_count = group_count + 1

}

#### CALCULATE CORRELATION
####____________________________________________________

pearson_sites = cor.test(subregion_data$nmds_stress, subregion_data$count, method = 'pearson')
pearson_taxa = cor.test(subregion_data$nmds_stress, subregion_data$taxa_n, method = 'pearson')
