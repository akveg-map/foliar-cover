# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Appendix S2 software table
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Appendix S2 software table" compiles table of software used to develop the AKVEG foliar cover maps and exports a text list of citations.
# ---------------------------------------------------------------------------

# Import required libraries
library(fs)
library(dplyr)
library(readr)
library(readxl)
library(tibble)
library(writexl)

# Define arcpy version
arcpy = '3.6.0'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = path(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
input_folder = path(project_folder, 'Documents/Manuscript_FoliarCover_FloristicGradients/appendix_s2/data_input')
output_folder = path(project_folder, 'Documents/Manuscript_FoliarCover_FloristicGradients/appendix_s2/data_output')

# Define input files
python_input = path(output_folder, 'AppendixS2_Python_Packages.csv')
R_input = path(output_folder, 'AppendixS2_R_Packages.csv')
package_input = path(input_folder, 'Software_Dependencies_20251216.xlsx')

# Define output files
table_output = path(output_folder, 'AppendixS2_Software_Table.xlsx')
citations_output = path(output_folder, 'AppendixS2_Citations.txt')

#### COMPILE AND EXPORT LIST OF LIBRARIES AND VERSIONS
####____________________________________________________

# Read input data
python_data = read_csv(python_input)
R_data = read_csv(R_input)

# Join version numbers to package data
package_data = read_xlsx(package_input, sheet='packages') %>%
  left_join(python_data, by = 'Name') %>%
  rename('pversion' = 'Version') %>%
  mutate(pversion = case_when(Name == 'arcpy' ~ arcpy,
                              TRUE ~ pversion)) %>%
  left_join(R_data, by = 'Name') %>%
  rename('rversion' = 'Version') %>%
  mutate(Version = case_when(is.na(pversion) ~ rversion,
                             TRUE ~ pversion)) %>%
  select(-pversion, -rversion)

# Format a citations list
citation_data = package_data %>%
  select(Citation_Full) %>%
  arrange(tolower(Citation_Full))

# Format table for publication
table_data = package_data %>%
  select(Platform, Purpose, Task, Name, Version, Citation)

# Export citations to text file
citation_data %>%
  pull(Citation_Full) %>%
  write_lines(citations_output)

# Export table
write_xlsx(table_data, path = table_output)
