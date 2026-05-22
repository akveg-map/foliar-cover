# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Appendix S5 project table
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-22
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Appendix S5 project table" compiles table of field survey projects and associated number of site visits used to develop the AKVEG foliar cover maps.
# ---------------------------------------------------------------------------

# Import required libraries
library(fs)
library(dplyr)
library(readr)
library(readxl)
library(RPostgres)
library(stringr)
library(tibble)
library(writexl)

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:'
root_folder = 'ACCS_Work'

# Set repository directory
database_repository = path(drive, root_folder, 'Repositories/akveg-database-public')
credentials_folder = path(drive, root_folder, 'Credentials/akveg_private_read')

# Define folder structure
project_folder = path(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
input_folder = path(project_folder, 'Documents/Manuscript_FoliarCover_FloristicGradients/tables')
citations_folder = path(drive, root_folder,
                        'OneDrive - University of Alaska/ACCS_Teams/Vegetation/AKVEG_Database/Data/Tables_Metadata')
output_folder = path(project_folder, 'Documents/Manuscript_FoliarCover_FloristicGradients/appendix_s5')

# Define input files
site_input = path(input_folder, '00_Training_Data_Summary.xlsx')
citations_input = path(citations_folder, 'citations.xlsx')

# Define output files
table_output = path(output_folder, 'AppendixS5_Project_Table.xlsx')
citations_output = path(output_folder, 'citations.txt')

# Define queries
project_file = path(database_repository, 'queries/01_project.sql')

#### QUERY AKVEG DATABASE
####____________________________________________________

# Import database connection function
connection_script = path(database_repository, 'pull_functions', 'connect_database_postgresql.R')
source(connection_script)

# Create a connection to the AKVEG PostgreSQL database
authentication = path(credentials_folder, 'authentication_akveg_private.csv')
database_connection = connect_database_postgresql(authentication)

# Read project data from AKVEG Database
project_query = read_file(project_file)
project_data = as_tibble(dbGetQuery(database_connection, project_query))

# Read organization data from AKVEG Database
organization_query = 'Select organization.organization as abbr
	 , database_dictionary.definition as organization
FROM organization
    LEFT JOIN database_dictionary ON organization.organization = database_dictionary.data_attribute'
organization_data = as_tibble(dbGetQuery(database_connection, organization_query))

#### COMPILE PROJECT CITATION TABLE
####____________________________________________________

# Format citations table
citation_data = read_xlsx(citations_input, sheet = 'citations') %>%
  mutate(citation_long = case_when(citation_url == 'NULL' ~ citation_long,
                                   citation_url != 'NULL' ~ paste(citation_long, ' Available: ', citation_url, sep = ''),
                                   TRUE ~ 'ERROR')) %>%
  distinct(project_code, citation_short, citation_long, citation_year) %>%
  arrange(project_code, citation_year, citation_short)

# Condense short citations
citation_condensed = citation_data %>%
  group_by(project_code) %>%
  summarise(citation_short = paste(citation_short, collapse = ', '))

# Format source table
source_data = read_xlsx(citations_input, sheet = 'citations') %>%
  mutate(data_source = case_when(source_url == 'NULL' ~ data_source,
                                   source_url != 'NULL' ~ paste(data_source, '. Available: ', source_url, sep = ''),
                                   TRUE ~ 'ERROR')) %>%
  distinct(project_code, data_source) %>%
  arrange(project_code)

# Compile project names
project_names = project_data %>%
  select(project_code, project_name)

#### COMPILE PROJECT METADATA TABLES
####____________________________________________________

# Summarize site visit number by project code
visit_data = read_xlsx(site_input, sheet = 'data') %>%
  group_by(project_code) %>%
  summarize(visit_n = n()) %>%
  mutate(project_code = case_when(project_code == 'nps_swan_2021' ~ 'nps_swan_2024',
                                  project_code == 'nrcs_soils_2022' ~ 'nrcs_soils_2024',
                                  TRUE ~ project_code))

# Create project citation table
project_citation = visit_data %>%
  left_join(project_data, by = 'project_code') %>%
  left_join(citation_condensed, by = 'project_code') %>%
  select(project_code, project_name, citation_short) %>%
  mutate(project_name = case_when(project_code == 'yukon_biophysical_2015' ~ 'Yukon Biophysical Inventory System Plots',
                                  project_code == 'yukon_landcover_2016' ~ 'Yukon Land Cover Observations',
                                  TRUE ~ project_name)) %>%
  rename(`Project Code` = project_code,
         `Project Name` = project_name,
         `Citation(s)` = citation_short)

# Create project metadata table
project_metadata = visit_data %>%
  left_join(project_data, by = 'project_code') %>%
  select(project_code, visit_n, originator, funder, year_end) %>%
  rename(`Project Code` = project_code,
         `Visits` = visit_n,
         `Origin.` = originator,
         `Funder` = funder,
         `Year End` = year_end)

# Create project source table
project_source = visit_data %>%
  left_join(source_data, by = 'project_code') %>%
  select(project_code, data_source) %>%
  rename(`Project Code` = project_code,
         `Data Source` = data_source)

# Create project organization table
project_funder = project_data %>%
  distinct(funder) %>%
  rename(abbr = funder)
project_organizations = project_data %>%
  distinct(originator) %>%
  rename(abbr = originator) %>%
  bind_rows(project_funder) %>%
  distinct(abbr) %>%
  left_join(organization_data, by = 'abbr') %>%
  arrange(abbr) %>%
  rename(`Abbr.` = abbr,
         `Organization Name` = organization)
  

# Compare site visit summaries
site_visit_selected = read_xlsx(site_input, sheet = 'summary') %>%
  filter(characteristic == 'site_visit_selected') %>%
  pull(value)
site_total = project_metadata %>%
  summarise(total = sum(`Visits`, na.rm = TRUE)) %>%
  pull(total)
if (site_visit_selected != site_total) {
  warning('Site visit totals do not match.')
}

#### EXPORT DATA
####____________________________________________________

# Export citations to text file
citation_data %>%
  distinct(citation_long) %>%
  arrange(citation_long) %>%
  pull(citation_long) %>%
  write_lines(citations_output)

# Export tables to excel
sheets = list(
  'citations' = project_citation,
  'metadata' = project_metadata,
  'source' = project_source,
  'organizations' = project_organizations
)
write_xlsx(sheets, path = table_output)
