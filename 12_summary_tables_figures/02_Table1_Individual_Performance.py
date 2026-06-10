# ---------------------------------------------------------------------------
# Table 1. Individual Performance
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-05-26
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Table 1. Individual Performance" calculates a table of performance metrics at the site scale and landscape scale for all mapped diagnostic species sets for publication. Landscape scale data are transformed by assigning all site visits from the cross-validation results to a predefined 10 km grid, removing grids that contain less than 3 points, and calculating mean observed and predicted cover values.
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
                   'wetsed': 'Wetland Sedges',
                   'feather': 'Feathermoss',
                   'sphagn': 'Sphagnum Moss',
                   'lichen': 'Lichen'
                   }

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
input_folder = os.path.join(project_folder, f'Data/Data_Output/model_results/version_{version_date}')
region_folder = os.path.join(project_folder, 'Data/Data_Input/region_data')
grid_folder = os.path.join(project_folder, 'Data/Data_Input/grid_data')
output_folder = os.path.join(project_folder, f'Data/Data_Output/summary_results/version_{version_date}')

# Define input files
grid_input = os.path.join(grid_folder, 'AlaskaYukon_010_Tiles_3338.shp')

# Define output data
performance_output = os.path.join(output_folder, 'Table1_Individual_Performance.xlsx')

# Define output variables
output_variables = ['abbrev', 'diagnostic_name', 'n_presence', 'cover_mean',
                    'R2_site', 'RMSE_site', 'R2_scaled', 'RMSE_scaled',]

#### CALCULATE MULTI-SCALE RESULTS
####____________________________________________________

# Read input grid and create grid_id
grid_data = gpd.read_file(grid_input)
grid_data['grid_id'] = range(1, len(grid_data) + 1)
grid_data = grid_data[['grid_id', 'geometry']]

# Initialize performance tracking list to store results data rows
performance_results = []

# Loop through each diagnostic species set
count = 1
for diagnostic_set, diagnostic_name in diagnostic_sets.items():
    print(f'Processing data for diagnostic_set {count} of {len(diagnostic_sets)}: {diagnostic_name}...')

    # Define input files for diagnostic_set
    set_folder = os.path.join(input_folder, diagnostic_set)
    set_input = os.path.join(set_folder, f'{diagnostic_set}_results.csv')
    r2_input = os.path.join(set_folder, f'{diagnostic_set}_r2.txt')
    rmse_input = os.path.join(set_folder, f'{diagnostic_set}_rmse.txt')

    # Define output files for diagnostic_set
    scaled_output = os.path.join(set_folder, f'{diagnostic_set}_scaled.csv')

    # Read input data
    input_data = pd.read_csv(set_input)
    input_data = input_data[['site_visit_code', 'cover_percent', 'prediction', 'longitude_dd', 'latitude_dd']]

    # Convert to spatial dataframe
    input_data = gpd.GeoDataFrame(
        input_data,
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

    # Read text performance metrics
    with open(r2_input, 'r') as text_read:
        r2_site = float(text_read.readline())
    with open(rmse_input, 'r') as text_read:
        rmse_site = float(text_read.readline())

    # Calculate mean and median cover for presences at the site level
    site_presences = input_data[input_data['cover_percent'] >= 3]
    n_presence = len(site_presences)
    cover_mean = round(site_presences['cover_percent'].mean(), 0)

    # Calculate scaled performance from grid summary
    y_scaled_obs = grid_summary['mean_cover_percent'].astype(float)
    y_scaled_pred = grid_summary['mean_prediction'].astype(float)

    # Only calculate if data exists to avoid errors
    if not y_scaled_obs.empty:
        r2_scaled = r2_score(y_scaled_obs, y_scaled_pred, multioutput='uniform_average')
        rmse_scaled = np.sqrt(mean_squared_error(y_scaled_obs, y_scaled_pred))
    else:
        r2_scaled, rmse_scaled = np.nan, np.nan

    # Create dictionary representing the row
    diagnostic_set_dict = {
        'abbrev': diagnostic_set,
        'diagnostic_name': diagnostic_name,
        'n_presence': n_presence,
        'cover_mean': cover_mean,
        'R2_site': round(r2_site, 2) if pd.notna(r2_site) else np.nan,
        'RMSE_site': round(rmse_site, 1) if pd.notna(rmse_site) else np.nan,
        'R2_scaled': round(r2_scaled, 2) if pd.notna(r2_scaled) else np.nan,
        'RMSE_scaled': round(rmse_scaled, 1) if pd.notna(rmse_scaled) else np.nan
    }

    performance_results.append(diagnostic_set_dict)

    count += 1
    print('----------')

#### EXPORT RESULTS
####____________________________________________________

# Convert list of dicts to DataFrame
print('Exporting final performance table to csv...')
performance_data = pd.DataFrame(performance_results, columns=output_variables).rename(columns={
    'diagnostic_name': 'Diagnostic Species Set',
    'n_presence': 'Pres.',
    'cover_mean': 'Mean Cover %'
})

# Export to csv
performance_data.to_excel(performance_output, index=False)
print('--- Script Finished ---')
