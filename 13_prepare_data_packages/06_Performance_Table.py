# ---------------------------------------------------------------------------
# Create data archive table
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-05-26
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Create data archive table" calculates a table of performance metrics at the site scale and landscape scale for all mapped diagnostic species sets for the data archive. Landscape scale data are transformed by assigning all site visits from the cross-validation results to a predefined 10 km grid, removing grids that contain less than 3 points, and calculating mean observed and predicted cover values.
# ---------------------------------------------------------------------------

# Import libraries
import os
import numpy as np
import pandas as pd
import geopandas as gpd
from sklearn.metrics import r2_score
from sklearn.metrics import mean_squared_error

# Set version date
version_date = '20260415'

# Define diagnostic species sets
diagnostic_sets = {'neetre': 'Needleleaf Trees',
                   'picgla': 'White Spruce',
                   'picmar': 'Black Spruce',
                   'picsit': 'Sitka Spruce',
                   'tsumer': 'Mountain Hemlock',
                   'tsuhet': 'Western Hemlock',
                   'abies': 'Fir Trees',
                   'calnoo': 'Alaska Yellow Cedar',
                   'pinus': 'Shore and Lodgepole Pine',
                   'larlar': 'Tamarack',
                   'brotre': 'Broadleaf Trees',
                   'bettre': 'Birch Trees',
                   'poptre': 'Aspen',
                   'populbt': 'Poplar and Cottonwood',
                   'alnus': 'Alder Shrubs',
                   'ndsalix': 'Willow Shrubs',
                   'betshr': 'Birch Shrubs',
                   'rubspe': 'Salmonberry',
                   'bderishr': 'Tall Blueberry Shrubs',
                   'vaculi': 'Low Blueberry Shrubs',
                   'rhoshr': 'Rhododendron Shrubs',
                   'nerishr': 'Needleleaf Ericaceous Shrubs',
                   'empnig': 'Crowberry',
                   'vacvit': 'Lingonberry',
                   'dryas': 'Dryas Dwarf Shrubs',
                   'dsalix': 'Willow Dwarf Shrubs',
                   'forb': 'Forbs',
                   'wetforb': 'Wetland Forbs',
                   'gramin': 'Graminoids',
                   'beach': 'Beach Herbaceous',
                   'halgra': 'Halophytic Graminoids',
                   'erivag': 'Tussock Cottongrass',
                   'mwcalama': 'Mesic-wet Calamagrostis',
                   'wetgram': 'Wetland Grasses and Rushes',
                   'wetsed': 'Wetland Sedges',
                   'feather': 'Feathermoss',
                   'sphagn': 'Sphagnum Moss',
                   'bromos': 'Brown Moss',
                   'lichen': 'Lichen'
                   }

# Define distribution list
distribution_list = ['abies', 'bromos', 'calnoo', 'larlar', 'pinus', 'wetgram']

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
repository_folder = os.path.join(drive, root_folder, 'Repositories/foliar-cover')
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
input_folder = os.path.join(project_folder, f'Data/Data_Output/model_results/version_{version_date}')
region_folder = os.path.join(project_folder, 'Data/Data_Input/region_data')
grid_folder = os.path.join(project_folder, 'Data/Data_Input/grid_data')
output_folder = os.path.join(project_folder, f'Data/Data_Output/data_package')

# Define input files
schema_input = os.path.join(repository_folder, 'AKVEG_Schema_FoliarCover.csv')
grid_input = os.path.join(grid_folder, 'AlaskaYukon_010_Tiles_3338.shp')

# Define output data
performance_output = os.path.join(output_folder, 'Results_Summary.csv')

# Define output variables
output_variables = ['abbreviation', 'diagnostic_set', 'lifeform', 'response',
                    'n_presence', 'cover_mean', '%_accuracy_site', 'auc_site',
                    'R2_site', 'RMSE_site', 'R2_scaled', 'RMSE_scaled',
                    'constituents']

#### CALCULATE MULTI-SCALE RESULTS
####____________________________________________________

# Read input schema file
schema_data = pd.read_csv(schema_input)[['target_abbr', 'lifeform', 'constituents']].rename(columns={
    'target_abbr': 'abbreviation'
})

# Read input grid and create grid_id
grid_data = gpd.read_file(grid_input)
grid_data['grid_id'] = range(1, len(grid_data) + 1)
grid_data = grid_data[['grid_id', 'geometry']]

# Initialize performance tracking list to store results data rows
performance_results = []

# Loop through each diagnostic species set
count = 1
for map_unit, diagnostic_set in diagnostic_sets.items():
    print(f'Processing data for diagnostic set {count} of {len(diagnostic_sets)}: {diagnostic_set}...')

    # Define input files
    set_folder = os.path.join(input_folder, map_unit)
    set_input = os.path.join(set_folder, f'{map_unit}_results.csv')
    acc_input = os.path.join(set_folder, f'{map_unit}_acc.txt')
    auc_input = os.path.join(set_folder, f'{map_unit}_auc.txt')
    r2_input = os.path.join(set_folder, f'{map_unit}_r2.txt')
    rmse_input = os.path.join(set_folder, f'{map_unit}_rmse.txt')

    # Summarize constituent list
    set_schema = schema_data[schema_data['abbreviation'] == map_unit]
    if not set_schema.empty and 'constituents' in set_schema.columns:
        diagnostic_taxa = "; ".join(set_schema['constituents'].dropna().astype(str).unique())
    else:
        diagnostic_taxa = ""

    # Read input data
    input_data = pd.read_csv(set_input)
    if not map_unit in distribution_list:
        input_data = input_data[['site_visit_code', 'cover_percent', 'prediction', 'longitude_dd', 'latitude_dd']]
    else:
        input_data = input_data[['site_visit_code', 'cover_percent', 'longitude_dd', 'latitude_dd']]

    # Calculate mean cover for presences at the site level
    site_presences = input_data[input_data['cover_percent'] >= 3]
    n_presence = len(site_presences)
    cover_mean = round(site_presences['cover_percent'].mean(), 0)

    # Read distribution performance metrics
    with open(acc_input, 'r') as text_read:
        acc_site = float(text_read.readline())
    with open(auc_input, 'r') as text_read:
        auc_site = float(text_read.readline())

    # Calculate multi-scale performance for cover models
    if not map_unit in distribution_list:
        # Read cover performance metrics
        with open(r2_input, 'r') as text_read:
            r2_site = float(text_read.readline())
        with open(rmse_input, 'r') as text_read:
            rmse_site = float(text_read.readline())

        # Define output files
        scaled_output = os.path.join(set_folder, f'{map_unit}_scaled.csv')

        # Convert to spatial dataframe
        input_data = gpd.GeoDataFrame(input_data,
                                      geometry=gpd.points_from_xy(input_data.longitude_dd,
                                                                  input_data.latitude_dd),
                                      crs='EPSG:4269')

        # Project to EPSG:3338
        input_data = input_data.to_crs('EPSG:3338')

        # Join 10 km grids
        input_data = gpd.sjoin(input_data, grid_data, how="left", predicate="within")
        if 'index_right' in input_data.columns:
            input_data = input_data.drop(columns=['index_right'])

        # Drop geometry for standard pandas aggregation
        input_data = pd.DataFrame(input_data.drop(columns='geometry'))

        # Summarize data by grid and remove grids with < 3 sites
        grid_summary = input_data.groupby('grid_id').agg(
            n_visits=('site_visit_code', 'size'),
            mean_cover_percent=('cover_percent', 'mean'),
            mean_prediction=('prediction', 'mean')
        ).reset_index()
        grid_summary = grid_summary[grid_summary['n_visits'] >= 3]

        # Export scaled data
        grid_summary.to_csv(scaled_output, header=True, index=False, sep=',', encoding='utf-8')

        # Calculate scaled performance from grid summary
        y_scaled_obs = grid_summary['mean_cover_percent'].astype(float)
        y_scaled_pred = grid_summary['mean_prediction'].astype(float)

        # Only calculate if data exists to avoid errors
        if not y_scaled_obs.empty:
            r2_scaled = r2_score(y_scaled_obs, y_scaled_pred, multioutput='uniform_average')
            rmse_scaled = np.sqrt(mean_squared_error(y_scaled_obs, y_scaled_pred))
        else:
            r2_scaled, rmse_scaled = np.nan, np.nan

        # Define response
        response = 'absolute foliar cover'

    # Default cover performance to np.nan for distribution maps
    else:
        r2_site = np.nan
        rmse_site = np.nan
        r2_scaled = np.nan
        rmse_scaled = np.nan
        response = 'probability of occurrence'

    # Create dictionary representing the row
    diagnostic_set_dict = {
        'abbreviation': map_unit,
        'diagnostic_set': diagnostic_set,
        'response': response,
        'n_presence': n_presence,
        'cover_mean': cover_mean,
        '%_accuracy_site': acc_site,
        'auc_site': auc_site,
        'R2_site': round(r2_site, 2) if pd.notna(r2_site) else np.nan,
        'RMSE_site': round(rmse_site, 1) if pd.notna(rmse_site) else np.nan,
        'R2_scaled': round(r2_scaled, 2) if pd.notna(r2_scaled) else np.nan,
        'RMSE_scaled': round(rmse_scaled, 1) if pd.notna(rmse_scaled) else np.nan,
        'constituents': diagnostic_taxa
    }

    performance_results.append(diagnostic_set_dict)

    count += 1
    print('----------')

#### EXPORT RESULTS
####____________________________________________________

# Join lifeform
print('Exporting final performance table to csv...')
performance_data = pd.DataFrame(performance_results)
lifeform_lookup = schema_data[['abbreviation', 'lifeform']].drop_duplicates()
lifeform_lookup['lifeform'] = lifeform_lookup['lifeform'].str.slice(start=3)
performance_data = pd.merge(performance_data,
                            lifeform_lookup,
                            on='abbreviation',
                            how='left')
performance_data = performance_data[output_variables]

# Export to csv
performance_data.to_csv(performance_output, header=True, index=False, sep=',', encoding='utf-8')
print('--- Script Finished ---')
