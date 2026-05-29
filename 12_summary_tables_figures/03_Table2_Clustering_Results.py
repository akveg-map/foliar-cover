# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Compile results
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-05-28
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Compile results" creates a summary table of the ordination and clustering results from all subregions.
# ---------------------------------------------------------------------------

# Import packages
import os
import numpy as np
import pandas as pd

# Set version date
version_date = '20260415'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define input folders
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
ordination_folder = os.path.join(project_folder, f'Data_Input/ordination_data/version_{version_date}')
results_folder = os.path.join(project_folder, f'Data_Output/ordination_results/version_{version_date}')
output_folder = os.path.join(project_folder, f'Data_Output/summary_results/version_{version_date}')

# Define input files
site_visit_input = os.path.join(ordination_folder, 'site_visit_data.csv')

# Define output files
performance_output = os.path.join(output_folder, 'Table2_Clustering_Performance.xlsx')

#### PROCESS SUBREGION SUMMARY
####____________________________________________________

# Read site visit data
site_visit_data = pd.read_csv(site_visit_input)
site_visit_data = site_visit_data[site_visit_data['group_id'] != -999].copy()

# Summarize the year range from observation dates per subregion unit
site_visit_data['year'] = pd.to_datetime(site_visit_data['observe_date']).dt.year
year_summary = site_visit_data.groupby('group_id')['year'].agg(['min', 'max']).dropna()
year_summary['obs_years'] = year_summary['min'].astype(int).astype(str) + '-' + year_summary['max'].astype(int).astype(str)

# Create subregion lookup table
subregion_lookup = site_visit_data[['group_id', 'subregion', 'focal_unit']].drop_duplicates()
subregion_lookup['focal_unit'] = subregion_lookup['focal_unit'].str.title()
subregion_lookup['unit_name'] = subregion_lookup['subregion']
subregion_lookup['unit_name'] = np.where(subregion_lookup['focal_unit'] != 'all',
                                         subregion_lookup['subregion'] + ' ' + subregion_lookup['focal_unit'],
                                         subregion_lookup['unit_name'])
subregion_lookup = subregion_lookup[['group_id', 'unit_name']].drop_duplicates()

# Merge year range into subregion lookup table
subregion_lookup = subregion_lookup.merge(year_summary[['obs_years']], on='group_id', how='left')

# Identify group number max
group_number = int(subregion_lookup['group_id'].max())

# Prepare empty lists to store data rows
performance_rows = []
equation_rows = []

# Summarize data for each subregion
for count in range(1, group_number + 1):
    # Define input files
    performance_input = os.path.join(results_folder, f'{count:02}_Performance.xlsx')

    # Read input data
    performance_row = pd.read_excel(performance_input, sheet_name='summary')
    equation_row = pd.read_excel(performance_input, sheet_name='equation')

    # Add group_id column to equation
    equation_row['group_id'] = count

    # Append the dataframes to our lists
    performance_rows.append(performance_row)
    equation_rows.append(equation_row)

# Concatenate all rows into single dataframes
performance_data = pd.concat(performance_rows, ignore_index=True)
equation_data = pd.concat(equation_rows, ignore_index=True)

# Add unit names to tables
performance_data = subregion_lookup.merge(performance_data, on='group_id', how='left')
equation_data = subregion_lookup.merge(equation_data, on='group_id', how='left')

# Filter subset of columns in performance data
performance_data = performance_data[['group_id', 'unit_name', 'obs_years', 'selected_n', 'nmds_stress', 'cluster_n',
    'mean_var', 'mean_sil', 'gam_clust', 'gam_ind', 'gam_akvwc', 'gam_lf',
    'scaled_ind', 'scaled_akvwc', 'scaled_lf']]

# Rename columns for final table
table_data = performance_data.rename(columns={'unit_name': 'Benchmark Dataset',
                                              'obs_years ': 'Observation Years',
                                              'selected_n': 'Count',
                                              'nmds_stress': 'NMDS Stress',
                                              'cluster_n': 'Clust.',
                                              'mean_var': 'Var.',
                                              'mean_sil': 'Sil.',
                                              'gam_clust': '% Dev.'})

# Prepare combined performance table
performance_data = performance_data[['group_id', 'unit_name', 'gam_clust', 'gam_ind', 'gam_akvwc', 'gam_lf',
                                     'scaled_ind', 'scaled_akvwc', 'scaled_lf']]

# Sort by group id
table_data = table_data.sort_values(by='group_id')
performance_data = performance_data.sort_values(by='group_id')
equation_data = equation_data.sort_values(by='group_id')

# Export data to xlsx using ExcelWriter to handle multiple sheets
with pd.ExcelWriter(performance_output, engine='openpyxl') as writer:
    table_data.to_excel(writer, sheet_name='Table2', index=False)
    performance_data.to_excel(writer, sheet_name='Performance', index=False)
    equation_data.to_excel(writer, sheet_name='Equations', index=False)
