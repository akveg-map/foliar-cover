# Import libraries
import pandas as pd
import plotly.express as px
import plotly.io as pio
import os
import kaleido

# Initialize kaleido
kaleido.get_chrome_sync()

# Set round date
round_date = 'round_20241124'

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
project_folder = os.path.join(drive, root_folder,
                           'Projects/VegetationEcology/AKVEG_Map')
data_folder = os.path.join(project_folder,
                           'Data/Data_Output/model_results', round_date)
plot_folder = os.path.join(project_folder,
                           'Documents/Manuscript_FoliarCover_FloristicGradients/appendix_s1/figures')

# Define indicators
indicators = ['alnus', 'betshr', 'bettre', 'brotre', 'dryas', 'dsalix', 'empnig', 'erivag',
              'mwcalama', 'ndsalix', 'nerishr', 'picgla', 'picmar', 'picsit', 'poptre',
              'populbt', 'rhoshr', 'rubspe', 'sphagn', 'tsumer', 'vaculi', 'vacvit', 'wetsed']

# Loop through indicators
for indicator in indicators:
    print(f'Creating plot for {indicator}...')

    # Define input data
    importance_input = os.path.join(data_folder, indicator, f'{indicator}_importances.csv')

    # Define output files
    importance_output = os.path.join(plot_folder, f'figure_importance_{indicator}.png')

    # Read importance data
    importance_data = pd.read_csv(importance_input)

    #### PROCESS CLASSIFIER DATA
    ####____________________________________________________

    # Create empty dataframe to store results
    classifier_data = pd.DataFrame(columns=importance_data.columns)

    # Standardize importances per outer cv iteration
    outer_cv_i = 1
    while outer_cv_i <= 10:
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

        # Increase count
        outer_cv_i += 1

    # Group by covariate and calculate statistics
    classifier_data = (classifier_data
                       .groupby('covariate')['importance']
                       .agg(['mean', 'std'])
                       .reset_index())
    classifier_data.rename(columns={'mean': 'importance_mean', 'std': 'importance_std'}, inplace=True)

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
    outer_cv_i = 1
    while outer_cv_i <= 10:
        # Select classifier importances for iteration
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

        # Increase count
        outer_cv_i += 1

    # Group by covariate and calculate statistics
    regressor_data = (regressor_data
                       .groupby('covariate')['importance']
                       .agg(['mean', 'std'])
                       .reset_index())
    regressor_data.rename(columns={'mean': 'importance_mean', 'std': 'importance_std'}, inplace=True)

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

    # Customize Layout to match ggplot style
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

    # Update error bar style to be black and thinner
    importance_plot.update_traces(error_y=dict(color='#000000', thickness=1.5, width=3))

    # Sort X-axis by descending value (mimicking reorder)
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
