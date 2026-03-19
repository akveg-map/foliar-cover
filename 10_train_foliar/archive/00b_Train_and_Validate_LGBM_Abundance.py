# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Train and Validate LightGBM Abundance Model
# Author: Timm Nawrocki, Matt Macander
# Last Updated: 2025-10-02
#
# Usage: Must be executed in an Anaconda Python 3.12+ installation.
#
# Description: This script consolidates the training and validation process for
# a LightGBM abundance model. It performs two main functions in sequence:
#   1. Trains a final LGBM classifier and regressor on the entire dataset,
#      optimizes parameters, determines a classification threshold, and saves
#      the final model objects (.joblib) and GEE-compatible tree strings.
#   2. Conducts a full, spatially-aware, nested cross-validation to
#      rigorously assess model performance. It outputs detailed validation
#      results and summary metrics (AUC, R-squared, RMSE, etc.).
#
# Parallel Execution Warning:
#   This script is designed to be run as a single process for a given output
#   directory. Running multiple instances of this script in parallel with the
#   *same* output folder will cause a race condition, leading to corrupted or
#   incomplete output files. Ensure that each parallel job writes to a
#   unique output folder by specifying a different `round_date` and `group`.
#
# Example usage from the command line:
#   python3 scripts/train_and_validate_lgbm_abundance.py \
#       --group betshr \
#       --round_date 20250930_emb_topo_lgbm \
#       --predictors emb topo \
#       --covariate_input 20250930/03_site_visit_all_buffer_3338_20250408_x_akveg_covar_emb_rand.csv \
#       --presence_threshold 3 \
#       --species_suffix _3338.csv \
#       --init_points 30 \
#       --n_iter 70
# ---------------------------------------------------------------------------

# Import packages
import argparse
import os
import time
import joblib
import lightgbm
import numpy as np
import pandas as pd
from akutils import *
from sklearn.metrics import (confusion_matrix, roc_auc_score, mean_squared_error,
                             mean_absolute_error, r2_score)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.utils import shuffle

#### SET UP AND PARSE ARGUMENTS
####____________________________________________________

# Create argument parser
parser = argparse.ArgumentParser(description='Train and validate a LightGBM abundance model.')

# Add arguments
parser.add_argument('--group', type=str, required=True, help='The species group to model (e.g., betshr).')
parser.add_argument('--round_date', type=str, required=True, help='The date stamp for the model run (e.g., 20250930_emb_topo_lgbm).')
parser.add_argument('--predictors', nargs='+', required=True, help='A list of predictor sets to use. Options: clim, s1, s2, topo, emb.')
parser.add_argument('--covariate_input', type=str, required=True, help='Relative path to the covariate data file from the extract_folder.')
parser.add_argument('--presence_threshold', type=int, default=3, help='Minimum predicted cover percentage to be considered "present".')
parser.add_argument('--species_suffix', type=str, default='_3338.csv', help='Suffix for the species input filename, following the group name (e.g., "_3338.csv").')
parser.add_argument('--init_points', type=int, default=30, help='Number of initial points for Bayesian optimization.')
parser.add_argument('--n_iter', type=int, default=70, help='Number of iterations for Bayesian optimization.')


# Parse arguments
args = parser.parse_args()

# Assign arguments to variables
group = args.group
round_date = args.round_date
predictor_names = args.predictors
covariate_relative_path = args.covariate_input
presence_threshold = args.presence_threshold
species_suffix = args.species_suffix
init_points = args.init_points
n_iter = args.n_iter

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = '/data/gis/raster_base/Alaska/AKVegMap'
root_folder = 'akveg-working'

# Define folder structure
extract_folder = os.path.join(drive, root_folder, 'Data_Input/extract_data')
species_folder = os.path.join(drive, root_folder, 'Data_Input/species_data')
output_folder = os.path.join(drive, root_folder, 'Data_Output/model_results', round_date, group)
os.makedirs(output_folder, exist_ok=True)

# Define input files
covariate_input = os.path.join(extract_folder, covariate_relative_path)
species_input = os.path.join(species_folder, f'cover_{group}{species_suffix}')

# Define output files for final trained model
threshold_output_final = os.path.join(output_folder, f'{group}_threshold_final.txt')
classifier_output = os.path.join(output_folder, f'{group}_classifier.joblib')
regressor_output = os.path.join(output_folder, f'{group}_regressor.joblib')
classifier_treestring_output = os.path.join(output_folder, f'{group}_classifier_treestring.txt')
regressor_treestring_output = os.path.join(output_folder, f'{group}_regressor_treestring.txt')
classifier_model_txt = os.path.join(output_folder, f'{group}_classifier_booster.txt')
regressor_model_txt = os.path.join(output_folder, f'{group}_regressor_booster.txt')

# Define output files for validation results
results_output = os.path.join(output_folder, f'{group}_results.csv')
importance_output = os.path.join(output_folder, f'{group}_importances.csv')
auc_output = os.path.join(output_folder, f'{group}_auc.txt')
acc_output = os.path.join(output_folder, f'{group}_acc.txt')
threshold_output_mean = os.path.join(output_folder, f'{group}_threshold_mean.txt')
rscore_output = os.path.join(output_folder, f'{group}_r2.txt')
rmse_output = os.path.join(output_folder, f'{group}_rmse.txt')
mae_output = os.path.join(output_folder, f'{group}_mae.txt')

# Define variable sets
validation = ['valid']
predictor_clim = ['summer', 'january', 'precip']
predictor_s1 =   ['s1_1_vha', 's1_1_vhd', 's1_1_vva', 's1_1_vvd',
                 's1_2_vha', 's1_2_vhd', 's1_2_vva', 's1_2_vvd',
                 's1_3_vha', 's1_3_vhd', 's1_3_vva', 's1_3_vvd']
predictor_s2 =   [f's2_{i}_{band}' for i in range(1, 6) for band in
                 ['blue', 'green', 'red', 'redge1', 'redge2', 'redge3', 'nir',
                  'redge4', 'swir1', 'swir2', 'nbr', 'ngrdi', 'ndmi', 'ndsi',
                  'ndvi', 'ndwi']]
predictor_topo = ['coast', 'stream', 'river', 'wetness',
                 'elevation', 'exposure', 'heatload', 'position',
                 'aspect', 'relief', 'roughness', 'slope']
predictor_emb =  ['A' + str(i).zfill(2) for i in range(64)]

# Dynamically build predictor_all list from input arguments
predictor_map = {
    'clim': predictor_clim, 's1': predictor_s1, 's2': predictor_s2,
    'topo': predictor_topo, 'emb': predictor_emb
}
predictor_all = []
for name in predictor_names:
    if name in predictor_map:
        predictor_all.extend(predictor_map[name])
    else:
        print(f"Warning: Predictor set '{name}' not recognized and will be skipped.")
if not predictor_all:
    raise ValueError("No valid predictor sets were provided. Exiting.")

# Define other field sets
obs_pres = ['presence']
obs_cover = ['cvr_pct']
retain_variables = ['st_vst'] + validation
all_variables = retain_variables + predictor_all + obs_pres + obs_cover
pred_abs = ['pred_abs']
pred_pres = ['pred_pres']
pred_bin = ['pred_bin']
pred_cover = ['pred_cover']
prediction = ['prediction']
outer_split = ['outer_split_n']
inner_split = ['inner_split_n']
inner_columns = all_variables + pred_abs + pred_pres + inner_split
outer_columns = all_variables + pred_abs + pred_pres + pred_cover + pred_bin + outer_split

# Define cross validation methods
outer_cv_splits = StratifiedGroupKFold(n_splits=10)
inner_cv_splits = StratifiedGroupKFold(n_splits=10)

#### PREPARE INPUT DATA
####____________________________________________________

# Read and merge input data
print('Loading input data...')
start_time = time.time()
covariate_data = pd.read_csv(covariate_input)
covariate_data[predictor_all] = covariate_data[predictor_all].astype('float')
species_data = pd.read_csv(species_input)[['st_vst', 'cvr_pct', 'presence', 'valid']]
input_data = species_data.merge(covariate_data, how='inner', on='st_vst')

# Shuffle data
shuffled_data = shuffle(input_data, random_state=314).copy()
end_timing(start_time)

# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# PART 1: TRAIN FINAL MODEL ON FULL DATASET
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #

print('\n' + '='*50)
print('PART 1: TRAINING FINAL MODEL')
print('='*50)

#### OPTIMIZE FINAL MODEL PARAMETERS
####____________________________________________________

print('Optimizing final classifier parameters on full dataset...')
classifier_params = optimize_lgbmclassifier(
    init_points=init_points, n_iter=n_iter, data=shuffled_data,
    all_variables=all_variables, predictor_all=predictor_all,
    target_field=obs_pres, stratify_field=obs_pres, group_field=validation
)
# Sanitize classifier parameters to ensure correct types
classifier_params['n_estimators'] = int(classifier_params['n_estimators'])
classifier_params['num_leaves'] = int(classifier_params['num_leaves'])
classifier_params['max_depth'] = int(classifier_params['max_depth'])
classifier_params['min_child_samples'] = int(classifier_params['min_child_samples'])

print('Optimizing final regressor parameters on full dataset...')
regressor_params = optimize_lgbmregressor(
    init_points=init_points, n_iter=n_iter, data=shuffled_data,
    all_variables=all_variables, predictor_all=predictor_all,
    target_field=obs_cover, stratify_field=obs_pres, group_field=validation
)
# Sanitize regressor parameters to ensure correct types
regressor_params['n_estimators'] = int(regressor_params['n_estimators'])
regressor_params['num_leaves'] = int(regressor_params['num_leaves'])
regressor_params['max_depth'] = int(regressor_params['max_depth'])
regressor_params['min_child_samples'] = int(regressor_params['min_child_samples'])

#### DETERMINE FINAL CLASSIFICATION THRESHOLD
####____________________________________________________
print('Creating inner splits for final threshold determination...')
start_time = time.time()

# Create empty data frames
inner_train_final = pd.DataFrame()
inner_test_final = pd.DataFrame()
inner_results_final = pd.DataFrame()

# Create inner cross validation splits from the full dataset
count = 1
for train_index, test_index in inner_cv_splits.split(shuffled_data,
                                                     shuffled_data[obs_pres[0]].astype('int32'),
                                                     shuffled_data[validation[0]].astype('int32')):
    train = shuffled_data.iloc[train_index].assign(inner_split_n=count)
    test = shuffled_data.iloc[test_index].assign(inner_split_n=count)
    inner_train_final = pd.concat([inner_train_final, train], ignore_index=True)
    inner_test_final = pd.concat([inner_test_final, test], ignore_index=True)
    count += 1
inner_cv_length = count - 1
end_timing(start_time)

# Iterate through inner cross validation splits to find threshold
for inner_cv_i in range(1, inner_cv_length + 1):
    print(f'\tConducting inner CV for threshold: Iteration {inner_cv_i} of {inner_cv_length}...')
    train_iter = inner_train_final[inner_train_final[inner_split[0]] == inner_cv_i]
    test_iter = inner_test_final[inner_test_final[inner_split[0]] == inner_cv_i]

    X_train = train_iter[predictor_all].astype(float)
    y_train = train_iter[obs_pres[0]].astype('int32')
    X_test = test_iter[predictor_all].astype(float)

    inner_classifier = lightgbm.LGBMClassifier(**classifier_params, boosting_type='gbdt', objective='binary', class_weight='balanced', n_jobs=2, importance_type='gain', verbosity=-1)
    inner_classifier.fit(X_train, y_train)
    probability = inner_classifier.predict_proba(X_test)

    test_iter = test_iter.assign(pred_abs=probability[:, 0], pred_pres=probability[:, 1])
    inner_results_final = pd.concat([inner_results_final, test_iter], ignore_index=True)

# Calculate the optimal threshold
print('Calculating optimal classification threshold...')
final_threshold, _, _, _, _ = determine_optimal_threshold(
    inner_results_final[pred_pres[0]],
    inner_results_final[obs_pres[0]]
)

#### TRAIN AND EXPORT FINAL MODELS
####____________________________________________________
start_time = time.time()
print('Training and exporting final models...')

# Prepare full dataset for training
X_class_final = shuffled_data[predictor_all].astype(float)
y_class_final = shuffled_data[obs_pres[0]].astype('int32')
regress_data_final = shuffled_data[shuffled_data[obs_cover[0]] >= 0]
X_regress_final = regress_data_final[predictor_all].astype(float)
y_regress_final = regress_data_final[obs_cover[0]].astype(float)

# Train final classifier
print('\tTraining final classifier...')
final_classifier = lightgbm.LGBMClassifier(**classifier_params, boosting_type='gbdt', objective='binary', class_weight='balanced', n_jobs=2, importance_type='gain', verbosity=-1)
final_classifier.fit(X_class_final, y_class_final)

# Train final regressor
print('\tTraining final regressor...')
final_regressor = lightgbm.LGBMRegressor(**regressor_params, boosting_type='gbdt', objective='regression', n_jobs=2, importance_type='gain', verbosity=-1)
final_regressor.fit(X_regress_final, y_regress_final)

# Export final models and threshold
print('\tExporting artifacts...')
export_threshold = round(final_threshold, 5)
with open(threshold_output_final, 'w') as file:
    file.write(str(export_threshold))
joblib.dump(final_classifier, classifier_output)
joblib.dump(final_regressor, regressor_output)

#### GEE TREE STRING CONVERSION FUNCTIONS
####____________________________________________________

def treedf_to_string(df):
    # https://github.com/giswqs/geemap/blob/master/geemap/ml.py
    # the table representation does not have lef vs right node structure
    # so we need to add in right nodes in the correct location
    # we do this by first calculating which nodes are right and then insert them at the correct index

    # get a dict of right node rows and assign key based on index where to insert
    inserts = {}
    for row in df.itertuples():
        child_r = row.children_right
        if child_r > row.Index:
            ordered_row = np.array(row)
            ordered_row[-1] = ">"
            inserts[child_r] = ordered_row[1:]  # drop index value
    # sort the inserts as to keep track of the additive indexing
    inserts_sorted = {k: inserts[k] for k in sorted(inserts.keys())}

    # loop through the row inserts and add to table (array)
    table_values = df.values
    for i, k in enumerate(inserts_sorted.keys()):
        table_values = np.insert(table_values, (k + i), inserts_sorted[k], axis=0)

    # make the ordered table array into a dataframe
    # note: df is dtype "object", need to cast later on
    ordered_df = pd.DataFrame(table_values, columns=df.columns)

    max_depth = np.max(ordered_df.node_depth.astype(int))
    tree_str = f"1) root {df['n_samples'][0]} 9999 9999 ({df['criterion'].sum()})\n"
    previous_depth = -1
    cnts = []
    # loop through the nodes and calculate the node number and values per node
    for row in ordered_df.itertuples():
        node_depth = int(row.node_depth)
        left = int(row.children_left)
        right = int(row.children_right)
        if left != right:
            if row.Index == 0:
                cnt = 2
            elif previous_depth > node_depth:
                depths = ordered_df.node_depth.values[: row.Index]
                idx = np.where(depths == node_depth)[0][-1]
                # cnt = (cnts[row.Index-1] // 2) + 1
                cnt = cnts[idx] + 1
            elif previous_depth < node_depth:
                cnt = cnts[row.Index - 1] * 2
            elif previous_depth == node_depth:
                cnt = cnts[row.Index - 1] + 1

            if node_depth == (max_depth - 1):
                value = float(ordered_df.iloc[row.Index + 1].value)
                samps = int(ordered_df.iloc[row.Index + 1].n_samples)
                criterion = float(ordered_df.iloc[row.Index + 1].criterion)
                tail = " *\n"
            else:
                if (
                        (bool(ordered_df.loc[ordered_df.node_id == left].iloc[0].is_leaf))
                        and (
                        bool(
                            int(row.Index)
                            < int(ordered_df.loc[ordered_df.node_id == left].index[0])
                        )
                )
                        and (str(row.sign) == "<=")
                ):
                    rowx = ordered_df.loc[ordered_df.node_id == left].iloc[0]
                    tail = " *\n"
                    value = float(rowx.value)
                    samps = int(rowx.n_samples)
                    criterion = float(rowx.criterion)

                elif (
                        (bool(ordered_df.loc[ordered_df.node_id == right].iloc[0].is_leaf))
                        and (
                        bool(
                            int(row.Index)
                            < int(ordered_df.loc[ordered_df.node_id == right].index[0])
                        )
                )
                        and (str(row.sign) == ">")
                ):
                    rowx = ordered_df.loc[ordered_df.node_id == right].iloc[0]
                    tail = " *\n"
                    value = float(rowx.value)
                    samps = int(rowx.n_samples)
                    criterion = float(rowx.criterion)

                else:
                    value = float(row.value)
                    samps = int(row.n_samples)
                    criterion = float(row.criterion)
                    tail = "\n"

            # extract out the information needed in each line
            spacing = (node_depth + 1) * "  "  # for pretty printing
            fname = str(row.feature_name)  # name of the feature (i.e. band name)
            tresh = float(row.threshold)  # threshold
            sign = str(row.sign)

            tree_str += f"{spacing}{cnt}) {fname} {sign} {tresh:.6f} {samps} {criterion:.4f} {value:.6f}{tail}"
            previous_depth = node_depth
        cnts.append(cnt)

    return tree_str

def lgbm_booster_to_tree_df(booster):
    # Convert classifier or regressor (saved using .booster_.save_model) to parsed data frame
    classifier_df = booster.trees_to_dataframe()

    classifier_df["row_id"] = classifier_df.index

    classifier_df["node_id"] = classifier_df.groupby("tree_index")["row_id"].rank(method="first", ascending=True)
    classifier_df["node_id"] = classifier_df["node_id"] - 1
    classifier_df["node_id"] = classifier_df["node_id"].astype('Int64')

    classifier_nodes = classifier_df[['tree_index','node_index','node_id']]

    classifier_df = classifier_df.rename(columns={
                                         "split_gain":"criterion",
                                         "count":"n_samples",
                                         "split_feature":"feature_name"})

    classifier_df["is_leaf"] = pd.isnull(classifier_df["threshold"])
    classifier_df["sign"] = "<="
    classifier_df["node_depth"] = classifier_df["node_depth"] - 1

    classifier_df = pd.merge(classifier_df, classifier_nodes, how='left', left_on=['tree_index','left_child'], right_on=['tree_index','node_index'])
    classifier_df = classifier_df.rename(columns={"node_id_x":"node_id",
                                                   "node_id_y":"children_left"})
    # classifier_df = classifier_df.fillna(-1)
    classifier_df = pd.merge(classifier_df, classifier_nodes, how='left', left_on=['tree_index','right_child'], right_on=['tree_index','node_index'])
    classifier_df = classifier_df.rename(columns={"node_id_x":"node_id",
                                                   "node_id_y":"children_right"})

    classifier_df_out = classifier_df
    classifier_df_out = classifier_df[["tree_index",
                                       "node_id","node_depth","is_leaf","children_left","children_right","value","criterion",
                                      "n_samples","threshold","feature_name","sign"]]
    # classifier_df_out.dtypes
    # classifier_nodes
    classifier_df_out = classifier_df_out.fillna(value={'threshold': -2, 'children_right': -1, 'children_left': -1, 'criterion': 0})

    return classifier_df_out

# Generate and export tree strings for GEE
print('Generating and exporting GEE tree strings...')
# Process classifier
print('\tProcessing classifier...')
final_classifier.booster_.save_model(classifier_model_txt)
classifier_booster = lightgbm.Booster(model_file=classifier_model_txt)
classifier_tree_df = lgbm_booster_to_tree_df(classifier_booster)

classifier_trees = []
for tree in classifier_tree_df.tree_index.unique():
    treedf = classifier_tree_df[classifier_tree_df.tree_index == tree].reset_index(drop=True)
    # print(f'\t\tProcessing classifier tree {tree} with {len(treedf)} nodes...')
    tree_str = treedf_to_string(treedf)
    classifier_trees.append(tree_str)

print(f'\tExporting {len(classifier_trees)} classifier trees to text file...')
with open(classifier_treestring_output, "w") as text_file:
    text_file.writelines(classifier_trees)

# Process regressor
print('\tProcessing regressor...')
final_regressor.booster_.save_model(regressor_model_txt)
regressor_booster = lightgbm.Booster(model_file=regressor_model_txt)
regressor_tree_df = lgbm_booster_to_tree_df(regressor_booster)

regressor_trees = []
for tree in regressor_tree_df.tree_index.unique():
    treedf = regressor_tree_df[regressor_tree_df.tree_index == tree].reset_index(drop=True)
    # print(f'\t\tProcessing regressor tree {tree} with {len(treedf)} nodes...')
    tree_str = treedf_to_string(treedf)
    regressor_trees.append(tree_str)

print(f'\tExporting {len(regressor_trees)} regressor trees to text file...')
with open(regressor_treestring_output, "w") as text_file:
    text_file.writelines(regressor_trees)

end_timing(start_time)
print(f'Final models and threshold exported successfully for "{group}".')
print(f'Optimal Threshold: {export_threshold}')

# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# PART 2: PERFORM SPATIAL CROSS-VALIDATION
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #

print('\n' + '='*50)
print('PART 2: PERFORMING SPATIAL CROSS-VALIDATION')
print('='*50)

#### SETUP CROSS-VALIDATION DATA
####____________________________________________________
print('Creating outer cross validation splits...')
start_time = time.time()
outer_train = pd.DataFrame()
outer_test = pd.DataFrame()

count = 1
for train_index, test_index in outer_cv_splits.split(shuffled_data,
                                                     shuffled_data[obs_pres[0]].astype('int32'),
                                                     shuffled_data[validation[0]].astype('int32')):
    train = shuffled_data.iloc[train_index].assign(outer_split_n=count)
    test = shuffled_data.iloc[test_index].assign(outer_split_n=count)
    outer_train = pd.concat([outer_train, train], ignore_index=True)
    outer_test = pd.concat([outer_test, test], ignore_index=True)
    count += 1
outer_cv_length = count - 1
print(f'Created {outer_cv_length} outer cross-validation group splits.')
end_timing(start_time)

#### CONDUCT MODEL VALIDATION
####____________________________________________________
outer_results = pd.DataFrame()
importance_results = pd.DataFrame()
threshold_list = []

# Iterate through outer cross validation splits
for outer_cv_i in range(1, outer_cv_length + 1):
    print(f'Conducting outer CV iteration {outer_cv_i} of {outer_cv_length}...')
    iter_start_time = time.time()

    # Partition outer data for this iteration
    outer_train_iter = outer_train[outer_train[outer_split[0]] == outer_cv_i].copy()
    outer_test_iter = outer_test[outer_test[outer_split[0]] == outer_cv_i].copy()

    # Optimize parameters for this specific outer fold
    print('\tOptimizing classifier parameters for outer fold...')
    cv_class_params = optimize_lgbmclassifier(init_points=init_points, n_iter=n_iter, data=outer_train_iter, all_variables=all_variables, predictor_all=predictor_all, target_field=obs_pres, stratify_field=obs_pres, group_field=validation)
    # Sanitize classifier parameters to ensure correct types
    cv_class_params['n_estimators'] = int(cv_class_params['n_estimators'])
    cv_class_params['num_leaves'] = int(cv_class_params['num_leaves'])
    cv_class_params['max_depth'] = int(cv_class_params['max_depth'])
    cv_class_params['min_child_samples'] = int(cv_class_params['min_child_samples'])
    
    print('\tOptimizing regressor parameters for outer fold...')
    cv_reg_params = optimize_lgbmregressor(init_points=init_points, n_iter=n_iter, data=outer_train_iter, all_variables=all_variables, predictor_all=predictor_all, target_field=obs_cover, stratify_field=obs_pres, group_field=validation)
    # Sanitize regressor parameters to ensure correct types
    cv_reg_params['n_estimators'] = int(cv_reg_params['n_estimators'])
    cv_reg_params['num_leaves'] = int(cv_reg_params['num_leaves'])
    cv_reg_params['max_depth'] = int(cv_reg_params['max_depth'])
    cv_reg_params['min_child_samples'] = int(cv_reg_params['min_child_samples'])

    # Setup inner data for threshold determination
    inner_train = pd.DataFrame()
    inner_results = pd.DataFrame()
    count = 1
    for train_idx, test_idx in inner_cv_splits.split(outer_train_iter, outer_train_iter[obs_pres[0]].astype('int32'), outer_train_iter[validation[0]].astype('int32')):
        train = outer_train_iter.iloc[train_idx].assign(inner_split_n=count)
        test = outer_train_iter.iloc[test_idx].assign(inner_split_n=count)
        
        # Train inner classifier
        inner_classifier = lightgbm.LGBMClassifier(**cv_class_params, boosting_type='gbdt', objective='binary', class_weight='balanced', n_jobs=2, verbosity=-1)
        inner_classifier.fit(train[predictor_all], train[obs_pres[0]])
        
        # Predict and store results
        probability = inner_classifier.predict_proba(test[predictor_all])
        test = test.assign(pred_abs=probability[:, 0], pred_pres=probability[:, 1])
        inner_results = pd.concat([inner_results, test], ignore_index=True)
        count += 1
        
    # Determine optimal threshold for this outer fold
    threshold, _, _, _, _ = determine_optimal_threshold(inner_results[pred_pres[0]], inner_results[obs_pres[0]])
    threshold_list.append(threshold)

    # Train outer models
    print('\tTraining outer models...')
    X_class_outer = outer_train_iter[predictor_all]
    y_class_outer = outer_train_iter[obs_pres[0]]
    outer_classifier = lightgbm.LGBMClassifier(**cv_class_params, boosting_type='gbdt', objective='binary', class_weight='balanced', n_jobs=2, importance_type='gain', verbosity=-1)
    outer_classifier.fit(X_class_outer, y_class_outer)

    regress_outer = outer_train_iter[outer_train_iter[obs_cover[0]] >= 0]
    X_regress_outer = regress_outer[predictor_all]
    y_regress_outer = regress_outer[obs_cover[0]]
    outer_regressor = lightgbm.LGBMRegressor(**cv_reg_params, boosting_type='gbdt', objective='regression', n_jobs=2, importance_type='gain', verbosity=-1)
    outer_regressor.fit(X_regress_outer, y_regress_outer)

    # Harvest feature importances
    class_imp = pd.DataFrame({'covariate': X_class_outer.columns, 'importance': outer_classifier.feature_importances_, 'component': 'classifier'})
    reg_imp = pd.DataFrame({'covariate': X_regress_outer.columns, 'importance': outer_regressor.feature_importances_, 'component': 'regressor'})
    importance_data = pd.concat([class_imp, reg_imp], ignore_index=True).assign(outer_cv_i=outer_cv_i)
    importance_results = pd.concat([importance_results, importance_data], ignore_index=True)

    # Predict on outer test set
    print('\tPredicting outer test data...')
    X_test_outer = outer_test_iter[predictor_all]
    prob_outer = outer_classifier.predict_proba(X_test_outer)
    cover_outer = outer_regressor.predict(X_test_outer)

    outer_test_iter = outer_test_iter.assign(
        pred_abs=prob_outer[:, 0],
        pred_pres=prob_outer[:, 1],
        pred_cover=cover_outer,
        pred_bin=(prob_outer[:, 1] >= threshold).astype(int)
    )
    outer_results = pd.concat([outer_results, outer_test_iter], ignore_index=True)
    end_timing(iter_start_time)

#### CALCULATE PERFORMANCE AND STORE VALIDATION RESULTS
####____________________________________________________
print('Calculating final performance metrics and storing validation results...')
start_time = time.time()

# Create a composite prediction
outer_results[prediction[0]] = np.where(
    (outer_results[pred_bin[0]] == 1) & (outer_results[pred_cover[0]] >= presence_threshold),
    outer_results[pred_cover[0]], 0
)
outer_results['distribution'] = ((outer_results[pred_bin[0]] == 1) & (outer_results[pred_cover[0]] >= presence_threshold)).astype(int)

# Clean and restrict results
valid_results = outer_results[outer_results[obs_cover[0]] >= 0].copy()
valid_results[prediction[0]] = np.clip(valid_results[prediction[0]], 0, 100)

# Partition observed vs predicted for metrics
y_class_obs = valid_results[obs_pres[0]]
y_class_pred_prob = valid_results[pred_pres[0]]
y_regress_obs = valid_results[obs_cover[0]]
y_regress_pred = valid_results[prediction[0]]

# Calculate metrics
tn, fp, fn, tp = confusion_matrix(y_class_obs, valid_results['distribution']).ravel()
validation_auc = roc_auc_score(y_class_obs, y_class_pred_prob)
validation_accuracy = (tp + tn) / (tp + tn + fp + fn)
r_score = r2_score(y_regress_obs, y_regress_pred)
mae = mean_absolute_error(y_regress_obs, y_regress_pred)
rmse = np.sqrt(mean_squared_error(y_regress_obs, y_regress_pred))

# Format metrics for export
export_auc = round(validation_auc, 3)
export_accuracy = round(validation_accuracy * 100, 1)
export_threshold_mean = round(np.mean(threshold_list), 5)
export_rscore = round(r_score, 3)
export_rmse = round(rmse, 1)
export_mae = round(mae, 1)

# Store output results
valid_results.to_csv(results_output, header=True, index=False)
importance_results.to_csv(importance_output, header=True, index=False)
metric_map = {
    auc_output: export_auc, acc_output: export_accuracy,
    threshold_output_mean: export_threshold_mean, rscore_output: export_rscore,
    rmse_output: export_rmse, mae_output: export_mae
}
for file_path, metric in metric_map.items():
    with open(file_path, 'w') as f:
        f.write(str(metric))

end_timing(start_time)

# Print final validation scores
print('\n--- Final Validation Metrics ---')
print(f'AUC: {export_auc}')
print(f'Accuracy: {export_accuracy}%')
print(f'Mean CV Threshold: {export_threshold_mean}')
print(f'R-squared: {export_rscore}')
print(f'RMSE: {export_rmse}')
print(f'MAE: {export_mae}')
print('--- Script Finished ---')

