# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Compile results
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Compile results" creates a summary table of the ordination and clustering results from all subregions.
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
round_date = 'round_20241124'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:'
root_folder = 'ACCS_Work'

# Define input folders
project_folder = path(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
input_folder = path(project_folder, 'Data_Input/ordination_data')

# Define input files
subregion_input = path(input_folder, 'subregion_summary.xlsx')

# Define output file
subregion_output = path(project_folder, 'Data_Output/ordination_results', round_date, '00_Subregion_Performance.xlsx')

# Read subregion data
subregion_data = read_xlsx(subregion_input, sheet = 'subregions') %>%
  filter(group_id != -999)
equation_data = read_xlsx(subregion_input, sheet = 'subregions') %>%
  filter(group_id != -999) %>%
  select(group_id, subregion)

# Identify group number
group_number = max(subregion_data$group_id)

#### READ PERFORMANCE DATA
####____________________________________________________

# Prepare empty data frames
performance_rows = tibble(group_id = 0,
                          selected_n = 0,
                          cluster_n = 0,
                          mean_var = 0,
                          mean_sil = 0,
                          nmds_stress = 0,
                          gam_clust = 0,
                          gam_ind = 0,
                          gam_akvwc = 0,
                          gam_lf = 0,
                          scaled_ind = 0,
                          scaled_akvwc = 0,
                          scaled_lf = 0)[0,]
equation_rows = tibble(group_id = 0,
                       gam_equation = '')[0,]

count = 1
while (count <= group_number) {
  
  # Define input file
  if (count < 10) {
    ordination_input = path(project_folder, 'Data_Output/ordination_results', round_date,
                             paste('0', toString(count), '_Performance.xlsx', sep = ''))
  } else {
    ordination_input = path(project_folder, 'Data_Output/ordination_results', round_date,
                             paste(toString(count), '_Performance.xlsx', sep = ''))
  }
  
  # Read performance results
  performance_row = read_xlsx(ordination_input, sheet = 'summary')
  equation_row = read_xlsx(ordination_input, sheet = 'equation') %>%
    mutate(group_id = count)
  
  # Bind rows
  performance_rows = rbind(performance_rows, performance_row)
  equation_rows = rbind(equation_rows, equation_row)
  
  # Increase count
  count = count + 1
  
}

# Join results
subregion_data = subregion_data %>%
  left_join(performance_rows, by = 'group_id') %>%
  select(group_id, subregion, focal_unit, obs_years, original_n, selected_n,	cluster_n,
         mean_var,	mean_sil,	nmds_stress,	gam_clust,	gam_ind,	gam_akvwc,	gam_lf,
         scaled_ind,	scaled_akvwc,	scaled_lf)
equation_data = equation_data %>%
  left_join(equation_rows, by = 'group_id')

# Export data to xlsx
sheets = list('summary' = subregion_data, 'equation' = equation_data)
write_xlsx(sheets, subregion_output)
  