# ---------------------------------------------------------------------------
# Compile and plot covariate importances
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-06-07
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Compile and plot covariate importances" standardizes covariate importances per diagnostic species set, model type (i.e., classifier or regressor), and outer cross-validation iteration. This script outputs summary plots and a single summary table.
# ---------------------------------------------------------------------------

# Import libraries
import pandas as pd
import plotly.express as px
import plotly.io as pio
import os
import kaleido

# Initialize kaleido
kaleido.get_chrome_sync()

# Set version date
version_date = '20260415'

# Define colors and patterns
plot_colors = {'classifier': "#36648B", 'regressor': "#53868B"}
plot_patterns = {
    'classifier': '.',
    'regressor': '\\'
}

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
input_folder = os.path.join(project_folder, f'Data/Data_Output/model_results/version_{version_date}')
output_folder = os.path.join(project_folder, f'Data/Data_Output/summary_results/version_{version_date}')
plots_folder = os.path.join(output_folder, 'plots')

# Define output files
covariate_output = os.path.join(output_folder, 'Covariate_Summary.csv')

# Define diagnostic species sets
diagnostic_sets = ['alnus', 'bderishr', 'beach', 'betshr', 'bettre', 'brotre',
                   'dryas', 'dsalix', 'empnig', 'erivag', 'feather', 'forb', 'gramin',
                   'halgra', 'lichen', 'mwcalama', 'ndsalix', 'neetre', 'nerishr',
                   'picgla', 'picmar', 'picsit', 'poptre', 'populbt', 'rhoshr', 'rubspe',
                   'sphagn', 'tsuhet', 'tsumer', 'vaculi', 'vacvit', 'wetforb', 'wetsed']

#### STANDARDIZE COVARIATE IMPORTANCES
####____________________________________________________

# Initialize list to store all standardized importances across all diagnostic species sets
importance_list = []

# Loop through diagnostic species sets
for diagnostic_set in diagnostic_sets:
    print(f'Standardizing importances for {diagnostic_set}...')

    # Define input data
    importance_input = os.path.join(input_folder, diagnostic_set, f'{diagnostic_set}_importances.csv')

    # Define output files
    importance_output = os.path.join(plots_folder, f'figure_importance_{diagnostic_set}.png')

    # Read importance data
    importance_data = pd.read_csv(importance_input)

    #### PROCESS CLASSIFIER DATA
    ####____________________________________________________

    # Create empty dataframe to store results
    classifier_data = pd.DataFrame(columns=importance_data.columns)

    # Standardize importances per outer cv iteration
    for outer_cv_i in range(1, 11):
        # Select classifier importances for iteration
        subset_data = importance_data[(importance_data['component'] == 'classifier')
                                      & (importance_data['outer_cv_i'] == outer_cv_i)].copy()

        # Determine maximum value
        max_importance = subset_data['importance'].max()

        # Calculate standardized importances
        subset_data['importance'] = subset_data['importance'] / max_importance

        # Add the test results to output data frame
        classifier_data = pd.concat([classifier_data if not classifier_data.empty else None,
                                     subset_data],
                                    axis=0)

    # Group by covariate and calculate statistics for plotting
    classifier_data = (classifier_data
                       .groupby('covariate')['importance']
                       .agg(['mean', 'std'])
                       .reset_index())
    classifier_data.rename(columns={'mean': 'importance_mean', 'std': 'importance_std'}, inplace=True)

    # Append classifier data to importance list
    classifier_export = classifier_data.copy()
    classifier_export['component'] = 'classifier'
    classifier_export['diagnostic_set'] = diagnostic_set
    importance_list.append(classifier_export)

    # Append identifier to covariate to distinguish classifier and regressor covariates
    classifier_data['covariate'] = classifier_data['covariate'] + ' '

    # Sort, take top 10, and tag component
    classifier_data = classifier_data.sort_values(by='importance_mean', ascending=False).head(10)
    classifier_data['Component'] = 'classifier'

    #### PROCESS REGRESSOR DATA
    ####____________________________________________________

    # Create empty dataframe to store results
    regressor_data = pd.DataFrame(columns=importance_data.columns)

    # Standardize importances per outer cv iteration
    for outer_cv_i in range(1, 11):
        # Select classifier importances for iteration (note: filtering for 'regressor' component)
        subset_data = importance_data[(importance_data['component'] == 'regressor')
                                      & (importance_data['outer_cv_i'] == outer_cv_i)].copy()

        # Determine maximum value
        max_importance = subset_data['importance'].max()

        # Calculate standardized importances
        subset_data['importance'] = subset_data['importance'] / max_importance

        # Add the test results to output data frame
        regressor_data = pd.concat([regressor_data if not regressor_data.empty else None,
                                     subset_data],
                                    axis=0)

    # Group by covariate and calculate statistics for plotting
    regressor_data = (regressor_data
                       .groupby('covariate')['importance']
                       .agg(['mean', 'std'])
                       .reset_index())
    regressor_data.rename(columns={'mean': 'importance_mean', 'std': 'importance_std'}, inplace=True)

    # Append regressor data to importance list
    regressor_export = regressor_data.copy()
    regressor_export['component'] = 'regressor'
    regressor_export['diagnostic_set'] = diagnostic_set
    importance_list.append(regressor_export)

    # Sort, take top 10, and tag component
    regressor_data = regressor_data.sort_values(by='importance_mean', ascending=False).head(10)
    regressor_data['Component'] = 'regressor'

    #### CREATE IMPORTANCE PLOT
    ####____________________________________________________

    # Combine data
    combined_data = pd.concat([classifier_data, regressor_data])

    # Create Plot
    importance_plot = px.bar(
        combined_data,
        x='covariate',
        y='importance_mean',
        color='Component',
        error_y='importance_std',
        #barmode='group',  # Groups bars side-by-side if they share a covariate
        color_discrete_map=plot_colors,
        template='plotly_white'
    )

    # Replace colors with patterns
    for trace in importance_plot.data:
        trace_name = trace.name
        pattern_shape = plot_patterns.get(trace_name, '')
        trace.marker.line.width = 1
        trace.marker.line.color = 'black'
        trace.marker.pattern.shape = pattern_shape
        trace.marker.pattern.fillmode = 'overlay'
        trace.marker.pattern.fgcolor = 'black'
        trace.marker.pattern.size = 6
        trace.textposition = 'outside'
        trace.textfont = dict(size=14, color = 'black')

    # Update layout
    importance_plot.update_layout(
        title=None,
        width=1000,
        height=500,
        showlegend = True,
        font = dict(size=18, color='black'),
        xaxis=dict(tickfont=dict(size=16, color='black'),
                   title=dict(text=None)),
        yaxis=dict(tickfont=dict(size=16, color='black'),
                   title=dict(text='Relative covariate importance (top 10)')),
        bargap=0.2,
        legend=dict(
            title=None,
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99
        )
    )

    # Rotate the x-axis labels
    importance_plot.update_xaxes(tickangle=45)

    # Update error bar style
    importance_plot.update_traces(error_y=dict(color='#000000', thickness=1.5, width=3))

    # Sort X-axis by descending value
    importance_plot.update_xaxes(categoryorder='total descending')

    # Export plot
    pio.write_image(
        importance_plot,
        importance_output,
        format='png',
        width=1000,
        height=500,
        scale=3
    )

#### EXPORT COVARIATE IMPORTANCE TABLE
####____________________________________________________

print('Compiling and exporting importance table...')
importance_data = pd.concat(importance_list, ignore_index=True)

# Format results
importance_data['importance_mean'] = importance_data['importance_mean'].round(2)
importance_data['importance_std'] = importance_data['importance_std'].round(2)
importance_data = importance_data[['diagnostic_set', 'component', 'covariate', 'importance_mean', 'importance_std']]

# Export importance table
importance_data.to_csv(covariate_output, index=False)
