# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Calculate performance table
# Author: Timm Nawrocki
# Last Updated: 2025-07-24
# Usage: Must be executed in an Anaconda Python 3.7+ installation.
# Description: "Calculate performance table" calculates a table of performance metrics at the site scale and landscape scale for all mapped indicators. Landscape scale data are transformed by assigning all site visits from the cross-validation results to a predefined 10 km grid, removing grids that contain less than 3 points, and calculating mean observed and predicted cover values.
# ---------------------------------------------------------------------------

# Import packages
import os
import numpy as np
import pandas as pd
import geopandas as gpd
from sklearn.metrics import r2_score
from sklearn.metrics import mean_squared_error

# Set version date
version_date = '20241124'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define file structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
input_folder = os.path.join(project_folder,
                            f'Data/Data_Output/model_results/version_{version_date}')
region_folder = os.path.join(project_folder, 'Data/Data_Input/region_data')
grid_folder = os.path.join(project_folder, 'Data/Data_Input/grid_data')

# Define input data
region_input = os.path.join(region_folder, 'AlaskaYukon_Regions_v2.0_3338.shp')
grid_input = os.path.join(grid_folder, 'AlaskaYukon_010_Tiles_3338.shp')

# Define output data
performance_output = os.path.join(input_folder, 'performance_table.csv')

# Define pre-determined field values
indicators = ['alnus', 'betshr', 'bettre', 'brotre', 'dryas', 'dsalix', 'empnig', 'erivag', 'mwcalama',
              'ndsalix', 'nerishr', 'picgla', 'picmar', 'picsit', 'poptre', 'populbt', 'rhoshr', 'rubspe',
              'sphagn', 'tsumer', 'vaculi', 'vacvit', 'wetsed']
names = ['alder shrubs',
         'birch shrubs',
         'birch trees',
         'broadleaf trees',
         'Dryas dwarf shrubs',
         'willow dwarf shrubs',
         'Empetrum nigrum',
         'Eriophorum vaginatum',
         'mesic-wet Calamagrostis',
         'willow non-dwarf shrubs',
         'needleleaf ericaceous dwarf shrubs',
         'white spruce',
         'black spruce',
         'Sitka spruce',
         'aspen',
         'poplar',
         'Rhododendron shrubs',
         'salmonberry',
         'Sphagnum moss',
         'mountain hemlock',
         'bog blueberry',
         'lingonberry',
         'wetland sedges']
model_types = ['lgbm', 'lgbm', 'lgbm', 'lgbm', 'lgbm no_clim', 'lgbm no_clim', 'lgbm no_clim',
               'lgbm', 'lgbm', 'lgbm', 'lgbm no_clim', 'lgbm', 'lgbm', 'rf', 'lgbm no_clim',
               'lgbm', 'lgbm', 'rf', 'lgbm', 'lgbm no_clim', 'lgbm', 'rf', 'lgbm']
life_forms = ['shrub', 'shrub', 'tree', 'tree', 'dwarf shrub', 'dwarf shrub', 'dwarf shrub',
              'herbaceous', 'herbaceous', 'shrub', 'dwarf shrub', 'tree', 'tree', 'tree',
              'tree', 'tree', 'dwarf shrub', 'shrub', 'moss', 'tree', 'shrub', 'dwarf shrub',
              'herbaceous']

# Define output variables
output_variables = ['abbrev', 'indicator_name', 'model_type', 'life_form', 'n_presence',
                    'r2_site', 'rmse_site', 'auc_site', 'acc_site',
                    'cover_median', 'cover_mean', 'r2_scaled', 'rmse_scaled',
                    'n_grid', 'r2_region', 'rmse_region']

# Create empty list to store results
performance_results_list = []

#### CALCULATE MULTI-SCALE RESULTS
####____________________________________________________

# Read input grid and create grid_id
grid_data = gpd.read_file(grid_input)
grid_data['grid_id'] = range(1, len(grid_data) + 1)
grid_data = grid_data[['grid_id', 'geometry']]

# Read input regions
region_data = gpd.read_file(region_input)
region_data = region_data[['region', 'geometry']]

# Loop through each diagnostic species set
count = 1
for indicator in indicators:
    print(f'Processing data for indicator {count} of {len(indicators)}: {indicator}...')

    # Define input files for indicator
    indicator_folder = os.path.join(input_folder, indicator)
    indicator_input = os.path.join(indicator_folder, f'{indicator}_results.csv')
    r2_input = os.path.join(indicator_folder, f'{indicator}_r2.txt')
    rmse_input = os.path.join(indicator_folder, f'{indicator}_rmse.txt')
    auc_input = os.path.join(indicator_folder, f'{indicator}_auc.txt')
    acc_input = os.path.join(indicator_folder, f'{indicator}_acc.txt')

    # Define output files for indicator
    scaled_output = os.path.join(indicator_folder, f'{indicator}_scaled.csv')
    region_output = os.path.join(indicator_folder, f'{indicator}_region.csv')

    # Read input data
    input_data = pd.read_csv(indicator_input)
    input_data = input_data[['st_vst', 'cvr_pct', 'prediction', 'cent_x', 'cent_y']]

    # Convert to spatial dataframe
    input_data = gpd.GeoDataFrame(
        input_data,
        geometry=gpd.points_from_xy(input_data.cent_x,
                                    input_data.cent_y),
        crs='EPSG:3338')

    # Join 10 km grids
    input_data = gpd.sjoin(input_data, grid_data, how="left", predicate="within")
    if 'index_right' in input_data.columns:
        input_data = input_data.drop(columns=['index_right'])

    # Join regions
    input_data = gpd.sjoin(input_data, region_data, how="left", predicate="within")
    if 'index_right' in input_data.columns:
        input_data = input_data.drop(columns=['index_right'])

    # Drop geometry for standard pandas aggregation
    input_data = pd.DataFrame(input_data.drop(columns='geometry'))

    # Summarize data by grid and remove grids with < 3 sites
    grid_summary = input_data.groupby('grid_id').agg(
        n_stvst=('st_vst', 'size'),
        mean_cvr_pct=('cvr_pct', 'mean'),
        mean_prediction=('prediction', 'mean')
    ).reset_index()
    grid_summary = grid_summary[grid_summary['n_stvst'] >= 3]

    # Summarize data by region and remove regions with < 50 sites
    region_summary = input_data.groupby('region').agg(
        n_stvst=('st_vst', 'size'),
        mean_cvr_pct=('cvr_pct', 'mean'),
        mean_prediction=('prediction', 'mean')
    ).reset_index()
    region_summary = region_summary[region_summary['n_stvst'] >= 50]

    # Export scaled data
    grid_summary.to_csv(scaled_output, header=True, index=False, sep=',', encoding='utf-8')
    region_summary.to_csv(region_output, header=True, index=False, sep=',', encoding='utf-8')

    # Read text performance metrics
    with open(r2_input, 'r') as text_read:
        r2_site = float(text_read.readline())
    with open(rmse_input, 'r') as text_read:
        rmse_site = float(text_read.readline())
    with open(auc_input, 'r') as text_read:
        auc_site = float(text_read.readline())
    with open(acc_input, 'r') as text_read:
        acc_site = float(text_read.readline())

    # Calculate mean and median cover for presences at the site level
    site_presences = input_data[input_data['cvr_pct'] >= 3]
    n_presence = len(site_presences)
    cover_mean = round(site_presences['cvr_pct'].mean(), 1)
    cover_median = round(site_presences['cvr_pct'].median(), 1)

    # Calculate scaled performance from grid summary
    y_scaled_obs = grid_summary['mean_cvr_pct'].astype(float)
    y_scaled_pred = grid_summary['mean_prediction'].astype(float)

    # Only calculate if data exists to avoid errors
    if not y_scaled_obs.empty:
        r2_scaled = r2_score(y_scaled_obs, y_scaled_pred, multioutput='uniform_average')
        rmse_scaled = np.sqrt(mean_squared_error(y_scaled_obs, y_scaled_pred))
    else:
        r2_scaled, rmse_scaled = np.nan, np.nan

    # Define number of grids with presences
    n_grid = len(grid_summary[grid_summary['mean_cvr_pct'] >= 1])

    # Calculate scaled performance from region summary
    y_region_obs = region_summary['mean_cvr_pct'].astype(float)
    y_region_pred = region_summary['mean_prediction'].astype(float)

    # Only calculate if data exists to avoid errors
    if not y_region_obs.empty:
        r2_region = r2_score(y_region_obs, y_region_pred, multioutput='uniform_average')
        rmse_region = np.sqrt(mean_squared_error(y_region_obs, y_region_pred))
    else:
        r2_region, rmse_region = np.nan, np.nan

    # Create dictionary representing the row
    indicator_dict = {
        'abbrev': indicator,
        'indicator_name': names[count - 1],
        'model_type': model_types[count - 1],
        'life_form': life_forms[count - 1],
        'n_presence': n_presence,
        'r2_site': r2_site,
        'rmse_site': rmse_site,
        'auc_site': auc_site,
        'acc_site': acc_site,
        'cover_median': cover_median,
        'cover_mean': cover_mean,
        'r2_scaled': round(r2_scaled, 3) if pd.notna(r2_scaled) else np.nan,
        'rmse_scaled': round(rmse_scaled, 1) if pd.notna(rmse_scaled) else np.nan,
        'n_grid': n_grid,
        'r2_region': round(r2_region, 3) if pd.notna(r2_region) else np.nan,
        'rmse_region': round(rmse_region, 1) if pd.notna(rmse_region) else np.nan
    }

    performance_results_list.append(indicator_dict)

    count += 1
    print('----------')

#### EXPORT RESULTS
####____________________________________________________

# Convert list of dicts to DataFrame
print('Exporting final performance table to csv...')
performance_data = pd.DataFrame(performance_results_list, columns=output_variables)

# Export to csv
performance_data.to_csv(performance_output, header=True, index=False, sep=',', encoding='utf-8')
print('--- Script Finished ---')
