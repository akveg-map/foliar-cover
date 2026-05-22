# ---------------------------------------------------------------------------
# Plot foliar cover performance combined
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Plot foliar cover performance combined" plots the performance of all foliar cover models in two panels for site-scale and local-scale results.
# ---------------------------------------------------------------------------

# Import libraries
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
import os
import kaleido

# Initialize kaleido
kaleido.get_chrome_sync()

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set round date
round_date = 'round_20241124'

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work/Projects/VegetationEcology/AKVEG_Map'

# Define folder structure
model_folder = os.path.join(drive, root_folder, 'Data/Data_Output/model_results', round_date)
output_folder = os.path.join(drive, root_folder, 'Documents/Manuscript_FoliarCover_FloristicGradients/figures')

# Define input file
performance_input = os.path.join(model_folder, 'performance_table.csv')

# Define output files
html_output = os.path.join(output_folder, 'Figure4_Performance_Combined.html')
plot_output = os.path.join(output_folder, 'Figure4_Performance_Combined.png')

#### CREATE PLOT
####____________________________________________________

# Read performance data
performance_data = pd.read_csv(performance_input)

# Calculate standardized RMSE
performance_data['std_rmse_site'] = round(
  (performance_data['rmse_site']/performance_data['cover_mean']),
  2)
performance_data['std_rmse_scaled'] = round(
  (performance_data['rmse_scaled']/performance_data['cover_mean']),
  2)

# Create reference line shapes representing "good" model performance
shapes = [
    dict(type="line", x0=0.4, y0=0.6, x1=1, y1=0.8, xref="x", yref="y",
         line=dict(color="black", dash="dash", width=1)),
    dict(type="line", x0=0.4, y0=0.6, x1=0.2, y1=0, xref="x", yref="y",
         line=dict(color="black", dash="dash", width=1)),
    dict(type="line", x0=0.4, y0=0.6, x1=1, y1=0.8, xref="x2", yref="y2",
         line=dict(color="black", dash="dash", width=1)),
    dict(type="line", x0=0.4, y0=0.6, x1=0.2, y1=0, xref="x2", yref="y2",
         line=dict(color="black", dash="dash", width=1))
]

# Create site plot
site_plot = px.scatter(performance_data,
                       x='r2_site',
                       y='std_rmse_site',
                       custom_data=['indicator_name', 'rmse_site', 'cover_mean', 'n_presence'])
site_plot.update_traces(hovertemplate='%{customdata[0]}<br>' +
                                      'R squared: %{x}<br>' +
                                      'RMSE: %{customdata[1]}<br>' +
                                      'Mean Cover (>3%): %{customdata[2]}<br>' +
                                      'Sites ≥ 3%: %{customdata[3]}')

# Create scaled plot
scaled_plot = px.scatter(performance_data,
                         x='r2_scaled',
                         y='std_rmse_scaled',
                         custom_data=['indicator_name', 'rmse_scaled', 'cover_mean', 'n_grid'])
scaled_plot.update_traces(hovertemplate='%{customdata[0]}<br>' +
                                        'R squared: %{x}<br>' +
                                        'RMSE: %{customdata[1]}<br>' +
                                        'Mean Cover (>3%): %{customdata[2]}<br>' +
                                        'Grids ≥ 1%: %{customdata[3]}')

# Create combined plot
combined_plot = make_subplots(rows=1, cols=2,
                              subplot_titles=('a. Site scale', 'b. Local scale'),
                              x_title='R squared',
                              y_title='Standardized RMSE',
                              horizontal_spacing=0.1)
for trace in site_plot.data:
    trace.marker.update(size=10, color='rgba(68,101,137,0.5)', line=dict(color='black', width=1))
    combined_plot.add_trace(trace, row=1, col=1)
for trace in scaled_plot.data:
    trace.showlegend = False
    trace.marker.update(size=10, color='rgba(68,101,137,0.5)', line=dict(color='black', width=1))
    combined_plot.add_trace(trace, row=1, col=2)

# Create reference points representing perfect predictions
ref_point_site = px.scatter(x=[1], y=[0])
ref_point_site.update_traces(
    marker=dict(size=10, color='black', symbol='circle'),
    showlegend=False,
    hovertemplate='R squared: 1<br>' +
                  'RMSE: 0'
)
ref_point_scaled = px.scatter(x=[1], y=[0])
ref_point_scaled.update_traces(
    marker=dict(size=10, color='black', symbol='circle'),
    showlegend=False,
    hovertemplate='R squared: 1<br>' +
                  'RMSE: 0'
)

# Add reference points to the plots
for trace in ref_point_site.data:
    combined_plot.add_trace(trace, row=1, col=1)
for trace in ref_point_scaled.data:
    combined_plot.add_trace(trace, row=1, col=2)

# Style the plot
combined_plot.update_layout(
    template='plotly_white',
    title=None,
    width=1000,
    height=500,
    showlegend=False,
    font=dict(size=18, color='black'),
    xaxis=dict(range=[0.15, 1.05],
               #scaleanchor="y",
               tick0=0.2,
               dtick=0.2,
               tickfont=dict(size=16, color='black')
               ),
    yaxis=dict(range=[-0.05, 0.8],
               tick0=0.4,
               dtick=0.2,
               tickfont=dict(size=16, color='black')
               ),
    xaxis2=dict(range=[0.15, 1.05],
                #scaleanchor="y2",
                tick0=0.2,
                dtick=0.2,
                tickfont=dict(size=16, color='black')
                ),
    yaxis2=dict(range=[-0.05, 0.8],
                tick0=0.4,
                dtick=0.2,
                tickfont=dict(size=16, color='black')
                ),
    shapes=shapes
)

# Align subplot titles to the left
subplot_domains = [0.0, 0.55]
for i, annotation in enumerate(combined_plot['layout']['annotations']):
    if 'text' in annotation and annotation['text'].startswith(('a.', 'b.')):
        annotation['xanchor'] = 'left'
        annotation['x'] = subplot_domains[i] + 0.01

# Increase the font size of the x and y axis titles and subplot titles
combined_plot.update_annotations(font=dict(size=20, color='black'))

# Add labels for perfect predictions
combined_plot.add_annotation(
    x=0.99, y=0.02,
    xref="x", yref="y",
    text="Perfect prediction",
    showarrow=True,
    arrowhead=2,
    arrowwidth=2,
    arrowsize=1,
    ax=-15, ay=-30,
    font=dict(size=16, color='black')
    )
combined_plot.add_annotation(
    x=0.99, y=0.02,
    xref="x2", yref="y2",
    text="Perfect prediction",
    showarrow=True,
    arrowhead=2,
    arrowwidth=2,
    arrowsize=1,
    ax=-15, ay=-30,
    font=dict(size=16, color='black')
    )

# Export to HTML (interactive) and PNG (publication)
combined_plot.write_html(html_output)
pio.write_image(combined_plot, plot_output, width=1000, height=500, scale=10)
