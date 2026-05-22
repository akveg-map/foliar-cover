# ---------------------------------------------------------------------------
# Plot characteristics of training and validation data
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Plot characteristics of training and validation data" plots stacked bar charts for the cover version and temporal range of data.
# ---------------------------------------------------------------------------

# Import libraries
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
import os
import kaleido

# Initialize kaleido
kaleido.get_chrome_sync()

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work/Projects/VegetationEcology/AKVEG_Map'

# Define folder structure
input_folder = os.path.join(drive, root_folder, 'Documents/Manuscript_FoliarCover_FloristicGradients/tables')
region_folder = os.path.join(drive, root_folder, 'Data/Data_Input/region_data')
output_folder = os.path.join(drive, root_folder, 'Documents/Manuscript_FoliarCover_FloristicGradients/figures')

# Define input file
site_input = os.path.join(input_folder, '00_Training_Data_Summary.xlsx')
region_input = os.path.join(region_folder, 'AlaskaYukon_Regions_v2.0_3338.shp')

# Define output files
html_output = os.path.join(output_folder, 'Figure3b_Training_Validation_Data.html')
plot_output = os.path.join(output_folder, 'Figure3b_Training_Validation_Data.png')

#### CREATE PLOT
####____________________________________________________

# Read region data to geopandas dataframe
region_data = gpd.read_file(region_input)[['region', 'geometry']]

# Read training data
site_visit_selected = pd.read_excel(site_input, sheet_name='data')

# Create geometry for site visits
geometry = [Point(xy) for xy in zip(site_visit_selected['longitude_dd'], site_visit_selected['latitude_dd'])]
site_visit_selected = gpd.GeoDataFrame(site_visit_selected, geometry=geometry, crs='EPSG:4269')

# Reproject points to match region data
if site_visit_selected.crs != region_data.crs:
    site_visit_selected = site_visit_selected.to_crs(region_data.crs)

# Join regions to site visit data
site_visit_selected = gpd.sjoin(site_visit_selected, region_data, how="left", predicate="within")

# Define a function to assign the year interval
def assign_year(observe_year):
    if (observe_year >= 2000) & (observe_year < 2005):
        return '2000-2004'
    elif (observe_year >= 2005) & (observe_year < 2010):
        return '2005-2009'
    elif (observe_year >= 2010) & (observe_year < 2015):
        return '2010-2014'
    elif (observe_year >= 2015) & (observe_year < 2020):
        return '2015-2019'
    elif (observe_year >= 2020) & (observe_year < 2025):
        return '2020-2024'
    else:
        return 'omit'

# Apply function to create new column
site_visit_selected['year_interval'] = site_visit_selected['observe_year'].apply(assign_year)

# Summarize data by cover version
cover_data = site_visit_selected.groupby(['cover_version', 'region']).size().reset_index(name='count')

# Summarize data by year interval
year_data = site_visit_selected.groupby(['year_interval', 'region']).size().reset_index(name='count')

# Define custom fill
cover_colors = {
    'absolute': '#242B40',
    'top': '#E1E5EE'
}
cover_patterns = {
    'absolute': 'x',
    'top': '\\'
}
year_colors = {
    '2000-2004': '#E1E5EE',
    '2005-2009': '#B2B7C3',
    '2010-2014': '#838897',
    '2015-2019': '#535A6C',
    '2020-2024': '#242B40'
}

# Define x-axis ordering
category_order = ['Arctic Northern',
                  'Arctic Western',
                  'Aleutian-Kamchatka',
                  'Alaska Southwest',
                  'Alaska Western',
                  'Alaska-Yukon Northern',
                  'Alaska-Yukon Central',
                  'Alaska-Yukon Southern',
                  'Alaska Pacific']

# Create cover version plot
cover_plot = px.bar(cover_data,
                    x='region',
                    y='count',
                    color='cover_version',
                    color_discrete_map=cover_colors,
                    category_orders={'region': category_order})

# Replace colors with patterns
for trace in cover_plot.data:
    map_name = trace.name
    pattern_shape = cover_patterns.get(map_name, '')
    trace.marker.line.width = 1
    trace.marker.line.color = 'black'
    trace.marker.pattern.shape = pattern_shape
    trace.marker.pattern.fillmode = 'overlay'
    fg_color = 'white' if map_name == 'absolute' else 'black'
    trace.marker.pattern.fgcolor = fg_color
    trace.marker.pattern.size = 10

# Create year-range plot
year_plot = px.bar(year_data,
                   x='region',
                   y='count',
                   color='year_interval',
                   color_discrete_map=year_colors,
                   category_orders={'region': category_order})
year_plot.update_traces(marker_line_color='black', marker_line_width=1)

# Create combined plot
combined_plot = make_subplots(rows=1, cols=2,
                              subplot_titles=('b. Site visits by absolute or top cover',
                                              'c. Site visits by year'),
                              horizontal_spacing=0.1,
                              shared_yaxes=True)
for trace in cover_plot.data:
    trace.name = f'cover: {trace.name}'
    trace.legendgroup = 'group1'
    combined_plot.add_trace(trace, row=1, col=1)
for trace in year_plot.data:
    trace.name = f'year: {trace.name}'
    trace.legendgroup = 'group2'
    combined_plot.add_trace(trace, row=1, col=2)

# Style the plot
combined_plot.update_layout(
    barmode='stack',
    template='plotly_white',
    title=None,
    width=1000,
    height=700,
    showlegend=True,
    font=dict(size=18, color='black'),
    xaxis=dict(tickfont=dict(size=16, color='black')),
    yaxis=dict(tickfont=dict(size=16, color='black')),
    xaxis2=dict(tickfont=dict(size=16, color='black')),
    yaxis2=dict(tickfont=dict(size=16, color='black'))
)

# Rotate the x-axis labels
combined_plot.update_xaxes(tickangle=45)

# Update the sort order of the x-axes
combined_plot.update_xaxes(
    categoryorder='array',
    categoryarray=category_order,
    row=1, col=1
)
combined_plot.update_xaxes(
    categoryorder='array',
    categoryarray=category_order,
    row=1, col=2
)

# Align subplot titles to the left
subplot_domains = [0.0, 0.55]
for i, annotation in enumerate(combined_plot['layout']['annotations']):
    if 'text' in annotation and annotation['text'].startswith(('b.', 'c.')):
        annotation['xanchor'] = 'left'
        annotation['x'] = subplot_domains[i] + 0.01

# Increase the font size of the subplot titles
combined_plot.update_annotations(font=dict(size=20, color='black'))

# Add annotations for x and y titles
combined_plot.add_annotation(
    xref='x domain',
    yref='y domain',
    x=0,
    y=-0.2,
    text='Region',
    showarrow=False,
    xanchor="center",
    yanchor="top",
    font=dict(size=20, color='black')
)

combined_plot.add_annotation(
    xref='x domain',
    yref='y domain',
    x=-0.18,
    y=0.5,
    text='Site visit count',
    showarrow=False,
    xanchor="right",
    yanchor="middle",
    textangle=-90,
    font=dict(size=20, color='black')
)

# Export to HTML (interactive) and PNG (publication)
combined_plot.write_html(html_output)
pio.write_image(combined_plot, plot_output, width=1000, height=700, scale=10)
