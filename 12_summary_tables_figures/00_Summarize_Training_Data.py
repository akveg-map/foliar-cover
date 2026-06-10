# ---------------------------------------------------------------------------
# Summarize training data
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-06-03
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Summarize training data" calculates training data metrics across all diagnostic species sets.
# ---------------------------------------------------------------------------

# Import packages
import os
import pandas as pd

# Set version date
version_date = '20260415'

# Define diagnostic species sets
diagnostic_sets = ['abies', 'alnus', 'bderishr', 'beach', 'betshr', 'bettre', 'bromos', 'brotre',
                   'calnoo', 'dryas', 'dsalix', 'empnig', 'erivag', 'feather', 'forb', 'gramin',
                   'halgra', 'larlar', 'lichen', 'mwcalama', 'ndsalix', 'neetre', 'nerishr',
                   'picgla', 'picmar', 'picsit', 'pinus', 'poptre', 'populbt', 'rhoshr', 'rubspe',
                   'sphagn', 'tsuhet', 'tsumer', 'vaculi', 'vacvit', 'wetforb', 'wetgram', 'wetsed']

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
input_folder = os.path.join(project_folder, 'Data_Input/site_data', f'version_{version_date}')

# Define input files
site_visit_input = os.path.join(input_folder, 'akveg_site_visits_3338.csv')

#### SUMMARIZE TRAINING DATA
####____________________________________________________

# Read input data
site_visit_data = pd.read_csv(site_visit_input)

# Eliminate site visits that are excluded for all diagnostic species
site_visit_data = site_visit_data[site_visit_data['exclude'] != 1]
site_visit_data = site_visit_data[~(site_visit_data[diagnostic_sets] == -1).all(axis=1)]

# Define number of projects
project_count = site_visit_data['project_code'].nunique()

# Define number of site visits
absence_data = site_visit_data[site_visit_data['project_code'] == 'akveg_absences']
observation_data = site_visit_data[site_visit_data['project_code'] != 'akveg_absences']
site_visit_count = observation_data['site_visit_code'].nunique()
absence_count = absence_data['site_visit_code'].nunique()

# Print results
print(f'Site visit count: {site_visit_count}')
print(f'Absence count: {absence_count}')
print(f'Project count: {project_count}')
