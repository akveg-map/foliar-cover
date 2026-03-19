# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Train and validate random forest abundance model
# Author: Timm Nawrocki, Matt Macander
# Last Updated: 2026-02-26
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Train and validate random forest abundance model" trains, exports, and validates a random forest classifier and regressor. The model validation accounts for spatial autocorrelation by grouping in 100 km blocks.
# ---------------------------------------------------------------------------

# Define model targets
group = 'wetforb'
version_date = '20260212'
presence_threshold = 3
predictor_names = ['clim', 'topo', 's1', 's2', 'emb']

# Import packages
import numpy as np
import os
import pandas as pd
import time
import joblib
from akutils import *
from sklearn.utils import shuffle
from sklearn.model_selection import StratifiedGroupKFold
from imblearn.ensemble import BalancedRandomForestClassifier
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import confusion_matrix
from sklearn.metrics import roc_auc_score
from sklearn.metrics import mean_squared_error
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import r2_score

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work/Projects/VegetationEcology/AKVEG_Map/Data'

# Define folder structure
site_folder = os.path.join(drive, root_folder,
                              f'Data_Input/site_data/version_{version_date}')
output_folder = os.path.join(drive, root_folder,
                             f'Data_Output/model_results/version_{version_date}/{group}')
if os.path.exists(output_folder) == 0:
    os.mkdir(output_folder)

# Define input files
covariate_input = os.path.join(site_folder, 'akveg_site_visit_covariates.csv')

# Define output files for final model
threshold_output = os.path.join(output_folder, f'{group}_threshold_final.txt')
classifier_output = os.path.join(output_folder, f'{group}_classifier.joblib')
regressor_output = os.path.join(output_folder, f'{group}_regressor.joblib')
classifier_treestring_output = os.path.join(output_folder, f'{group}_classifier_treestring.txt')
regressor_treestring_output = os.path.join(output_folder, f'{group}_regressor_treestring.txt')

# Define output files for validation results
results_output = os.path.join(output_folder, f'{group}_results.csv')
importance_output = os.path.join(output_folder, f'{group}_importances.csv')
threshold_output_mean = os.path.join(output_folder, f'{group}_threshold_mean.txt')
auc_output = os.path.join(output_folder, f'{group}_auc.txt')
acc_output = os.path.join(output_folder, f'{group}_acc.txt')
rscore_output = os.path.join(output_folder, f'{group}_r2.txt')
rmse_output = os.path.join(output_folder, f'{group}_rmse.txt')
mae_output = os.path.join(output_folder, f'{group}_mae.txt')

# Define covariate sets
validation = ['valid']
predictor_clim = ['summer', 'january', 'precip']
predictor_s1 = ['s1_1_vha', 's1_1_vhd', 's1_1_vva', 's1_1_vvd',
                's1_2_vha', 's1_2_vhd', 's1_2_vva', 's1_2_vvd',
                's1_3_vha', 's1_3_vhd', 's1_3_vva', 's1_3_vvd']
predictor_s2 = [f's2_{i}_{band}' for i in range(1, 6) for band in
                ['blue', 'green', 'red', 'redge1', 'redge2', 'redge3', 'nir',
                 'redge4', 'swir1', 'swir2', 'nbr', 'ngrdi', 'ndmi', 'ndsi',
                 'ndvi', 'ndwi']]
predictor_topo = ['coast', 'stream', 'river', 'wetness',
                  'elevation', 'exposure', 'heatload', 'position',
                  'aspect', 'relief', 'roughness', 'slope']
predictor_emb = ['A' + str(i).zfill(2) for i in range(64)]

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
obs_cover = ['cover_percent']
retain_variables = ['site_visit_code'] + validation
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
classifier_params = {'n_estimators': 10,
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
                     'n_jobs': 2,
                     'random_state': 314}

# Create a standardized parameter set for a random forest classifier
regressor_params = {'n_estimators': 10,
                    'criterion': 'poisson',
                    'max_depth': None,
                    'min_samples_split': 2,
                    'min_samples_leaf': 1,
                    'min_weight_fraction_leaf': 0,
                    'max_features': 'sqrt',
                    'bootstrap': True,
                    'oob_score': False,
                    'warm_start': True,
                    'n_jobs': 2,
                    'random_state': 314}

# Define cross validation methods
outer_cv_splits = StratifiedGroupKFold(n_splits=10)
inner_cv_splits = StratifiedGroupKFold(n_splits=10)

#### PREPARE INPUT DATA
####____________________________________________________

# Read input data to data frames
print('Loading input data...')
start_time = time.time()
input_data = pd.read_csv(covariate_input).rename(
    columns={group: 'cover_percent'})

# Filter the input data to include valid data only
input_data = input_data[input_data['cover_percent'] >= 0].copy()

# Threshold the presence-absence data
input_data['presence'] = np.where(input_data['cover_percent'] >= presence_threshold, 1, 0)

# Shuffle data
shuffled_data = shuffle(input_data, random_state=314).copy()
end_timing(start_time)

# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# PART 1: TRAIN FINAL MODEL ON FULL DATASET
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #

print('\n' + '=' * 50)
print('PART 1: TRAINING FINAL MODEL')
print('=' * 50)

#### DETERMINE FINAL CLASSIFICATION THRESHOLD
####____________________________________________________
print('Calculating optimal classification threshold...')
start_time = time.time()

# Create empty data frames to store results
inner_results_final = pd.DataFrame()

# Conduct model training in inner cross validation splits
count = 1
for train_index, test_index in inner_cv_splits.split(
        shuffled_data,
        shuffled_data[obs_pres[0]].astype('int32'),
        shuffled_data[validation[0]].astype('int32')):
    # Split the data into train and test partitions
    train = shuffled_data.iloc[train_index].assign(inner_split_n=count)
    test = shuffled_data.iloc[test_index].assign(inner_split_n=count)

    # Identify X and y inner train and test splits
    X_train = train[predictor_all].astype(float)
    y_class = train[obs_pres[0]].astype('int32')
    X_test = test[predictor_all].astype(float)

    # Train inner classifier
    inner_classifier = BalancedRandomForestClassifier(**classifier_params)
    inner_classifier.fit(X_train, y_class)

    # Predict and store results
    probability = inner_classifier.predict_proba(X_test)
    test = test.assign(pred_abs=probability[:, 0], pred_pres=probability[:, 1])
    inner_results_final = pd.concat([inner_results_final, test], ignore_index=True)
    count += 1

# Calculate the optimal threshold
final_threshold, _, _, _, _ = determine_optimal_threshold(
    inner_results_final[pred_pres[0]],
    inner_results_final[obs_pres[0]]
)
end_timing(start_time)

#### TRAIN AND EXPORT FINAL MODELS
####____________________________________________________
print('Training and exporting final models...')
start_time = time.time()

# Prepare full dataset for training
X_train = shuffled_data[predictor_all].astype(float)
y_class = shuffled_data[obs_pres[0]].astype('int32')
y_regress = shuffled_data[obs_cover[0]].astype(float)

# Train final classifier
print('\tTraining final classifier...')
final_classifier = BalancedRandomForestClassifier(**classifier_params)
final_classifier.fit(X_train, y_class)

# Train final regressor
print('\tTraining final regressor...')
final_regressor = RandomForestRegressor(**regressor_params)
final_regressor.fit(X_train, y_regress)

# Export final models and threshold
print('\tExporting trained model results...')
export_threshold = round(final_threshold, 5)
with open(threshold_output, 'w') as file:
    file.write(str(export_threshold))
joblib.dump(final_classifier, classifier_output)
joblib.dump(final_regressor, regressor_output)

# Process classifier tree strings
classifier_trees = rf_to_gee_strings(final_classifier, predictor_all, model_type='classifier')
print(f'\tExporting {len(classifier_trees)} classifier trees to text file...')
with open(classifier_treestring_output, "w") as text_file:
    text_file.writelines(classifier_trees)

# Process regressor tree strings
regressor_trees = rf_to_gee_strings(final_regressor, predictor_all, model_type='regressor')
print(f'\tExporting {len(regressor_trees)} regressor trees to text file...')
with open(regressor_treestring_output, "w") as text_file:
    text_file.writelines(regressor_trees)

# Report progress
print(f'Optimal Threshold: {export_threshold}')
end_timing(start_time)

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

# Create empty data frames to store results
outer_train = pd.DataFrame()
outer_test = pd.DataFrame()
outer_results = pd.DataFrame()
importance_results = pd.DataFrame()
threshold_list = []

# Create outer cross validation splits
count = 1
for train_index, test_index in outer_cv_splits.split(
        shuffled_data,
        shuffled_data[obs_pres[0]].astype('int32'),
        shuffled_data[validation[0]].astype('int32')):
    # Split the data into train and test partitions
    train = shuffled_data.iloc[train_index].assign(outer_split_n=count)
    test = shuffled_data.iloc[test_index].assign(outer_split_n=count)
    # Append to data frames
    outer_train = pd.concat([outer_train, train], ignore_index=True)
    outer_test = pd.concat([outer_test, test], ignore_index=True)
    count += 1
outer_cv_length = count - 1
print(f'Created {outer_cv_length} outer cross-validation group splits.')
end_timing(start_time)

#### CONDUCT MODEL VALIDATION
####____________________________________________________

# Iterate through outer cross validation splits
for outer_cv_i in range(1, outer_cv_length + 1):
    print(f'Conducting outer CV iteration {outer_cv_i} of {outer_cv_length}...')
    iter_start_time = time.time()

    # Partition outer data for this iteration
    outer_train_iter = outer_train[outer_train[outer_split[0]] == outer_cv_i].copy()
    outer_test_iter = outer_test[outer_test[outer_split[0]] == outer_cv_i].copy()

    # Create empty data frames to store results
    inner_results = pd.DataFrame()

    # Conduct inner cross validation
    count = 1
    for train_index, test_index in inner_cv_splits.split(
            outer_train_iter,
            outer_train_iter[obs_pres[0]].astype('int32'),
            outer_train_iter[validation[0]].astype('int32')):
        # Split the data into train and test partitions
        train = outer_train_iter.iloc[train_index].assign(inner_split_n=count)
        test = outer_train_iter.iloc[test_index].assign(inner_split_n=count)

        # Identify X and y inner train and test splits
        X_train = train[predictor_all].astype(float)
        y_class = train[obs_pres[0]].astype('int32')
        X_test = test[predictor_all].astype(float)

        # Train inner classifier
        inner_classifier = BalancedRandomForestClassifier(**classifier_params)
        inner_classifier.fit(X_train, y_class)

        # Predict and store results
        probability = inner_classifier.predict_proba(X_test)
        test = test.assign(pred_abs=probability[:, 0], pred_pres=probability[:, 1])
        inner_results = pd.concat([inner_results, test], ignore_index=True)
        count += 1

    # Determine optimal threshold for this outer fold
    print('\tOptimizing classification threshold...')
    threshold, _, _, _, _ = determine_optimal_threshold(
        inner_results[pred_pres[0]],
        inner_results[obs_pres[0]]
    )
    threshold_list.append(threshold)

    # Identify X and y outer train splits
    X_train = outer_train_iter[predictor_all]
    y_class = outer_train_iter[obs_pres[0]]
    y_regress = outer_train_iter[obs_cover[0]]
    
    # Train outer classifier
    print('\tTraining outer classifier...')
    outer_classifier = BalancedRandomForestClassifier(**classifier_params)
    outer_classifier.fit(X_train, y_class)
    
    # Train outer regressor
    print('\tTraining outer regressor...')
    outer_regressor = RandomForestRegressor(**regressor_params)
    outer_regressor.fit(X_train, y_regress)

    # Harvest feature importances
    classifier_imp = pd.DataFrame({
        'covariate': X_train.columns,
        'importance': outer_classifier.feature_importances_,
        'component': 'classifier'
    })
    regressor_imp = pd.DataFrame({
        'covariate': X_train.columns,
        'importance': outer_regressor.feature_importances_,
        'component': 'regressor'
    })
    importance_data = (pd.concat([classifier_imp, regressor_imp], ignore_index=True)
                       .assign(outer_cv_i=outer_cv_i))
    importance_results = pd.concat([importance_results, importance_data], ignore_index=True)

    # Predict outer test
    print('\tPredicting outer test data...')
    X_test = outer_test_iter[predictor_all].astype(float)
    probability_outer = outer_classifier.predict_proba(X_test)
    cover_outer = outer_regressor.predict(X_test)

    # Assign predicted values to outer test data frame
    outer_test_iter = outer_test_iter.assign(
        pred_abs=probability_outer[:, 0],
        pred_pres=probability_outer[:, 1],
        pred_cover=cover_outer,
        pred_bin=(probability_outer[:, 1] >= threshold).astype(int)
    )
    outer_results = pd.concat([outer_results, outer_test_iter], ignore_index=True)
    end_timing(iter_start_time)

#### CALCULATE PERFORMANCE AND STORE VALIDATION RESULTS
####____________________________________________________
print('Calculating performance metrics and storing validation results...')
start_time = time.time()

# Create a composite prediction
outer_results[prediction[0]] = np.where(
    (outer_results[pred_bin[0]] == 1) & (outer_results[pred_cover[0]] >= presence_threshold),
    outer_results[pred_cover[0]], 0
)
outer_results['distribution'] = ((outer_results[pred_bin[0]] == 1)
                                 & (outer_results[pred_cover[0]] >= presence_threshold)).astype(int)

# Clean and restrict results
outer_results[prediction[0]] = np.clip(outer_results[prediction[0]], 0, 100)

# Partition observed vs predicted for metrics
y_classify_observed = outer_results[obs_pres[0]].astype('int32')
y_classify_predicted = outer_results['distribution'].astype('int32')
y_classify_probability = outer_results[pred_pres[0]].astype(float)
y_regress_observed = outer_results[obs_cover[0]].astype(float)
y_regress_predicted = outer_results[prediction[0]].astype(float)

# Calculate metrics
true_negative, false_positive, false_negative, true_positive = confusion_matrix(
    y_classify_observed, y_classify_predicted
).ravel()
validation_auc = roc_auc_score(y_classify_observed, y_classify_probability)
validation_accuracy = ((true_negative + true_positive) /
                       (true_negative + false_positive + false_negative + true_positive))
r_score = r2_score(y_regress_observed, y_regress_predicted)
mae = mean_absolute_error(y_regress_observed, y_regress_predicted)
rmse = np.sqrt(mean_squared_error(y_regress_observed, y_regress_predicted))

# Format metrics for export
export_auc = round(validation_auc, 3)
export_accuracy = round(validation_accuracy * 100, 1)
export_threshold_mean = round(np.mean(threshold_list), 5)
export_rscore = round(r_score, 3)
export_rmse = round(rmse, 1)
export_mae = round(mae, 1)

# Store output results
outer_results.to_csv(results_output, header=True, index=False, sep=',', encoding='utf-8')
importance_results.to_csv(importance_output, header=True, index=False, sep=',', encoding='utf-8')
metric_map = {
    auc_output: export_auc, acc_output: export_accuracy,
    threshold_output_mean: export_threshold_mean, rscore_output: export_rscore,
    rmse_output: export_rmse, mae_output: export_mae
}
for file_path, metric in metric_map.items():
    with open(file_path, 'w') as f:
        f.write(str(metric))

# Print final validation scores
print('\n--- Final Validation Metrics ---')
print(f'AUC: {export_auc}')
print(f'Accuracy: {export_accuracy}%')
print(f'Mean CV Threshold: {export_threshold_mean}')
print(f'R-squared: {export_rscore}')
print(f'RMSE: {export_rmse}')
print(f'MAE: {export_mae}')
end_timing(start_time)
