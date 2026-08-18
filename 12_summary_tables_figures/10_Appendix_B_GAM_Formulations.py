# ---------------------------------------------------------------------------
# Prepare Appendix B GAM formulations
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-08-11
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Prepare Appendix B GAM formulations" compiles the exact formulations from the Generalized Additive Models for the foliar cover map combined performance assessments across all subregions into a single excel table. This table is formatted to be published as a manuscript appendix.
# ---------------------------------------------------------------------------

# Import packages
import os
import pandas as pd

# Set version date
version_date = '20260415'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
input_folder = os.path.join(project_folder, f'Data_Output/ordination_results/version_{version_date}')
output_folder = os.path.join(project_folder, f'Data_Output/summary_results/version_{version_date}')

# Define output file path
output_file = os.path.join(output_folder, f'Appendix_B_GAM_Formulations.xlsx')

# Define subregion dictionary
subregion_dictionary = {
    ('Arctic Coastal Plain', 'all'): 1,
    ('Arctic Foothills & Mountains', 'all'): 2,
    ('Seward Peninsula', 'all'): 3,
    ('Bering Sea Islands', 'all'): 4,
    ('Alaska Peninsula', 'all'): 5,
    ('Kodiak Southwest', 'all'): 6,
    ('Southwest Mountains', 'all'): 7,
    ('Bristol Bay', 'forest'): 8,
    ('Bristol Bay', 'non-forest'): 9,
    ('Alaska Western', 'forest'): 10,
    ('Alaska Western', 'non-forest'): 11,
    ('Alaska-Yukon Northwest', 'all'): 12,
    ('Yukon Flats', 'forest'): 13,
    ('Yukon Flats', 'non-forest'): 14,
    ('Eastern Interior', 'forest'): 15,
    ('Eastern Interior', 'non-forest'): 16,
    ('Central Interior', 'all'): 17,
    ('Denali North', 'forest'): 18,
    ('Denali North', 'non-forest'): 19,
    ('Wrangell-Copper', 'forest'): 20,
    ('Wrangell-Copper', 'non-forest'): 21,
    ('Nelchina Uplands', 'all'): 22,
    ('Denali South', 'forest'): 23,
    ('Denali South', 'non-forest'): 24,
    ('Cook Inlet', 'all'): 25,
    ('Kodiak Northeast', 'forest'): 26,
    ('Kodiak Northeast', 'non-forest'): 27,
    ('Pacific Mainland', 'forest'): 28,
    ('Pacific Mainland', 'non-forest'): 29
}

#### Create list of model formulations
####____________________________________________________

# Create list to store data
input_list = []

# Read all input files that correspond to the subregion dictionary
for key, value in subregion_dictionary.items():
    # Define input file
    input_file = os.path.join(input_folder, f'{value:02d}_performance.xlsx')

    # Read input data
    input_data = pd.read_excel(input_file, sheet_name='equation')

    # Add subregion data
    input_data['subregion_id'] = value
    input_data['subregion'] = key[0]
    input_data['focal_unit'] = key[1]

    # Append data frame to list
    input_list.append(input_data)

# Merge data frames
output_data = pd.concat(input_list, ignore_index=True)

# Format table
output_data = output_data.rename(columns = {'gam_equation': 'gam_formulation'})
output_data = output_data[['subregion_id', 'subregion', 'focal_unit', 'gam_formulation']]

# Define the header text
# Define the header text
header_1 = 'Supporting Information for “Scaling ecological complexity in large extent vegetation maps: unifying continuous spatial models with categorical classification” in Ecological Informatics by Timm W. Nawrocki, Matthew J. Macander, Aaron F. Wells, Amanda Droghini, Gerald V. Frost, Lindsey A. Flagstad, Matthew L. Carlson, Hunter A. Gravley, Michael Hannam, Amy E. Miller, Carl Roland, Calvin B. Heslop, Kathryn C. Baer, Tina V. Boucher, Blaine T. Spellman, Marji Patz, Lisa B. Saperstein, Denise Gordon, Caitlin Willier, and Elizabeth M. Powers.'
header_2 = 'Appendix B: Generalized Additive Model Formulations for Diagnostic Species Sets'
header_3 = 'This appendix provides the formulations of the Generalized Additive Models (GAMs) for the combined performance assessment of the diagnostic species sets. Smoothed terms are indicated by "s()" while linear terms appear unmodified in the formula. We used Thin Plate Regression Splines to smooth the terms as implemented in the mgcv package in R (see Appendix A for citation). See Appendix A for a description of our rule-based approach to determine which diagnostic species sets were included in each model, which were smoothed, and which were linear. Appendix A also provides an explanation for the GAM formulations of the tested categorical maps, the Landfire 2023 Existing Vegetation Types and the Alaska Vegetation and Wetland Composite (fine classes). Table A.1. in Appendix A defines the diagnostic species set abbreviations used as covariate names in the model formulations.'

# Export data frame to excel with custom headers
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # Write the dataframe starting at row 5 (index 4) to leave room for the headers and an empty row
    output_data.to_excel(writer, sheet_name='formulations', index=False, startrow=4)

    # Access the openpyxl worksheet object
    worksheet = writer.sheets['formulations']

    # Write the custom text to the first three rows (openpyxl uses 1-based indexing)
    worksheet.cell(row=1, column=1, value=header_1)
    worksheet.cell(row=2, column=1, value=header_2)
    worksheet.cell(row=3, column=1, value=header_3)
