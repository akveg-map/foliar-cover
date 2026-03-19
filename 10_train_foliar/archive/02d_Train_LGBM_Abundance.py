# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Train LightGBM abundance model
# Author: Timm Nawrocki
# Last Updated: 2024-11-24
# Usage: Must be executed in an Anaconda Python 3.12+ installation.
# Description: "Train LightGBM abundance model" trains and saves a LightGBM classifier and regressor for use in prediction.
# ---------------------------------------------------------------------------

# Define model targets
group = 'alnus'
round_date = 'round_20241124'

# Import packages
import os
import pandas as pd
import time
from akutils import *
from sklearn.utils import shuffle
from sklearn.model_selection import StratifiedGroupKFold
from lightgbm import LGBMClassifier
from lightgbm import LGBMRegressor
import joblib

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'D:/'
root_folder = 'ACCS_Work/Projects/VegetationEcology/AKVEG_Map/Data'

# Define folder structure
extract_folder = os.path.join(drive, root_folder, 'Data_Input/extract_data')
species_folder = os.path.join(drive, root_folder, 'Data_Input/species_data')
output_folder = os.path.join(drive, root_folder, 'Data_Output/model_results', round_date, group)
if os.path.exists(output_folder) == 0:
    os.mkdir(output_folder)

# Define input files
covariate_input = os.path.join(extract_folder, 'AKVEG_Sites_Covariates_3338.csv')
species_input = os.path.join(species_folder, f'cover_{group}_3338.csv')

# Define output files
threshold_output = os.path.join(output_folder, f'{group}_threshold_final.txt')
classifier_output = os.path.join(output_folder, f'{group}_classifier.joblib')
regressor_output = os.path.join(output_folder, f'{group}_regressor.joblib')

# Define variable sets
validation = ['valid']
predictor_all = ['summer', 'january', 'precip',
                 'coast', 'stream', 'river', 'wetness',
                 'elevation', 'exposure', 'heatload', 'position',
                 'aspect', 'relief', 'roughness', 'slope',
                 's1_1_vha', 's1_1_vhd', 's1_1_vva', 's1_1_vvd',
                 's1_2_vha', 's1_2_vhd', 's1_2_vva', 's1_2_vvd',
                 's1_3_vha', 's1_3_vhd', 's1_3_vva', 's1_3_vvd',
                 's2_1_blue', 's2_1_green', 's2_1_red', 's2_1_redge1', 's2_1_redge2',
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
obs_pres = ['presence']
obs_cover = ['cvr_pct']
retain_variables = ['st_vst'] + validation
all_variables = retain_variables + predictor_all + obs_pres + obs_cover
outer_split = ['outer_split_n']
inner_split = ['inner_split_n']
pred_abs = ['pred_abs']
pred_pres = ['pred_pres']
pred_bin = ['pred_bin']
pred_cover = ['pred_cover']
prediction = ['prediction']
inner_columns = all_variables + pred_abs + pred_pres + inner_split
outer_columns = all_variables + pred_abs + pred_pres + pred_cover + pred_bin + outer_split

# Define cross validation methods
inner_cv_splits = StratifiedGroupKFold(n_splits=10)

#### PREPARE INPUT DATA
####____________________________________________________

# Read input data to data frames
print('Loading input data...')
iteration_start = time.time()
covariate_data = pd.read_csv(covariate_input)
covariate_data = foliar_cover_predictors(covariate_data, predictor_all)
species_data = pd.read_csv(species_input)[['st_vst', 'cvr_pct', 'presence', 'valid']]

# Create an inner join of species and covariate data
input_data = species_data.merge(covariate_data, how='inner', on='st_vst')

# Create empty lists to store threshold and performance metrics
auc_list = []
accuracy_list = []
classifier_list = []

# Shuffle data
shuffled_data = shuffle(input_data, random_state=314).copy()

# Create an empty data frame to store the outer test results
outer_results = pd.DataFrame(columns=outer_columns)
end_timing(iteration_start)

#### SETUP INNER DATA
####____________________________________________________
print('Creating inner cross validation splits...')

# Create an empty data frame to store the inner cross validation splits
inner_train = pd.DataFrame(columns=all_variables + inner_split)
inner_test = pd.DataFrame(columns=all_variables + inner_split)

# Create an empty data frame to store the inner test results
inner_results = pd.DataFrame(columns=all_variables + pred_abs + pred_pres + ['inner_cv_split_n'])

# Create inner cross validation splits
count = 1
for train_index, test_index in inner_cv_splits.split(shuffled_data,
                                                     shuffled_data[obs_pres[0]].astype('int32'),
                                                     shuffled_data[validation[0]].astype('int32')):
    # Split the data into train and test partitions
    train = shuffled_data.iloc[train_index]
    test = shuffled_data.iloc[test_index]
    # Insert iteration to train
    train = train.assign(inner_split_n=count)
    # Insert iteration to test
    test = test.assign(inner_split_n=count)
    # Append to data frames
    inner_train = pd.concat([inner_train if not inner_train.empty else None,
                             train],
                            axis=0)
    inner_test = pd.concat([inner_test if not inner_test.empty else None,
                            test],
                           axis=0)
    # Increase counter
    count += 1
inner_cv_length = count - 1

# Reset indices
inner_train = inner_train.reset_index()
inner_test = inner_test.reset_index()

#### CONDUCT CLASSIFIER OPTIMIZATION
####____________________________________________________

print('Optimizing classifier parameters...')

# Optimize classifier
classifier_params = optimize_lgbmclassifier(init_points=30,
                                            n_iter=70,
                                            data=shuffled_data,
                                            all_variables=all_variables,
                                            predictor_all=predictor_all,
                                            target_field=obs_pres,
                                            stratify_field=obs_pres,
                                            group_field=validation)

#### CONDUCT INNER REGRESSOR OPTIMIZATION
####____________________________________________________

print('Optimizing regressor parameters...')

# Optimize regressor
regressor_params = optimize_lgbmregressor(init_points=30,
                                          n_iter=70,
                                          data=shuffled_data,
                                          all_variables=all_variables,
                                          predictor_all=predictor_all,
                                          target_field=obs_cover,
                                          stratify_field=obs_pres,
                                          group_field=validation)

#### CONDUCT THRESHOLD DETERMINATION
####____________________________________________________

# Identify X and y train splits for the classifier
X_class_outer = shuffled_data[predictor_all].astype(float).copy()
y_class_outer = shuffled_data[obs_pres[0]].astype('int32').copy()
groups_outer = shuffled_data[validation[0]].astype('int32').copy()

# Identify X and y train splits for the regressor
X_regress_outer = shuffled_data[predictor_all].astype(float).copy()
y_regress_outer = shuffled_data[obs_cover[0]].astype(float).copy()

# Iterate through inner cross validation splits
inner_cv_i = 1
while inner_cv_i <= inner_cv_length:
    print(f'\tConducting inner cross validation iteration {inner_cv_i} of {inner_cv_length}...')
    inner_train_iteration = inner_train[inner_train[inner_split[0]] == inner_cv_i].copy()
    inner_test_iteration = inner_test[inner_test[inner_split[0]] == inner_cv_i].copy()

    # Identify X and y inner train and test splits
    X_class_inner = inner_train_iteration[predictor_all].astype(float).copy()
    y_class_inner = inner_train_iteration[obs_pres[0]].astype('int32').copy()
    X_test_inner = inner_test_iteration[predictor_all].astype(float).copy()

    # Train classifier on the inner train data
    print('\t\tTraining inner classifier...')
    inner_classifier = LGBMClassifier(
        boosting_type='gbdt',
        num_leaves=int(classifier_params['num_leaves']),
        max_depth=int(classifier_params['max_depth']),
        learning_rate=classifier_params['learning_rate'],
        n_estimators=int(classifier_params['n_estimators']),
        objective='binary',
        class_weight='balanced',
        min_split_gain=classifier_params['min_split_gain'],
        min_child_weight=classifier_params['min_child_weight'],
        min_child_samples=int(classifier_params['min_child_samples']),
        subsample=classifier_params['subsample'],
        subsample_freq=1,
        colsample_bytree=classifier_params['colsample_bytree'],
        reg_alpha=classifier_params['reg_alpha'],
        reg_lambda=classifier_params['reg_lambda'],
        n_jobs=2,
        importance_type='gain',
        verbosity=-1
    )
    inner_classifier.fit(X_class_inner, y_class_inner)

    # Predict inner test data
    print('\t\tPredicting inner cross-validation test data...')
    probability_inner = inner_classifier.predict_proba(X_test_inner)

    # Assign predicted values to inner test data frame
    inner_test_iteration = inner_test_iteration.assign(pred_abs=probability_inner[:, 0])
    inner_test_iteration = inner_test_iteration.assign(pred_pres=probability_inner[:, 1])

    # Add the test results to output data frame
    inner_results = pd.concat([inner_results if not inner_results.empty else None,
                               inner_test_iteration],
                              axis=0)

    # Increase n value
    inner_cv_i += 1

# Calculate the optimal threshold and performance of the presence-absence classification
print('\tOptimizing classification threshold...')
threshold, sensitivity, specificity, auc, accuracy = determine_optimal_threshold(
    inner_results[pred_pres[0]],
    inner_results[obs_pres[0]]
)

#### TRAIN FINAL MODELS
####____________________________________________________

# Train classifier on the outer train data
print('\tTraining outer classifier...')
final_classifier = LGBMClassifier(
    boosting_type='gbdt',
    num_leaves=int(classifier_params['num_leaves']),
    max_depth=int(classifier_params['max_depth']),
    learning_rate=classifier_params['learning_rate'],
    n_estimators=int(classifier_params['n_estimators']),
    objective='binary',
    class_weight='balanced',
    min_split_gain=classifier_params['min_split_gain'],
    min_child_weight=classifier_params['min_child_weight'],
    min_child_samples=int(classifier_params['min_child_samples']),
    subsample=classifier_params['subsample'],
    subsample_freq=1,
    colsample_bytree=classifier_params['colsample_bytree'],
    reg_alpha=classifier_params['reg_alpha'],
    reg_lambda=classifier_params['reg_lambda'],
    n_jobs=2,
    importance_type='gain',
    verbosity=-1
)
final_classifier.fit(X_class_outer, y_class_outer)

# Train regressor on the outer train data
print('\tTraining outer regressor...')
final_regressor = LGBMRegressor(
    boosting_type='gbdt',
    num_leaves=int(regressor_params['num_leaves']),
    max_depth=int(regressor_params['max_depth']),
    learning_rate=regressor_params['learning_rate'],
    n_estimators=int(regressor_params['n_estimators']),
    objective='regression',
    min_split_gain=regressor_params['min_split_gain'],
    min_child_weight=regressor_params['min_child_weight'],
    min_child_samples=int(regressor_params['min_child_samples']),
    subsample=regressor_params['subsample'],
    subsample_freq=1,
    colsample_bytree=regressor_params['colsample_bytree'],
    reg_alpha=regressor_params['reg_alpha'],
    reg_lambda=regressor_params['reg_lambda'],
    n_jobs=2,
    importance_type='gain',
    verbosity=-1
)
final_regressor.fit(X_regress_outer, y_regress_outer)

# Export final models
export_threshold = round(threshold, 5)
file = open(threshold_output, 'w')
file.write(str(export_threshold))
file.close()
joblib.dump(final_classifier, classifier_output)
joblib.dump(final_regressor, regressor_output)
