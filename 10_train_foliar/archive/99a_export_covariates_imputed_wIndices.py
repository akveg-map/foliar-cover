# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Export Covariates with imputed data and spectral indices
# Note v2 indices are calculated from mean reflectance
# Author: Timm Nawrocki and Matt Macander
# Last Updated: 2025-10-01
# Usage: Must be executed in an Anaconda Python 3.12+ installation.
# Description: "Train LightGBM abundance model" trains and saves a LightGBM
# classifier and regressor for use in prediction. This script is a combination
# of the validation script (01d) and the final training script (02d).
#
# Example usage from the command line:
# python3 scripts/99a_export_covariates_imputed_wIndices.py --group betshr --round_date 20250930_emb_topo_lgbm --predictors emb topo
# ---------------------------------------------------------------------------

# Import packages
import argparse
import os
import pandas as pd
import time
from akutils import *
from sklearn.utils import shuffle
from sklearn.model_selection import StratifiedGroupKFold
from lightgbm import LGBMClassifier
from lightgbm import LGBMRegressor
import lightgbm
import joblib
import numpy as np

#### SET UP AND PARSE ARGUMENTS
####____________________________________________________

# Create argument parser
parser = argparse.ArgumentParser(description='Train a LightGBM abundance model.')

# Add arguments
parser.add_argument('--group', type=str, required=True, help='The species group to model (e.g., betshr).')
parser.add_argument('--round_date', type=str, required=True, help='The date stamp for the model run (e.g., 20250930_emb_topo_lgbm).')
parser.add_argument('--predictors', nargs='+', required=True, help='A list of predictor sets to use. Options: clim, s1, s2, topo, emb.')

# Parse arguments
args = parser.parse_args()

# Assign arguments to variables
group = args.group
round_date = args.round_date
predictor_names = args.predictors

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = '/data/gis/raster_base/Alaska/AKVegMap'
root_folder = 'akveg-working'

# Define folder structure
extract_folder = os.path.join(drive, root_folder, 'Data_Input/extract_data')
species_folder = os.path.join(drive, root_folder, 'Data_Input/species_data')
output_folder = os.path.join(drive, root_folder, 'Data_Output/model_results', round_date, group)
if os.path.exists(output_folder) == 0:
    os.makedirs(output_folder, exist_ok=True)

# Define input files
covariate_input = os.path.join(extract_folder, 'AKVEG_Sites_Covariates_3338.csv')
covariate_output = os.path.join(extract_folder, 'AKVEG_Sites_Covariates_3338_imputed_wIndices.csv')
species_input = os.path.join(species_folder, f'cover_{group}_3338.csv')

# Define output files
threshold_output = os.path.join(output_folder, f'{group}_threshold_final.txt')
classifier_output = os.path.join(output_folder, f'{group}_classifier.joblib')
regressor_output = os.path.join(output_folder, f'{group}_regressor.joblib')
classifier_treestring_output = os.path.join(output_folder, f'{group}_classifier_treestring.txt')
regressor_treestring_output = os.path.join(output_folder, f'{group}_regressor_treestring.txt')

# Define variable sets
validation = ['valid']
predictor_clim = ['summer', 'january', 'precip']
predictor_s1 =   ['s1_1_vha', 's1_1_vhd', 's1_1_vva', 's1_1_vvd',
                 's1_2_vha', 's1_2_vhd', 's1_2_vva', 's1_2_vvd',
                 's1_3_vha', 's1_3_vhd', 's1_3_vva', 's1_3_vvd']
predictor_s2 =   ['s2_1_blue', 's2_1_green', 's2_1_red', 's2_1_redge1', 's2_1_redge2',
                 's2_1_redge3', 's2_1_nir', 's2_1_redge4', 's2_1_swir1', 's2_1_swir2',
                 's2_1_nbr', 's2_1_ngrdi', 's2_1_ndmi', 's2_1_ndsi', 's2_1_ndvi', 's2_1_ndwi',
                 's2_2_blue', 's2_2_green', 's2_2_red', 's2_2_redge1', 's2_2_redge2',
                 's2_2_redge3', 's2_2_nir', 's2_2_redge4', 's2_2_swir1', 's2_2_swir2',
                 's2_2_nbr', 's2_2_ngrdi', 's2_2_ndmi', 's2_2_ndsi', 's2_2_ndvi', 's2_2_ndwi',
                 's2_3_blue', 's2_3_green', 's2_3_red', 's2_3_redge1', 's2_3_redge2',
                 's2_3_redge3', 's2_3_nir', 's2_3_redge4', 's2_3_swir1', 's2_3_swir2',
                 's2_3_nbr', 's2_3_ngrdi', 's2_3_ndmi', 's2_3_ndsi', 's2_3_ndvi', 's2_3_ndwi',
                 's2_4_blue', 's2_4_green', 's2_4_red', 's2_4_redge1', 's2_4_redge2',
                 's2_4_redge3', 's2_4_nir', 's2_4_redge4', 's2_4_swir1', 's2_4_swir2',
                 's2_4_nbr', 's2_4_ngrdi', 's2_4_ndmi', 's2_4_ndsi', 's2_4_ndvi', 's2_4_ndwi',
                 's2_5_blue', 's2_5_green', 's2_5_red', 's2_5_redge1', 's2_5_redge2',
                 's2_5_redge3', 's2_5_nir', 's2_5_redge4', 's2_5_swir1', 's2_5_swir2',
                 's2_5_nbr', 's2_5_ngrdi', 's2_5_ndmi', 's2_5_ndsi', 's2_5_ndvi', 's2_5_ndwi']
predictor_topo = ['coast', 'stream', 'river', 'wetness',
                 'elevation', 'exposure', 'heatload', 'position',
                 'aspect', 'relief', 'roughness', 'slope']
predictor_emb =  ['A' + str(i).zfill(2) for i in range(64)]

# Dynamically build predictor_all list from input arguments
predictor_map = {
    'clim': predictor_clim,
    's1': predictor_s1,
    's2': predictor_s2,
    'topo': predictor_topo,
    'emb': predictor_emb
}
predictor_all = []
for name in predictor_names:
    if name in predictor_map:
        predictor_all.extend(predictor_map[name])
    else:
        print(f"Warning: Predictor set '{name}' not recognized and will be skipped.")
if not predictor_all:
    raise ValueError("No valid predictor sets were provided. Exiting.")

obs_pres = ['presence']
obs_cover = ['cvr_pct']
retain_variables = ['st_vst'] + validation
all_variables = retain_variables + predictor_all + obs_pres + obs_cover
inner_split = ['inner_split_n']
pred_abs = ['pred_abs']
pred_pres = ['pred_pres']
inner_columns = all_variables + pred_abs + pred_pres + inner_split

# Define cross validation methods
inner_cv_splits = StratifiedGroupKFold(n_splits=10)

#### PREPARE INPUT DATA
####____________________________________________________

# Read input data to data frames
print('Loading input data...')
iteration_start = time.time()
covariate_data = pd.read_csv(covariate_input)
covariate_data = foliar_cover_predictors(covariate_data, predictor_all)
covariate_data.to_csv(covariate_output, header=True, index=False, sep=',', encoding='utf-8')

