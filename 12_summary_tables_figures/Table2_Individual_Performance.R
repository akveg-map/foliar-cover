# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Table 2. Individual performance
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Table 2. Individual performance" formats a table for publication to display the results of the individual performance assessment at the site scale and local scale.
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
input_folder = path(project_folder, 'Data/Data_Output/model_results', round_date)
output_folder = path(project_folder, 'Documents/Manuscript_FoliarCover_FloristicGradients/tables')

# Define input files
performance_input = path(input_folder, 'performance_table.csv')

# Define output files
performance_output = path(output_folder, 'Table2_Individual_Performance.xlsx')

#### FORMAT PERFORMANCE RESULTS
####____________________________________________________

# Format performance results
performance_data = read_csv(performance_input) %>%
  select(indicator_name, r2_site, rmse_site, auc_site, acc_site, r2_scaled, rmse_scaled, n_presence, cover_mean) %>%
  mutate(r2_site = round(r2_site, 2),
         rmse_site = str_c(round(rmse_site, 0), '%'),
         auc_site = round(auc_site, 2),
         acc_site = str_c(round(acc_site, 0), '%'),
         r2_scaled = round(r2_scaled, 2),
         rmse_scaled = str_c(round(rmse_scaled, 0), '%'),
         cover_median = str_c(round(cover_median, 0), '%'),
         cover_mean = str_c(round(cover_mean, 0), '%')
         ) %>%
  rename(Indicator = indicator_name,
         Presences = n_presence,
         R2 = r2_site,
         RMSE = rmse_site,
         AUC = auc_site,
         `% ACC` = acc_site,
         `R2 (ls)` = r2_scaled,
         `RMSE (ls)` = rmse_scaled,
         median = cover_median,
         mean = cover_mean)

# Export data to xlsx
sheets = list('performance' = performance_data)
write_xlsx(sheets, performance_output, format_headers = FALSE)
