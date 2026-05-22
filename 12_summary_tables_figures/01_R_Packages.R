# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Compile R packages
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Compile R packages" compiles a list of R packages and versions into a csv table.
# ---------------------------------------------------------------------------

# Import required libraries
library(fs)
library(dplyr)
library(tibble)

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = path(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
output_folder = path(project_folder, 'Documents/Manuscript_FoliarCover_FloristicGradients/appendix_s2/data_output')

# Define output files
library_output = path(output_folder, 'AppendixS2_R_Packages.csv')

#### COMPILE AND EXPORT LIST OF LIBRARIES AND VERSIONS
####____________________________________________________

# Get matrix of libraries
library_data = as_tibble(installed.packages()) %>%
  rename(Name = Package) %>%
  select(Name, Version)

# Export library dataframe
write.csv(library_data, library_output, fileEncoding = 'UTF-8', row.names = FALSE)
