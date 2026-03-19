# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Train and Validate Random Forest Abundance Model
# Author: Timm Nawrocki
# Last Updated: 2025-10-02
#
# Usage: Must be executed in an Anaconda Python 3.12+ installation.
#
# Description: This script consolidates the training and validation process for
# a Random Forest abundance model. It performs two main functions in sequence:
#   1. Trains a final RF classifier and regressor on the entire dataset,
#      determines a classification threshold, and saves the final model
#      objects (.joblib) and GEE-compatible tree strings.
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
#   python3 scripts/00a_Train_and_Validate_RF_Abundance.py \
#       --group betshr \
#       --round_date 20250930_emb_topo_rf \
#       --predictors emb topo \
#       --covariate_input 20250930/03_site_visit_all_buffer_3338_20250408_x_akveg_covar_emb_rand.csv \
#       --presence_threshold 3 \
#       --species_suffix _3338.csv
# ---------------------------------------------------------------------------

# Import packages
import argparse
import os
import time
import joblib
import numpy as np
import pandas as pd
from akutils import *
from sklearn.metrics import (confusion_matrix, roc_auc_score, mean_squared_error,
                             mean_absolute_error, r2_score)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.utils import shuffle
from imblearn.ensemble import BalancedRandomForestClassifier
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import _tree

#### SET UP AND PARSE ARGUMENTS
####____________________________________________________

# Create argument parser
parser = argparse.ArgumentParser(description='Train and validate a Random Forest abundance model.')

# Add arguments
parser.add_argument('--group', type=str, required=True, help='The species group to model (e.g., betshr).')
parser.add_argument('--round_date', type=str, required=True, help='The date stamp for the model run (e.g., 20250930_emb_topo_rf).')
parser.add_argument('--predictors', nargs='+', required=True, help='A list of predictor sets to use. Options: clim, s1, s2, topo, emb.')
parser.add_argument('--covariate_input', type=str, required=True, help='Relative path to the covariate data file from the extract_folder.')
parser.add_argument('--presence_threshold', type=int, default=3, help='Minimum predicted cover percentage to be considered "present".')
parser.add_argument('--species_suffix', type=str, default='_3338.csv', help='Suffix for the species input filename, following the group name (e.g., "_3338.csv").')

# Parse arguments
args = parser.parse_args()

# Assign arguments to variables
group = args.group
round_date = args.round_date
predictor_names = args.predictors
covariate_relative_path = args.covariate_input
presence_threshold = args.presence_threshold
species_suffix = args.species_suffix

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
# Placeholder output files for GEE-compatible model export
classifier_treestring_output = os.path.join(output_folder, f'{group}_classifier_treestring.txt')
regressor_treestring_output = os.path.join(output_folder, f'{group}_regressor_treestring.txt')


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

# Create a standardized parameter set for a random forest classifier
classifier_params = {'n_estimators': 500,
                     'criterion': 'gini',
                     'max_depth': None,
                     'min_samples_split': 2,
                     'min_samples_leaf': 1,
                     'min_weight_fraction_leaf': 0,
                     'max_features': 'sqrt',
                     'bootstrap': True,
                     'oob_score': False,
                     'sampling_strategy': 'all',
                     'replacement': True,
                     'warm_start': False,
                     'class_weight': None,
                     'n_jobs': -1,
                     'random_state': 314}

# Create a standardized parameter set for a random forest regressor
regressor_params = {'n_estimators': 500,
                    'criterion': 'squared_error',
                    'max_depth': None,
                    'min_samples_split': 2,
                    'min_samples_leaf': 1,
                    'min_weight_fraction_leaf': 0,
                    'max_features': 'sqrt',
                    'bootstrap': True,
                    'oob_score': False,
                    'warm_start': False,
                    'n_jobs': -1,
                    'random_state': 314}

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

    inner_classifier = BalancedRandomForestClassifier(**classifier_params)
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
final_classifier = BalancedRandomForestClassifier(**classifier_params)
final_classifier.fit(X_class_final, y_class_final)

# Train final regressor
print('\tTraining final regressor...')
final_regressor = RandomForestRegressor(**regressor_params)
final_regressor.fit(X_regress_final, y_regress_final)

# Export final models and threshold
print('\tExporting artifacts...')
export_threshold = round(final_threshold, 5)
with open(threshold_output_final, 'w') as file:
    file.write(str(export_threshold))
joblib.dump(final_classifier, classifier_output)
joblib.dump(final_regressor, regressor_output)
end_timing(start_time)

#### GEE TREE STRING CONVERSION (OPTIMIZED)
####____________________________________________________

def rf_to_gee_strings(model, feature_names, model_type):
    """
    Converts a scikit-learn RandomForest model to a list of GEE-compatible strings.
    This optimized version avoids slow DataFrame manipulations and uses direct
    tree traversal for much better performance with large models.
    """
    strings = []
    for tree in model.estimators_:
        tree_ = tree.tree_
        is_regressor = model_type == 'regressor'

        # First pass: Get GEE node numbers using a level-order traversal
        node_to_cnt = {0: 1}
        queue = [(0, 1)]
        head = 0
        while head < len(queue):
            current_node, current_cnt = queue[head]
            head += 1
            if tree_.feature[current_node] != _tree.TREE_UNDEFINED:
                left_child = tree_.children_left[current_node]
                right_child = tree_.children_right[current_node]
                left_cnt = current_cnt * 2
                right_cnt = current_cnt * 2 + 1
                node_to_cnt[left_child] = left_cnt
                node_to_cnt[right_child] = right_cnt
                queue.append((left_child, left_cnt))
                queue.append((right_child, right_cnt))

        # Second pass: Build the string using a recursive depth-first traversal
        tree_string_parts = []
        
        # Add root line
        root_impurity = tree_.impurity[0]
        root_samples = tree_.n_node_samples[0]
        tree_string_parts.append(f"1) root {root_samples} 9999 9999 ({root_impurity})\n")

        def recurse(node_id, depth):
            """Recursive helper to build the string for each node."""
            if tree_.feature[node_id] == _tree.TREE_UNDEFINED:
                return

            # --- Left Branch ---
            left_child_id = tree_.children_left[node_id]
            sign = "<="
            
            # Get node properties
            feature_name = feature_names[tree_.feature[node_id]]
            threshold = tree_.threshold[node_id]
            n_samples = tree_.n_node_samples[node_id]
            impurity = tree_.impurity[node_id]
            cnt = node_to_cnt.get(left_child_id, 0)
            indent = "  " * depth

            # Determine value and tail
            is_leaf = tree_.feature[left_child_id] == _tree.TREE_UNDEFINED
            if is_leaf:
                if is_regressor:
                    value = tree_.value[left_child_id][0][0]
                else:
                    value = tree_.value[left_child_id][0][1] / np.sum(tree_.value[left_child_id][0]) if np.sum(tree_.value[left_child_id][0]) > 0 else 0
                tail = " *\n"
            else: # Not a leaf, use parent's value
                if is_regressor:
                    value = tree_.value[node_id][0][0]
                else:
                    value = tree_.value[node_id][0][1] / np.sum(tree_.value[node_id][0]) if np.sum(tree_.value[node_id][0]) > 0 else 0
                tail = "\n"

            tree_string_parts.append(f"{indent}{cnt}) {feature_name} {sign} {threshold:.6f} {n_samples} {impurity:.4f} {value:.6f}{tail}")
            if not is_leaf:
                recurse(left_child_id, depth + 1)
            
            # --- Right Branch ---
            right_child_id = tree_.children_right[node_id]
            sign = ">"
            cnt = node_to_cnt.get(right_child_id, 0)
            
            is_leaf = tree_.feature[right_child_id] == _tree.TREE_UNDEFINED
            if is_leaf:
                if is_regressor:
                    value = tree_.value[right_child_id][0][0]
                else:
                    value = tree_.value[right_child_id][0][1] / np.sum(tree_.value[right_child_id][0]) if np.sum(tree_.value[right_child_id][0]) > 0 else 0
                tail = " *\n"
            else: # Not a leaf, use parent's value
                if is_regressor:
                    value = tree_.value[node_id][0][0]
                else:
                    value = tree_.value[node_id][0][1] / np.sum(tree_.value[node_id][0]) if np.sum(tree_.value[node_id][0]) > 0 else 0
                tail = "\n"
            
            tree_string_parts.append(f"{indent}{cnt}) {feature_name} {sign} {threshold:.6f} {n_samples} {impurity:.4f} {value:.6f}{tail}")
            if not is_leaf:
                recurse(right_child_id, depth + 1)

        recurse(0, 1)
        strings.append("".join(tree_string_parts))
        
    return strings


print('Generating and exporting GEE tree strings...')
gee_start_time = time.time()

# Process classifier
print('\tProcessing classifier...')
classifier_trees = rf_to_gee_strings(final_classifier, predictor_all, model_type='classifier')
print(f'\tExporting {len(classifier_trees)} classifier trees to text file...')
with open(classifier_treestring_output, "w") as text_file:
    text_file.writelines(classifier_trees)

# Process regressor
print('\tProcessing regressor...')
regressor_trees = rf_to_gee_strings(final_regressor, predictor_all, model_type='regressor')
print(f'\tExporting {len(regressor_trees)} regressor trees to text file...')
with open(regressor_treestring_output, "w") as text_file:
    text_file.writelines(regressor_trees)

end_timing(gee_start_time)

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

    #### SETUP INNER DATA FOR THRESHOLD DETERMINATION
    print('\tCreating inner cross validation splits...')
    inner_results = pd.DataFrame()
    count = 1
    for train_idx, test_idx in inner_cv_splits.split(outer_train_iter, outer_train_iter[obs_pres[0]].astype('int32'), outer_train_iter[validation[0]].astype('int32')):
        train = outer_train_iter.iloc[train_idx].assign(inner_split_n=count)
        test = outer_train_iter.iloc[test_idx].assign(inner_split_n=count)

        # Train inner classifier
        inner_classifier = BalancedRandomForestClassifier(**classifier_params)
        inner_classifier.fit(train[predictor_all], train[obs_pres[0]])

        # Predict and store results
        probability = inner_classifier.predict_proba(test[predictor_all])
        test = test.assign(pred_abs=probability[:, 0], pred_pres=probability[:, 1])
        inner_results = pd.concat([inner_results, test], ignore_index=True)
        count += 1

    # Determine optimal threshold for this outer fold
    print('\tOptimizing classification threshold...')
    threshold, _, _, _, _ = determine_optimal_threshold(inner_results[pred_pres[0]], inner_results[obs_pres[0]])
    threshold_list.append(threshold)

    #### CONDUCT OUTER CROSS VALIDATION
    # Train outer models
    print('\tTraining outer models...')
    X_class_outer = outer_train_iter[predictor_all]
    y_class_outer = outer_train_iter[obs_pres[0]]
    outer_classifier = BalancedRandomForestClassifier(**classifier_params)
    outer_classifier.fit(X_class_outer, y_class_outer)

    regress_outer = outer_train_iter[outer_train_iter[obs_cover[0]] >= 0]
    X_regress_outer = regress_outer[predictor_all]
    y_regress_outer = regress_outer[obs_cover[0]]
    outer_regressor = RandomForestRegressor(**regressor_params)
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
y_class_obs_pres = valid_results[obs_pres[0]]
y_class_pred_dist = valid_results['distribution']
y_class_pred_prob = valid_results[pred_pres[0]]
y_regress_obs = valid_results[obs_cover[0]]
y_regress_pred = valid_results[prediction[0]]

# Calculate metrics
tn, fp, fn, tp = confusion_matrix(y_class_obs_pres, y_class_pred_dist).ravel()
validation_auc = roc_auc_score(y_class_obs_pres, y_class_pred_prob)
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

