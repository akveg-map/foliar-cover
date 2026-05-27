# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Table 3. Ordination and clustering results
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Table 3. Ordination and clustering results" formats a table for publication to display the results of the ordination and clustering from field data.
# ---------------------------------------------------------------------------

# Import required libraries
library(dplyr)
library(fs)
library(readr)
library(readxl)
library(writexl)
library(stringr)
library(tibble)
library(tidyr)

# Set round date
round_date = 'round_20241124'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = path(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
input_folder = path(project_folder, 'Data/Data_Output/ordination_results', round_date)
output_folder = path(project_folder, 'Documents/Manuscript_FoliarCover_FloristicGradients/tables')

# Define input files
ordination_input = path(input_folder, '00_Subregion_Performance.xlsx')

# Define output files
ordination_output = path(output_folder, 'Table3_Ordination_Clustering.xlsx')

#### FORMAT ORDINATION RESULTS
####____________________________________________________

# Format ordination results
ordination_data = read_xlsx(ordination_input, sheet = 'summary') %>%
  filter(!is.na(group_id)) %>%
  mutate(noise_pct = (original_n - selected_n)/original_n)
ordination_results = ordination_data %>%
  mutate(`Benchmark Dataset` = case_when(focal_unit == 'all' ~ subregion,
                                         focal_unit != 'all' ~ str_c(subregion, ' (', focal_unit, ')'),
                                         TRUE ~ 'error')) %>%
  select(`Benchmark Dataset`, obs_years, selected_n, nmds_stress, cluster_n, mean_var, mean_sil, gam_clust) %>%
  mutate(nmds_stress = round(nmds_stress, 2),
         mean_var = round(mean_var, 2),
         mean_sil = round(mean_sil, 2),
         gam_clust = str_c(round((gam_clust * 100), 0), '%')
         ) %>%
  rename(`Obs. Years` = obs_years,
         Count = selected_n,
         Stress = nmds_stress,
         Clusters = cluster_n,
         `Var.` = mean_var,
         `Sil.` = mean_sil,
         `% Inf.` = gam_clust)

# Calculate the relationship between NMDS stress and 
r =  cor.test(ordination_data$nmds_stress, ordination_data$selected_n, 
                method = "pearson")

# Calculate text summary data
summary_data = tibble(subregion_n = length(unique(ordination_data$subregion)),
                      focal_n = nrow(ordination_data) - length(unique(ordination_data$subregion)),
                      benchmark_n = nrow(ordination_data),
                      original_n = sum(ordination_data$original_n),
                      noise_pct_mean = mean(ordination_data$noise_pct),
                      noise_pct_sd = sd(ordination_data$noise_pct),
                      noise_pct_min = min(ordination_data$noise_pct),
                      noise_pct_max = max(ordination_data$noise_pct),
                      selected_n = sum(ordination_data$selected_n),
                      selected_min = min(ordination_data$selected_n),
                      selected_max = max(ordination_data$selected_n),
                      stress_mean = mean(ordination_data$nmds_stress),
                      stress_sd = sd(ordination_data$nmds_stress),
                      stress_min = min(ordination_data$nmds_stress),
                      stress_max = max(ordination_data$nmds_stress),
                      stress_n_pearson = as.numeric(r$estimate),
                      gam_clust_mean = mean(ordination_data$gam_clust),
                      gam_clust_sd = sd(ordination_data$gam_clust),
                      scaled_ind_mean = mean(ordination_data$scaled_ind),
                      scaled_ind_sd = sd(ordination_data$scaled_ind),
                      scaled_akvwc_mean = mean(ordination_data$scaled_akvwc),
                      scaled_akvwc_sd = sd(ordination_data$scaled_akvwc),
                      scaled_lf_mean = mean(ordination_data$scaled_lf),
                      scaled_lf_sd = sd(ordination_data$scaled_lf)
                      )
summary_data = summary_data %>%
  mutate_all(as.character) %>%
  pivot_longer(colnames(summary_data), names_to = 'characteristic', values_to = 'value')

# Export data to xlsx
sheets = list('table' = ordination_results, 'text' = summary_data)
write_xlsx(sheets, ordination_output, format_headers = FALSE)
