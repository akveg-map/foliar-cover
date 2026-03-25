# ---------------------------------------------------------------------------
# Create data package
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-03-08
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Create data package" parses database export to files that can be included in a public data repository by removing all private data.
# ---------------------------------------------------------------------------

# Import libraries
import os
import pandas as pd

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
training_folder = os.path.join(project_folder,
                               'Documents/Manuscript_FoliarCover_FloristicGradients/tables')
ordination_folder = os.path.join(project_folder, 'Data/Data_Input/ordination_data')
archive_folder = os.path.join(project_folder, 'Data/Data_Input/database_archive')
metadata_folder = os.path.join(drive, root_folder, 'OneDrive - University of Alaska',
                               'ACCS_Teams/Vegetation/AKVEG_Database/Data/Tables_Metadata')
output_folder = os.path.join(project_folder,
                             'Documents/Manuscript_FoliarCover_FloristicGradients/data_package',
                             '00_data_input/database_archive')

# Define input files
schema_input = os.path.join(metadata_folder, 'database_schema.xlsx')
dictionary_input = os.path.join(metadata_folder, 'database_dictionary.xlsx')
taxonomy_input = os.path.join(archive_folder, 'version_20260212', '00_taxonomy.csv')
project_input = os.path.join(archive_folder, 'version_20260212', '01_project.csv')
training_site_input = os.path.join(training_folder, '00_Training_Data_Summary.xlsx')
ordination_site_input = os.path.join(ordination_folder, '03_site_visit.csv')
site_visit_input = os.path.join(archive_folder, 'version_20260212', '03_site_visit.csv')
vegetation_input = os.path.join(archive_folder, 'version_20260212', '05_vegetation_cover.csv')

# Define output file
schema_output = os.path.join(output_folder, '00_database_schema.csv')
dictionary_output = os.path.join(output_folder, '00_data_dictionary.csv')
taxonomy_output = os.path.join(output_folder, '00_taxonomy.csv')
project_output = os.path.join(output_folder, '01_project.csv')
site_visit_output = os.path.join(output_folder, '03_site_visit.csv')
vegetation_output = os.path.join(output_folder, '05_vegetation_cover.csv')

#### READ AND PREPARE INPUT DATA
####____________________________________________________

# Read input data
schema_data = pd.read_excel(schema_input, sheet_name='schema')
dictionary_data = pd.read_excel(dictionary_input, sheet_name='dictionary')
taxonomy_data = pd.read_csv(taxonomy_input)
project_data = pd.read_csv(project_input)
training_site_data = pd.read_excel(training_site_input, sheet_name='data')
ordination_site_data = pd.read_csv(ordination_site_input)
site_visit_data = pd.read_csv(site_visit_input)
vegetation_data = pd.read_csv(vegetation_input)

# Remove private projects
project_data = project_data[project_data['private']==False]

# Create list of unique projects
projects_public = project_data['project_code'].unique()

# Create list of unique sites from training and ordination data
initial_site_data = pd.concat([training_site_data[['site_visit_code']],
                               ordination_site_data[['site_visit_code']]],
                              axis=0)
initial_site_visits = initial_site_data['site_visit_code'].unique()

# Create subset of site visit data
site_visit_data = site_visit_data[site_visit_data['site_visit_code'].isin(initial_site_visits)]
site_visit_data = site_visit_data[site_visit_data['project_code'].isin(projects_public)]

# Create subset of projects
projects_included = site_visit_data['project_code'].unique()
project_data = project_data[project_data['project_code'].isin(projects_included)]

# Create subset of vegetation data
vegetation_data = vegetation_data[vegetation_data['site_visit_code'].isin(initial_site_visits)]

# Export data to output
schema_data.to_csv(schema_output, header=True, index=False, sep=',', encoding='utf-8')
dictionary_data.to_csv(dictionary_output, header=True, index=False, sep=',', encoding='utf-8')
taxonomy_data.to_csv(taxonomy_output, header=True, index=False, sep=',', encoding='utf-8')
project_data.to_csv(project_output, header=True, index=False, sep=',', encoding='utf-8')
site_visit_data.to_csv(site_visit_output, header=True, index=False, sep=',', encoding='utf-8')
vegetation_data.to_csv(vegetation_output, header=True, index=False, sep=',', encoding='utf-8')
