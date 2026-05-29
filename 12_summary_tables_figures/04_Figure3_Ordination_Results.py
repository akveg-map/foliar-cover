# ---------------------------------------------------------------------------
# Figure 3. Combined performance
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-05-28
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Figure 3. Combined performance" plots bar charts comparing the combined performance of three vegetation maps relative to the compositional variation partitioned among preliminary alliances.
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

# Set round date
version_date = '20260415'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
output_folder = os.path.join(project_folder, f'Data_Output/summary_results/version_{version_date}')

# Define input file
performance_input = os.path.join(output_folder, 'Table2_Clustering_Performance.xlsx')

# Define output files
html_output = os.path.join(output_folder, 'Figure3_Combined_Performance.html')
plot_output = os.path.join(output_folder, 'Figure3_Combined_Performance.png')

# Assign treeless and treed systems
treeless_list = ['Arctic Coastal Plain', 'Arctic Foothills & Mountains', 'Seward Peninsula',
                 'Bering Sea Islands', 'Alaska Peninsula', 'Kodiak Southwest', 'Southwest Mountains',
                 'Bristol Bay Non-forest', 'Alaska Western Non-forest', 'Yukon Flats Non-forest',
                 'Eastern Interior Non-forest', 'Denali North Non-forest', 'Wrangell-Copper Non-forest',
                 'Nelchina Uplands', 'Denali South Non-Forest', 'Kodiak Northeast Non-Forest',
                 'Pacific Mainland Non-forest']
tree_list = ['Bristol Bay Forest', 'Alaska Western Forest', 'Alaska-Yukon Northwest', 'Yukon Flats Forest',
             'Eastern Interior Forest', 'Central Interior', 'Denali North Forest', 'Wrangell-Tetlin',
             'Wrangell-Copper Forest', 'Denali South Forest', 'Cook Inlet', 'Kodiak Northeast Forest',
             'Pacific Mainland Forest']

#### CREATE PLOT
####____________________________________________________

# Read ordination results
performance_data = pd.read_excel(performance_input, sheet_name='summary')
performance_data['map1'] = performance_data['scaled_ind'] * 100
performance_data['map2'] = performance_data['scaled_akvwc'] * 100
performance_data['map3'] = performance_data['scaled_lf'] * 100

# Select columns
performance_data = performance_data[['unit_name', 'map1', 'map2', 'map3']]

# Add a row id column
performance_data = performance_data.reset_index().rename(columns={'index': 'id'})

# Pivot data to long form
performance_long = pd.wide_to_long(performance_data,
                                  ['map'],
                                  i='id',
                                  j='value',
                                  sep='').reset_index()

# Create function to assign vegetation map names
def assign_map(value):
    if value == 1:
        map_name = 'AKVEG foliar cover'
    elif value == 2:
        map_name = 'AKVWC (fine classes)'
    elif value == 3:
        map_name = 'LANDFIRE 2023 EVT'
    else:
        map_name = 'error'
    return map_name

# Apply function to create new column
performance_long['map_name'] = performance_long['value'].apply(assign_map)

# Rename performance value
performance_long = performance_long.rename(columns={'map': 'performance'})

# Round performance to nearest percentage
performance_long['performance'] = performance_long['performance'].round(0).astype(int)

# Split data into treeless and treed groups
treeless_data = performance_long[(performance_long['unit_name'].isin(treeless_list))]
tree_data = performance_long[(performance_long['unit_name'].isin(tree_list))]

# Define custom fill
map_colors = {
    'LANDFIRE 2023 EVT': '#ffffff',
    'AKVWC (fine classes)': '#ffffff',
    'AKVEG foliar cover': '#242B40'
}
map_patterns = {
    'LANDFIRE 2023 EVT': '.',
    'AKVWC (fine classes)': '\\',
    'AKVEG foliar cover': 'x'
}

# Create treeless plot
treeless_plot = px.bar(treeless_data,
                       x='unit_name',
                       y='performance',
                       color='map_name',
                       color_discrete_map=map_colors,
                       text='performance',
                       category_orders={'unit_name': treeless_list})

# Replace colors with patterns
for trace in treeless_plot.data:
    map_name = trace.name
    pattern_shape = map_patterns.get(map_name, '')
    trace.marker.line.width = 1
    trace.marker.line.color = 'black'
    trace.marker.pattern.shape = pattern_shape
    trace.marker.pattern.fillmode = 'overlay'
    fg_color = 'white' if map_name == 'AKVEG foliar cover' else 'black'
    trace.marker.pattern.fgcolor = fg_color
    trace.marker.pattern.size = 6
    trace.textposition = 'outside'
    trace.textfont = dict(size=14, color = 'black')

# Create tree plot
tree_plot = px.bar(tree_data,
                   x='unit_name',
                   y='performance',
                   color='map_name',
                   color_discrete_map=map_colors,
                   text='performance',
                   category_orders={'unit_name': tree_list})

# Replace colors with patterns
for trace in tree_plot.data:
    map_name = trace.name
    pattern_shape = map_patterns.get(map_name, '')
    trace.marker.line.width = 1
    trace.marker.line.color = 'black'
    trace.marker.pattern.shape = pattern_shape
    trace.marker.pattern.fillmode = 'overlay'
    fg_color = 'white' if map_name == 'AKVEG foliar cover' else 'black'
    trace.marker.pattern.fgcolor = fg_color
    trace.marker.pattern.size = 6
    trace.textposition = 'outside'
    trace.textfont = dict(size=14, color='black')

# Create combined plot
combined_plot = make_subplots(rows=2, cols=1,
                              subplot_titles=('a. Non-forest subregions and/or focal units',
                                              'b. Forest subregions and/or focal units'),
                              horizontal_spacing=0.1,
                              shared_yaxes=False)
for trace in treeless_plot.data:
    combined_plot.add_trace(trace, row=1, col=1)
for trace in tree_plot.data:
    trace.showlegend = False
    combined_plot.add_trace(trace, row=2, col=1)

# Style the plot
combined_plot.update_layout(
    barmode='group',
    template='plotly_white',
    title=None,
    width=1000,
    height=1100,
    showlegend=True,
    font=dict(size=18, color='black'),
    xaxis=dict(tickfont=dict(size=16, color='black'),
               domain=[0.0, 0.835]),
    yaxis=dict(range=[0, 102],
               tick0=0,
               dtick=20,
               tickfont=dict(size=16, color='black'),
               title=dict(text='Relative performance %'),
               domain=[0.6, 1.0]),
    xaxis2=dict(tickfont=dict(size=16, color='black'),
                domain=[0.0, 1.0]),
    yaxis2=dict(range=[0, 102],
                tick0=0,
                dtick=20,
                tickfont=dict(size=16, color='black'),
                title=dict(text='Relative performance %'),
                domain=[0.0, 0.4]),
    legend=dict(orientation='h',
                yanchor='bottom',
                y=1.05,
                xanchor='center',
                x=0.5)
)

# Rotate the x-axis labels
combined_plot.update_xaxes(tickangle=30)

# Update the sort order of the x-axes
combined_plot.update_xaxes(
    categoryorder='array',
    categoryarray=treeless_list,
    row=1, col=1
)
combined_plot.update_xaxes(
    categoryorder='array',
    categoryarray=tree_list,
    row=2, col=1
)

# Align subplot titles to the left
subplot_domains = [0.0, 0.0]
for i, annotation in enumerate(combined_plot['layout']['annotations']):
    if 'text' in annotation and annotation['text'].startswith(('a.', 'b.')):
        annotation['xanchor'] = 'left'
        annotation['x'] = subplot_domains[i] + 0.01

# Move the second subplot title higher
combined_plot.layout.annotations[1].y += 0.03

# Increase the font size of the subplot titles
combined_plot.update_annotations(font=dict(size=20, color='black'))

# Export to HTML (interactive) and PNG (publication)
combined_plot.write_html(html_output)
pio.write_image(combined_plot, plot_output, width=1000, height=1100, scale=10)
