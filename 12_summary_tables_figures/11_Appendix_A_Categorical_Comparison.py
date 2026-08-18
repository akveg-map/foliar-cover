# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Create indicator performance map comparison
# Author: Timm Nawrocki
# Last Updated: 2026-08-11
# Usage: Must be executed in an Anaconda Python 3.7+ installation.
# Description: "Create indicator performance map comparison" calculates the r squared and root mean squared error of the categorical vegetation maps and creates an output table to compare with the foliar cover maps.
# ---------------------------------------------------------------------------

# Import packages
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from sklearn.preprocessing import OneHotEncoder
from sklearn.utils import shuffle
from sklearn.model_selection import KFold
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error

# Set version date
version_date = '20260415'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
site_folder = os.path.join(project_folder, f'Data_Input/site_data/version_{version_date}')
ancillary_folder = os.path.join(project_folder, 'Data_Input/ancillary_data/processed')
region_folder = os.path.join(project_folder, 'Data_Input/region_data')
model_folder = os.path.join(project_folder, f'Data_Output/model_results/version_{version_date}')
output_folder = os.path.join(project_folder, f'Data_Output/summary_results/version_{version_date}')

# Define input file
performance_input = os.path.join(output_folder, 'Table1_Individual_Performance.xlsx')
site_visit_input = os.path.join(site_folder, 'akveg_site_visits_3338.csv')
domain_input = os.path.join(region_folder, 'AlaskaYukon_MapDomain_v2p1_3338.shp')
akvwc_input = os.path.join(ancillary_folder, 'AlaskaVegetationWetlandComposite_Fine_30m_3338_v20180412.tif')
landfire_input = os.path.join(ancillary_folder, 'LA23_EVT_240.tif')

# Define output file
performance_output = os.path.join(output_folder, 'TableA3_Indicator_Performance_Comparison.xlsx')

# Define diagnostic species sets
diagnostic_sets = ['alnus', 'bderishr', 'beach', 'betshr', 'bettre', 'brotre',
                   'dryas', 'dsalix', 'empnig', 'erivag', 'feather', 'forb', 'gramin',
                   'halgra', 'lichen', 'mwcalama', 'ndsalix', 'neetre', 'nerishr',
                   'picgla', 'picmar', 'picsit', 'poptre', 'populbt', 'rhoshr', 'rubspe',
                   'sphagn', 'tsuhet', 'tsumer', 'vaculi', 'vacvit', 'wetforb', 'wetsed']

# Define 10-fold cross validation split methods
outer_cv_splits = KFold(n_splits=10, shuffle=True, random_state=314)

# Create an empty list to store the final performance dictionaries
performance_results = []

#### PROCESS SITE VISIT DATA
####____________________________________________________
print('Preparing site visit data...')

# Read input site visit data
site_visit_data = pd.read_csv(site_visit_input)

# Read input shapefiles
domain_shape = gpd.read_file(domain_input)

# Remove exclusion sites
site_visit_data = site_visit_data[site_visit_data['exclude'] == 0].copy()

# Create geodataframe
site_visit_data = gpd.GeoDataFrame(
    site_visit_data,
    geometry=gpd.points_from_xy(site_visit_data.cent_x,
                                site_visit_data.cent_y),
    crs='EPSG:3338')

# Subset points to map domain
site_visit_data = gpd.clip(site_visit_data, domain_shape)

# Identify coordinates from site visit data
coordinates = [(x, y) for x, y in zip(site_visit_data.geometry.x, site_visit_data.geometry.y)]

# Extract AKVWC fine classes from raster to sites
print('\tExtracting AKVWC fine classes...')
with rasterio.open(akvwc_input) as src:
    # Capture the AKVWC nodata value
    akvwc_nodata = src.nodata
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['akvwc_fine'] = [x[0] for x in extracted_values]

# Extract Landfire classes from raster to sites
print('\tExtracting Landfire classes...')
with rasterio.open(landfire_input) as src:
    # Capture the Landfire nodata value
    landfire_nodata = src.nodata
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['landfire_evt'] = [x[0] for x in extracted_values]

# Remove sites that do not have valid data in the AKVWC or Landfire maps
site_visit_data = site_visit_data[(site_visit_data['akvwc_fine'] != akvwc_nodata)
                                  & (site_visit_data['landfire_evt'] != landfire_nodata)
                                  & (site_visit_data['landfire_evt'] != -9999)].copy()

# Prepend 'm' prefix to valid raster extractions (ignore NA values)
site_visit_data['akvwc_fine'] = site_visit_data['akvwc_fine'].apply(
    lambda x: f'm{int(x)}' if pd.notna(x) and x != 0 else np.nan
)
site_visit_data['landfire_evt'] = site_visit_data['landfire_evt'].apply(
    lambda x: f'm{int(x)}' if pd.notna(x) and x != 0 else np.nan
)

# Select columns
site_visit_data = site_visit_data[['site_visit_code', 'akvwc_fine', 'landfire_evt']]

#### CALCULATE MAP PERFORMANCE
####____________________________________________________

# Loop through model output folders and calculate map performance
count = 1
for diagnostic_set in diagnostic_sets:
    print(f'Processing diagnostic set {count} of {len(diagnostic_sets)}...')

    # Define input file
    input_file = os.path.join(model_folder, diagnostic_set, f'{diagnostic_set}_results.csv')

    # Read input file
    input_data = pd.read_csv(input_file)[['site_visit_code', 'cover_percent', 'prediction']]

    # Rename observed column
    input_data = input_data.rename(columns={'cover_percent': 'observed'})

    # Join input data to site visit data
    input_data = pd.merge(site_visit_data, input_data, on='site_visit_code', how='left')
    input_data = input_data.dropna()

    # Shuffle data
    input_data = shuffle(input_data, random_state=21).reset_index(drop=True)

    #### CALCULATE AKVWC PERFORMANCE
    ####____________________________________________________

    # Set the discrete X data and reshape for the encoder
    X_akvwc = input_data['akvwc_fine']
    X_akvwc_array = np.asarray(X_akvwc).reshape(-1, 1)

    # Fit a one-hot encoder to the discrete map classes
    encoder_akvwc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    X_akvwc_trans = encoder_akvwc.fit_transform(X_akvwc_array)

    # Lists to store true and predicted values across all folds
    y_observed_all = []
    y_predicted_all = []

    # Iterate through outer cross-validation splits
    for train_index, test_index in outer_cv_splits.split(input_data):
        #### CONDUCT MODEL TRAIN

        # Identify X and y train splits
        X_train_regress = X_akvwc_trans[train_index]
        y_train_regress = input_data.loc[train_index, 'observed']

        # Fit linear regression
        regression = LinearRegression()
        regression.fit(X_train_regress, y_train_regress)

        #### CONDUCT MODEL TEST

        # Identify X and y test splits
        X_test_regress = X_akvwc_trans[test_index]
        y_test_observed = input_data.loc[test_index, 'observed']

        # Use the regressor to predict foliar cover response
        y_test_predicted = regression.predict(X_test_regress)

        # Store predictions and observations for this fold
        y_observed_all.extend(y_test_observed)
        y_predicted_all.extend(y_test_predicted)

    # Calculate performance metrics using concatenated fold results
    r2_akvwc = r2_score(y_observed_all, y_predicted_all)
    rmse_akvwc = np.sqrt(mean_squared_error(y_observed_all, y_predicted_all))

    #### CALCULATE LANDFIRE PERFORMANCE
    ####____________________________________________________

    # Set the discrete X data and reshape for the encoder
    X_lf = input_data['landfire_evt']
    X_lf_array = np.asarray(X_lf).reshape(-1, 1)

    # Fit a one-hot encoder to the discrete map classes
    encoder_lf = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    X_lf_trans = encoder_lf.fit_transform(X_lf_array)

    # Lists to store true and predicted values across all folds
    y_observed_all = []
    y_predicted_all = []

    # Iterate through outer cross-validation splits
    for train_index, test_index in outer_cv_splits.split(input_data):
        #### CONDUCT MODEL TRAIN

        # Identify X and y train splits
        X_train_regress = X_lf_trans[train_index]
        y_train_regress = input_data.loc[train_index, 'observed']

        # Fit linear regression
        regression = LinearRegression()
        regression.fit(X_train_regress, y_train_regress)

        #### CONDUCT MODEL TEST

        # Identify X and y test splits
        X_test_regress = X_lf_trans[test_index]
        y_test_observed = input_data.loc[test_index, 'observed']

        # Use the regressor to predict foliar cover response
        y_test_predicted = regression.predict(X_test_regress)

        # Store predictions and observations for this fold
        y_observed_all.extend(y_test_observed)
        y_predicted_all.extend(y_test_predicted)

    # Calculate performance metrics using concatenated fold results
    r2_lf = r2_score(y_observed_all, y_predicted_all)
    rmse_lf = np.sqrt(mean_squared_error(y_observed_all, y_predicted_all))

    #### STORE RESULTS
    ####____________________________________________________

    # Append results as a dictionary
    performance_results.append({
        'abbrev': diagnostic_set,
        'R2_akvwc': round(r2_akvwc, 2),
        'R2_landfire': round(r2_lf, 2)
    })

    count += 1

# Convert results list to a data frame
categorical_results = pd.DataFrame(performance_results)

# Read performance input
performance_data = pd.read_excel(performance_input, sheet_name='Sheet1')
performance_data = performance_data.rename(columns={'R2_site': 'R2_foliar'})

# Join categorical results to foliar performance
performance_data = pd.merge(performance_data, categorical_results, on='abbrev', how='left')
performance_data = performance_data[['abbrev', 'Diagnostic Species Set', 'Pres.',
                                     'R2_foliar', 'R2_akvwc', 'R2_landfire']]

# Calculate the mean for each column and create a new row
mean_row = pd.DataFrame([{
    'abbrev': 'mean',
    'Diagnostic Species Set': 'mean',
    'Pres.': 'NA',
    'R2_foliar': performance_data['R2_foliar'].mean().round(2),
    'R2_akvwc': performance_data['R2_akvwc'].mean().round(2),
    'R2_landfire': performance_data['R2_landfire'].mean().round(2)
}])

# Append the mean row to the bottom of the data frame
performance_data = pd.concat([performance_data, mean_row], ignore_index=True)

# Export the final data frame to csv
performance_data.to_excel(performance_output, index=False)
