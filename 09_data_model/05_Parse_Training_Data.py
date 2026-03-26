# ---------------------------------------------------------------------------
# Parse training data
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-03-26
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Parse training data" parses train-validate-test data for all diagnostic species sets.
# ---------------------------------------------------------------------------

# Import libraries
import os
import numpy as np
import pandas as pd

# Set version date
version_date = '20260326'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
repository_folder = os.path.join(drive, root_folder, 'Repositories/foliar-cover')
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
input_folder = os.path.join(project_folder, 'Data/Data_Input/database_archive', f'version_{version_date}')
output_folder = os.path.join(project_folder, 'Data/Data_Input/site_data', f'version_{version_date}')

# Define input files
schema_input = os.path.join(repository_folder, 'AKVEG_Schema_FoliarCover.csv')
taxonomy_input = os.path.join(input_folder, '00_taxonomy.csv')
project_input = os.path.join(input_folder, '01_project.csv')
site_visit_input = os.path.join(input_folder, '03_site_visit.csv')
vegetation_input = os.path.join(input_folder, '05_vegetation_cover.csv')

# Define output file
site_visit_output = os.path.join(output_folder, 'akveg_site_visits_3338.csv')

#### READ AND PREPARE INPUT DATA
####____________________________________________________

# Read input data
schema_data = pd.read_csv(schema_input)
taxonomy_data = pd.read_csv(taxonomy_input)
project_data = pd.read_csv(project_input)
site_visit_data = pd.read_csv(site_visit_input)
vegetation_data = pd.read_csv(vegetation_input)

# Remove dead vegetation
vegetation_data = vegetation_data[vegetation_data['dead_status'] == False]

# Join taxon habit to vegetation cover
taxon_habit = taxonomy_data[['taxon_name', 'taxon_habit']]
vegetation_data = pd.merge(left=vegetation_data,
                           right=taxon_habit,
                           left_on='name_accepted',
                           right_on='taxon_name',
                           how='left').drop(columns=['taxon_name'])

# Add private boolean field to site_visit_data
project_data = project_data[['project_code', 'private']]
site_visit_data = pd.merge(left=site_visit_data,
                           right=project_data,
                           on='project_code',
                           how='left')
site_visit_data['private'] = site_visit_data['private'].fillna('False')

# Create new column to record exclusions
site_visit_data['exclude'] = 0

# Exclude site visits sampled before 2000
site_visit_data['exclude'] = np.where(site_visit_data['observe_year'] < 2000,
                                      1, site_visit_data['exclude'])

# Exclude site visits made before burn or within 10 years post-burn
site_visit_data['exclude'] = np.where(site_visit_data['observe_year'] <= (site_visit_data['fire_year'] + 10),
                                      1, site_visit_data['exclude'])

# Exclude site visits where the centroid overlaps persistent water
site_visit_data['exclude'] = np.where((site_visit_data['esa_type'] == 80)
                                      & (site_visit_data['project_code'] != 'akveg_absences'),
                                      1, site_visit_data['exclude'])

# Exclude site visits in Kenai Fjords that extend beyond the coastline
site_visit_data['exclude'] = np.where((site_visit_data['project_code'] == 'nps_kenai_2004')
                                      & (site_visit_data['coast'] < 50),
                                      1, site_visit_data['exclude'])

# Exclude site visits where the plot radius is below 4 m
site_visit_data['exclude'] = np.where(site_visit_data['plot_radius_m'] < 4,
                                      1, site_visit_data['exclude'])

# Exclude earlier revisits to the most recent site visit
revisit_data = site_visit_data.copy()
site_counts = revisit_data['site_code'].value_counts()
revisit_data['total_visits'] = revisit_data['site_code'].map(site_counts)
revisit_data['observe_datetime'] = pd.to_datetime(revisit_data['observe_date'], format='%Y-%m-%d')
revisit_data = revisit_data.sort_values(by='observe_datetime')
revisit_data = revisit_data.drop_duplicates(subset=['site_code'], keep='last')
revisit_data = revisit_data.drop(columns=['observe_datetime', 'total_visits']).copy()
site_visit_data['exclude'] = np.where(
    site_visit_data['site_visit_code'].isin(revisit_data['site_visit_code'].unique()),
    site_visit_data['exclude'], 1)

# Split observed absences from observed presences
explicit_absences = vegetation_data[vegetation_data['cover_percent'] == -999].copy()
explicit_absences['cover_percent'] = 0
vegetation_data = vegetation_data[vegetation_data['cover_percent'] >= 0].copy()


#### IDENTIFY EXCLUSION SITES
####____________________________________________________

# Define a function to list site visit codes for exclusion
def exclusion_sites(vegetation_data, exclude_taxon):
    # Filter site visits from vegetation data to the excluded taxon
    filtered_data = vegetation_data[
        (vegetation_data['name_accepted'] == exclude_taxon)
        & ((vegetation_data['cover_percent'] >= 5) | (vegetation_data['cover_percent'] == -999))]
    exclude_site_visits = filtered_data['site_visit_code'].unique()
    return exclude_site_visits


# Exclude sites with tree observations
exclude_brotre = exclusion_sites(vegetation_data, 'tree broadleaf')
exclude_nedtre = exclusion_sites(vegetation_data, 'tree needleleaf')
exclude_betula = exclusion_sites(vegetation_data, 'Betula')
exclude_picea = exclusion_sites(vegetation_data, 'Picea')
exclude_populus = exclusion_sites(vegetation_data, 'Populus')
exclude_tsuga = exclusion_sites(vegetation_data, 'Tsuga')

# Exclude sites with shrub observations
exclude_dwashr = exclusion_sites(vegetation_data, 'shrub dwarf')
exclude_shrub = exclusion_sites(vegetation_data, 'shrub')
exclude_decshr = exclusion_sites(vegetation_data, 'shrub deciduous')
exclude_evrshr = exclusion_sites(vegetation_data, 'shrub evergreen')
exclude_rubus = exclusion_sites(vegetation_data, 'Rubus')
exclude_salix = exclusion_sites(vegetation_data, 'Salix')
exclude_vaccinium = exclusion_sites(vegetation_data, 'Vaccinium')

# Exclude sites with herbaceous observations
exclude_forb = exclusion_sites(vegetation_data, 'forb')
exclude_gramin = exclusion_sites(vegetation_data, 'graminoid')
exclude_grass = exclusion_sites(vegetation_data, 'grass (Poaceae)')
exclude_herb = exclusion_sites(vegetation_data, 'herbaceous')
exclude_calama = exclusion_sites(vegetation_data, 'Calamagrostis')
exclude_carex = exclusion_sites(vegetation_data, 'Carex')
exclude_erioph = exclusion_sites(vegetation_data, 'Eriophorum')
exclude_festuca = exclusion_sites(vegetation_data, 'Festuca')
exclude_sedge = exclusion_sites(vegetation_data, 'sedge (Cyperaceae)')
exclude_leymus = exclusion_sites(vegetation_data, 'Leymus')

# Exclude sites with nonvascular observations
exclude_bryoph = exclusion_sites(vegetation_data, 'bryophyte')
exclude_moss = exclusion_sites(vegetation_data, 'moss')

# Exclude specific observations
exclude_picgla = ['WRST_T31_07_20040721', 'KENA20170425_20170725', 'KENA20170377_20170725',
                  'KENA20170891_20170817', 'KENA20171155_20170901', 'KENA20171335_20170722',
                  'KENA20170916_20170712', 'KENA20170902_20170731', 'KENA20171144_20170804',
                  'KENA20171016_20170810', 'KENA20170896_20170901', 'KENA20171116_20170817',
                  'KENA20171112_20170817', 'KENA20171131_20170721', 'KENA20171130_20170721',
                  'KENA20171105_20170721', 'KENA20171277_20170721', 'KENA20170257_20170731',
                  'KENA20170241_20170731', 'KENA20171266_20170730', 'KENA20171265_20170730',
                  'KENA20170172_20170731', 'KENA20170132_20170731', 'KENA20171232_20170731',
                  'KENA20171229_20170731', 'KENA20171254_20170730', 'HAIN20000064_20000710',
                  'HAIN20000058_20000711', 'HAIN20000036_20000709', 'HAIN20000038_20000709',
                  'HAIN20000029_20000708', 'HAIN20000018_20000708', 'HAIN20000016_20000708',
                  'HAIN20000037_20000710', 'HAIN20000030_20000710', 'HAIN20000026_20000710',
                  'HAIN20000026_20000710', 'HAIN20000009_20000710', 'HAIN20000010_20000710',
                  'HAIN20000006_20000710', 'HAIN20000092_20000710', '12TD06901_20120923']

#### PARSE TRAINING DATA
####____________________________________________________

# Define lifeform list for taxonomic scopes
vascular_list = ['1. needleleaf tree', '2. broadleaf tree', '3. shrub',
                 '4. dwarf shrub', '5. graminoid', '6. forb']
bryophyte_list = ['7. bryophytes']
lichen_list = ['8. lichen']


# Define a function to parse training data
def parse_training_data(target,
                        schema_data=schema_data,
                        vegetation_data=vegetation_data,
                        site_visit_data=site_visit_data,
                        explicit_absences=explicit_absences,
                        exclusion_list=[]):
    # Retrieve parameters from schema
    parameter_data = schema_data[schema_data['target_abbr'] == target]
    constituents_list = parameter_data['constituents'].unique()
    lifeform = parameter_data['lifeform'].unique()[0]
    target_name = parameter_data['target'].unique()[0]

    # Compile data for target
    if parameter_data['type'].unique()[0] == 'functional group':
        target_data = vegetation_data[vegetation_data['taxon_habit'].isin(constituents_list)].copy()
    elif parameter_data['type'].unique()[0] == 'diagnostic species set':
        target_data = vegetation_data[vegetation_data['name_accepted'].isin(constituents_list)].copy()
    else:
        quit()

    # Update names and columns
    target_data['name_accepted'] = target_name
    target_data['code_accepted'] = target
    target_data = target_data.drop(columns=['taxon_habit'])

    # Identify site visits with target data presences
    target_site_visits = target_data['site_visit_code'].unique()

    # Identify set of potential absence points
    potential_absences = site_visit_data[~site_visit_data['site_visit_code'].isin(target_site_visits)]

    # Identify lifeform scope
    if lifeform in vascular_list:
        lifeform_scope = 'scope_vascular'
    elif lifeform in bryophyte_list:
        lifeform_scope = 'scope_bryophyte'
    elif lifeform in lichen_list:
        lifeform_scope = 'scope_lichen'
    else:
        quit()

    # Identify base absences
    if lifeform in vascular_list:
        absence_data = potential_absences[potential_absences[lifeform_scope].isin(
            ['exhaustive', 'non-trace species', 'absence']
        )]
    else:
        absence_data = potential_absences[potential_absences[lifeform_scope].isin(
            ['exhaustive', 'non-trace species', 'common species', 'absence']
        )]

    # If top absences is true, identify top absences
    if parameter_data['top_absence'].unique()[0] == True:
        absence_top = potential_absences[potential_absences[lifeform_scope] == 'top canopy']
        absence_data = pd.concat([absence_data, absence_top], axis=0)

    # Add additional generated absences for bettre and picea
    if target == 'bettre':
        absence_generated = potential_absences[potential_absences[lifeform_scope] == 'bettre']
        absence_data = pd.concat([absence_data, absence_generated], axis=0)
    if target in ['picgla', 'picmar']:
        absence_generated = potential_absences[potential_absences[lifeform_scope] == 'picea']
        absence_data = pd.concat([absence_data, absence_generated], axis=0)

    # Format absence data to match target data fields
    absence_site_visits = absence_data['site_visit_code'].unique()
    absence_data = pd.DataFrame({'site_visit_code': absence_site_visits,
                                 'code_accepted': target,
                                 'name_accepted': target_name,
                                 'dead_status': False,
                                 'cover_type': 'absolute foliar cover',
                                 'cover_percent': 0})

    # Identify explicit absences
    absence_explicit = explicit_absences[explicit_absences['name_accepted'].isin(constituents_list)]
    absence_explicit = absence_explicit[~absence_explicit['site_visit_code'].isin(target_site_visits)]

    # Merge explicit absences with inferred absences
    if len(absence_explicit) > 0:
        absence_explicit['name_accepted'] = target_name
        absence_explicit['code_accepted'] = target
        absence_explicit = absence_explicit.drop(columns=['taxon_habit'])
        absence_data = pd.concat([absence_data, absence_explicit], axis=0)

    # Combine presence and absence data
    training_data = pd.concat([target_data, absence_data], axis=0)
    training_data = (training_data.groupby(['site_visit_code', 'name_accepted'])['cover_percent']
                     .sum()
                     .to_frame()
                     .reset_index())
    training_data['code_accepted'] = target

    # Exclude site visits from exclusion list
    if len(exclusion_list) > 0:
        for exclusion_sites in exclusion_list:
            training_data = training_data[~training_data['site_visit_code'].isin(exclusion_sites)]

    # Prepare data to append
    training_data['cover_percent'] = np.where(training_data['cover_percent'] >= 100,
                                              100, training_data['cover_percent'])
    training_data = (training_data[['site_visit_code', 'cover_percent']]
                     .rename(columns={'cover_percent': target})
                     .copy())

    # Append training data to site visit data
    site_visit_data = pd.merge(left=site_visit_data,
                               right=training_data,
                               on='site_visit_code',
                               how='left')
    site_visit_data[target] = site_visit_data[target].fillna(-1)
    site_visit_data[target] = np.where(site_visit_data['exclude'] == 1, -1, site_visit_data[target])

    return site_visit_data[target]


# Parse needleleaf tree training data
site_visit_data['neetre'] = parse_training_data(target='neetre')
site_visit_data['picgla'] = parse_training_data(target='picgla',
                                                exclusion_list=[exclude_nedtre,
                                                                exclude_picea,
                                                                exclude_picgla])
site_visit_data['picmar'] = parse_training_data(target='picmar',
                                                exclusion_list=[exclude_nedtre,
                                                                exclude_picea])
site_visit_data['picsit'] = parse_training_data(target='picsit',
                                                exclusion_list=[exclude_nedtre,
                                                                exclude_picea,
                                                                exclude_picgla])
site_visit_data['tsuhet'] = parse_training_data(target='tsuhet',
                                                exclusion_list=[exclude_nedtre,
                                                                exclude_tsuga])
site_visit_data['tsumer'] = parse_training_data(target='tsumer',
                                                exclusion_list=[exclude_nedtre,
                                                                exclude_tsuga])

# Parse broadleaf tree training data
site_visit_data['brotre'] = parse_training_data(target='brotre')
site_visit_data['bettre'] = parse_training_data(target='bettre',
                                                exclusion_list=[exclude_brotre,
                                                                exclude_betula])
site_visit_data['poptre'] = parse_training_data(target='poptre',
                                                exclusion_list=[exclude_brotre,
                                                                exclude_populus])
site_visit_data['populbt'] = parse_training_data(target='populbt',
                                                 exclusion_list=[exclude_brotre,
                                                                 exclude_populus])

# Parse shrub training data
site_visit_data['alnus'] = parse_training_data(target='alnus',
                                               exclusion_list=[exclude_shrub,
                                                               exclude_decshr])
site_visit_data['bderishr'] = parse_training_data(target='bderishr',
                                                  exclusion_list=[exclude_shrub,
                                                                  exclude_decshr,
                                                                  exclude_vaccinium])
site_visit_data['betshr'] = parse_training_data(target='betshr',
                                                exclusion_list=[exclude_shrub,
                                                                exclude_decshr,
                                                                exclude_betula])
site_visit_data['ndsalix'] = parse_training_data(target='ndsalix',
                                                 exclusion_list=[exclude_shrub,
                                                                 exclude_decshr])
site_visit_data['rhoshr'] = parse_training_data(target='rhoshr',
                                                exclusion_list=[exclude_shrub,
                                                                exclude_evrshr])
site_visit_data['rubspe'] = parse_training_data(target='rubspe',
                                                exclusion_list=[exclude_shrub,
                                                                exclude_decshr,
                                                                exclude_rubus])
site_visit_data['vaculi'] = parse_training_data(target='vaculi',
                                                exclusion_list=[exclude_shrub,
                                                                exclude_decshr,
                                                                exclude_vaccinium])

# Parse dwarf shrub training data
site_visit_data['dryas'] = parse_training_data(target='dryas',
                                               exclusion_list=[exclude_dwashr])
site_visit_data['dsalix'] = parse_training_data(target='dsalix',
                                                exclusion_list=[exclude_dwashr,
                                                                exclude_decshr,
                                                                exclude_salix])
site_visit_data['empnig'] = parse_training_data(target='empnig',
                                                exclusion_list=[exclude_dwashr,
                                                                exclude_evrshr])
site_visit_data['nerishr'] = parse_training_data(target='nerishr',
                                                 exclusion_list=[exclude_dwashr,
                                                                 exclude_evrshr])
site_visit_data['vacvit'] = parse_training_data(target='vacvit',
                                                exclusion_list=[exclude_dwashr,
                                                                exclude_evrshr,
                                                                exclude_vaccinium])

# Parse graminoid training data
site_visit_data['erivag'] = parse_training_data(target='erivag',
                                                exclusion_list=[exclude_gramin,
                                                                exclude_erioph])
site_visit_data['gramin'] = parse_training_data(target='gramin')
site_visit_data['halgra'] = parse_training_data(target='halgra',
                                                exclusion_list=[exclude_gramin,
                                                                exclude_grass,
                                                                exclude_carex])
site_visit_data['mwcalama'] = parse_training_data(target='mwcalama',
                                                  exclusion_list=[exclude_gramin,
                                                                  exclude_grass,
                                                                  exclude_calama])
site_visit_data['wetsed'] = parse_training_data(target='wetsed',
                                                exclusion_list=[exclude_gramin,
                                                                exclude_erioph,
                                                                exclude_carex])
site_visit_data['wetgram'] = parse_training_data(target='wetgram',
                                                 exclusion_list=[exclude_gramin])

# Parse forb training data
site_visit_data['forb'] = parse_training_data(target='forb')
site_visit_data['wetforb'] = parse_training_data(target='wetforb',
                                                 exclusion_list=[exclude_forb])
site_visit_data['beach'] = parse_training_data(target='beach')

# Parse bryophyte training data
site_visit_data['bromos'] = parse_training_data(target='bromos', exclusion_list=[exclude_moss])
site_visit_data['feather'] = parse_training_data(target='feather', exclusion_list=[exclude_moss])
site_visit_data['sphagn'] = parse_training_data(target='sphagn', exclusion_list=[exclude_moss])

# Parse lichen training data
site_visit_data['lichen'] = parse_training_data(target='lichen')

#### EXPORT DATA TO SINGLE TABLE
####____________________________________________________

site_visit_data.to_csv(site_visit_output, header=True, index=False, sep=',', encoding='utf-8')
