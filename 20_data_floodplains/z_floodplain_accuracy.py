# Import packages
import numpy as np
import os
import pandas as pd
from akutils import test_presence_threshold
from sklearn.metrics import confusion_matrix
from sklearn.metrics import roc_auc_score

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work/Projects/VegetationEcology/AKVEG_Map/Data/Data_Input/floodplains'

# Define input files
floodplain_input = os.path.join(drive, root_folder, 'floodplain_results.xlsx')

#### DEFINE FUNCTIONS
####____________________________________________________

def determine_optimal_threshold(predict_probability, y_test):
    """
    Description: determines the threshold value that minimizes the absolute value difference between sensitivity and specificity to one percentage.
    Inputs: 'predict_probability' -- the predicted probability values
            'y_test' -- the observed binary values
    Returned Value: Returns the optimal threshold value and the sensitivity, specificity, auc, and accuracy of the optimal threshold value
    Preconditions: requires existing probability predictions and binary responses of the same shape
    """

    # Import packages
    import numpy as np

    # Iterate through numbers between 0 and 100 to output a list of sensitivity and specificity values per threshold number
    i = 1
    sensitivity_list = []
    specificity_list = []
    while i <= 100:
        sensitivity, specificity, auc, accuracy = test_presence_threshold(predict_probability, i, y_test)
        sensitivity_list.append(sensitivity)
        specificity_list.append(specificity)
        i = i + 1

    # Calculate a list of absolute value difference between sensitivity and specificity and find the optimal threshold
    difference_list = [np.absolute(a - b) for a, b in zip(sensitivity_list, specificity_list)]
    value, threshold = min((value, threshold) for (threshold, value) in enumerate(difference_list))

    # Calculate the performance of the optimal threshold
    sensitivity, specificity, auc, accuracy = test_presence_threshold(predict_probability, threshold, y_test)

    # Return the optimal threshold and the performance metrics of the optimal threshold
    return threshold, sensitivity, specificity, auc, accuracy

#### DETERMINE THRESHOLD AND ACCURACY
####____________________________________________________

# Read input data
floodplain_data = pd.read_excel(floodplain_input, sheet_name='points')

# Format data
floodplain_data['observe'] = np.where(floodplain_data['CID'] == 1, 0, 1)
floodplain_data = floodplain_data.dropna()

# Determine optimal threshold for this outer fold
print('Optimizing classification threshold...')
threshold, _, _, _, _ = determine_optimal_threshold(
    floodplain_data['predict_prob'],
    floodplain_data['observe']
)

# Apply threshold to prediction probability
floodplain_data['predict'] = np.where(floodplain_data['predict_prob'] >= threshold, 1, 0)

# Partition observed vs predicted for metrics
y_classify_observed = floodplain_data['observe']
y_classify_predicted = floodplain_data['predict']
y_classify_probability = floodplain_data['predict_prob']

# Calculate metrics
true_negative, false_positive, false_negative, true_positive = confusion_matrix(
    y_classify_observed, y_classify_predicted
).ravel()
validation_auc = roc_auc_score(y_classify_observed, y_classify_probability)
validation_accuracy = ((true_negative + true_positive) /
                       (true_negative + false_positive + false_negative + true_positive))

# Print final validation scores
print('\n--- Final Validation Metrics ---')
print(f'Threshold: {threshold}')
print(f'AUC: {round(validation_auc, 3)}')
print(f'Accuracy: {round(validation_accuracy * 100, 1)}%')
