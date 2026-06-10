# ---------------------------------------------------------------------------
# Plot foliar cover performance individual
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Plot foliar cover performance individual" plots the performance of each foliar cover model in two panels for site scale and landscape scale results.
# ---------------------------------------------------------------------------

# Import libraries
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import os
import kaleido

# Initialize kaleido
kaleido.get_chrome_sync()

# Set round date
round_date = 'round_20241124'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work/Projects/VegetationEcology/AKVEG_Map'

# Define folder structure
data_folder = os.path.join(drive, root_folder,
                           'Data/Data_Output/model_results', round_date)
plot_folder = os.path.join(drive, root_folder,
                           'Documents/Manuscript_FoliarCover_FloristicGradients/appendix_s1/figures')

# Define indicators
indicators = ['alnus', 'betshr', 'bettre', 'brotre', 'dryas', 'dsalix', 'empnig', 'erivag',
              'mwcalama', 'ndsalix', 'nerishr', 'picgla', 'picmar', 'picsit', 'poptre',
              'populbt', 'rhoshr', 'rubspe', 'sphagn', 'tsumer', 'vaculi', 'vacvit', 'wetsed']

#### CREATE PLOTS
####____________________________________________________

# Create output plot for each indicator
for indicator in indicators:
    print(f'Creating plot for {indicator}...')

    # Define input files
    site_input = os.path.join(data_folder, indicator, indicator + '_results.csv')
    scaled_input = os.path.join(data_folder, indicator, indicator + '_scaled.csv')

    # Define output files
    html_output = os.path.join(plot_folder,
                               f'figure_performance_{indicator}.html')
    plot_output = os.path.join(plot_folder,
                               f'figure_performance_{indicator}.png')

    # Process performance data
    site_data = pd.read_csv(site_input)[['st_vst', 'cvr_pct', 'prediction']]
    scaled_data = pd.read_csv(scaled_input)

    # Define bin edges
    x_edges = np.linspace(0, 100, 21)
    y_edges = np.linspace(0, 100, 21)

    # Compute 2D histogram for site scale data
    hist, x_edges, y_edges = np.histogram2d(site_data['cvr_pct'], site_data['prediction'], bins=[x_edges, y_edges])
    hist_log = np.where(hist > 0, np.log1p(hist), np.nan)

    # Compute bin centers (for axis labels)
    x_centers = 0.5 * (x_edges[:-1] + x_edges[1:])
    y_centers = 0.5 * (y_edges[:-1] + y_edges[1:])

    # Build custom hover text showing original counts
    hover_text = [[f"Count: {int(hist[i, j])}" for j in range(hist.shape[1])] for i in range(hist.shape[0])]
    hover_text = np.array(hover_text).T  # Transpose to match heatmap orientation

    # Colorbar ticks: select log-space values
    log_tick_vals = [0, 1, 2, 3, 4, 5, 6, 8, 9, 10]  # log(1 + count)
    linear_tick_vals = [int(np.expm1(v)) for v in log_tick_vals]  # inverse of log1p
    linear_tick_vals = [0, 1, 5, 20, 50, 150, 400, 3000, 8000, 22000]  # Check against values calculated above

    # Create the heatmap
    site_plot = go.Figure(data=go.Heatmap(
        z=hist_log.T,
        x=x_centers,
        y=y_centers,
        text=hover_text,
        hoverinfo='text',
        colorscale='Viridis',
        colorbar=dict(
            title='Count',
            tickvals=log_tick_vals,
            ticktext=linear_tick_vals,
            x=-0.22,  # Move colorbar to the left
            xanchor='left'),
        zmin=np.nanmin(hist_log),
        zmax=np.nanmax(hist_log)
    ))

    # Create reference line shapes
    shapes = [
        dict(type="line", x0=0, y0=0, x1=100, y1=100, xref="x", yref="y",
             line=dict(color="white", dash="dash", width=1)),
        dict(type="line", x0=0, y0=0, x1=100, y1=100, xref="x2", yref="y2",
             line=dict(color="red", dash="dash", width=1))
    ]

    # Create axis label annotations
    annotations = [
        # X-axis label (bottom center)
        dict(text='Observed foliar cover %',
             x=0.5, y=-0.2, xref="paper", yref="paper",
             showarrow=False, font=dict(size=16)
             ),
        # Y-axis label (left center, rotated)
        dict(text='Predicted foliar cover %',
             x=-0.07, y=0.2, xref="paper", yref="paper",
             showarrow=False, textangle=-90, font=dict(size=16)
             ),
        # Subplot 1 title
        dict(text='Site-scale',
             x=-0, y=1.12, xref='paper', yref='paper',
             showarrow=False, font=dict(size=18)
             ),
        # Subplot 2 title
        dict(text='Landscape-scale',
             x=0.65, y=1.12, xref='paper', yref='paper',
             showarrow=False, font=dict(size=18)
             )
    ]

    # Create landscape plot
    scaled_plot = px.scatter(scaled_data,
                             x='mean_cvr_pct',
                             y='mean_prediction')

    # Create combined plot
    combined_plot = make_subplots(rows=1, cols=2,
                                  horizontal_spacing=0.1)
    for trace in site_plot.data:
        combined_plot.add_trace(trace, row=1, col=1)
    for trace in scaled_plot.data:
        trace.showlegend = False
        trace.marker.update(size=10, color='rgba(0,132,168,0.4)', line=dict(color='black', width=1))
        combined_plot.add_trace(trace, row=1, col=2)

    # Style the plot
    combined_plot.update_layout(
        template='plotly_white',
        title=dict(
            text='Observed versus predicted foliar cover at site and landscape scales',
            x=0.5,
            y=0.94,
            xanchor='center',  # extra bottom padding
        ),
        width=1000,
        height=500,
        showlegend=True,
        font = dict(size=18, color='black'),
        legend=dict(font=dict(size=16)),
        xaxis=dict(range=[0, 100], scaleanchor="y", tick0=0, dtick=10, tickfont=dict(size=16)),
        yaxis=dict(range=[0, 100], tick0=0, dtick=10, tickfont=dict(size=16)),
        xaxis2=dict(range=[0, 100], scaleanchor="y2", tick0=0, dtick=10, tickfont=dict(size=16)),
        yaxis2=dict(range=[0, 100], tick0=0, dtick=10, tickfont=dict(size=16)),
        shapes=shapes,
        annotations=annotations
    )

    # Export to HTML (interactive)
    combined_plot.write_html(html_output)

    # Remove title for PNG export
    combined_plot.update_layout(title=None)
    combined_plot.update_layout(margin=dict(t=50))

    # Export plot to PNG
    pio.write_image(combined_plot, plot_output, format='png', width=1000, height=500, scale=3)
