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
arctic_list = ['Arctic Coastal Plain', 'Arctic Foothills & Mountains', 'Seward Peninsula',
               'Bering Sea Islands', 'Alaska Peninsula', 'Kodiak Southwest', 'Southwest Mountains',
               'Nelchina Uplands']
treeless_list = ['Bristol Bay (non-forest)', 'Alaska Western (non-forest)', 'Yukon Flats (non-forest)',
                 'Eastern Interior (non-forest)', 'Denali North (non-forest)', 'Wrangell-Copper (non-forest)',
                 'Denali South (non-forest)', 'Kodiak Northeast (non-forest)',
                 'Pacific Mainland (non-forest)']
tree_list = ['Bristol Bay (forest)', 'Alaska Western (forest)', 'Alaska-Yukon Northwest', 'Yukon Flats (forest)',
             'Eastern Interior (forest)', 'Central Interior', 'Denali North (forest)',
             'Wrangell-Copper (forest)', 'Denali South (forest)', 'Cook Inlet', 'Kodiak Northeast (forest)',
             'Pacific Mainland (forest)']

#### CREATE PLOT
####____________________________________________________

# Read ordination results
performance_data = pd.read_excel(performance_input, sheet_name='Performance')
performance_data = performance_data.rename(columns={'scaled_ind': 'map1',
                                                    'scaled_akvwc': 'map2',
                                                    'scaled_lf': 'map3'})

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

# Create a sequential mapping dictionary from left-to-right, top-to-bottom
ordered_units = arctic_list + treeless_list + tree_list
sequential_id_map = {unit: str(i + 1) for i, unit in enumerate(ordered_units)}

# Apply the new sequential ID to the long dataframe
performance_long['plot_id_str'] = performance_long['unit_name'].map(sequential_id_map)

# Create category order lists for the x-axes based on the new IDs
arctic_ids = [sequential_id_map[name] for name in arctic_list if name in sequential_id_map]
treeless_ids = [sequential_id_map[name] for name in treeless_list if name in sequential_id_map]
tree_ids = [sequential_id_map[name] for name in tree_list if name in sequential_id_map]

# Split data into three groups
arctic_data = performance_long[(performance_long['unit_name'].isin(arctic_list))]
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

# Create Arctic plot
arctic_plot = px.bar(arctic_data,
                     x='plot_id_str',
                     y='performance',
                     color='map_name',
                     color_discrete_map=map_colors,
                     text='performance',
                     hover_data=['unit_name'],
                     category_orders={'plot_id_str': arctic_ids})

for trace in arctic_plot.data:
    map_name = trace.name
    pattern_shape = map_patterns.get(map_name, '')
    trace.marker.line.width = 1
    trace.marker.line.color = 'black'
    trace.marker.pattern.shape = pattern_shape
    trace.marker.pattern.fillmode = 'overlay'
    trace.marker.pattern.fgcolor = 'white' if map_name == 'AKVEG foliar cover' else 'black'
    trace.marker.pattern.size = 6
    trace.textposition = 'outside'
    trace.textfont = dict(size=14, color='black')

# Create treeless plot
treeless_plot = px.bar(treeless_data,
                       x='plot_id_str',
                       y='performance',
                       color='map_name',
                       color_discrete_map=map_colors,
                       text='performance',
                       hover_data=['unit_name'],
                       category_orders={'plot_id_str': treeless_ids})

for trace in treeless_plot.data:
    map_name = trace.name
    pattern_shape = map_patterns.get(map_name, '')
    trace.marker.line.width = 1
    trace.marker.line.color = 'black'
    trace.marker.pattern.shape = pattern_shape
    trace.marker.pattern.fillmode = 'overlay'
    trace.marker.pattern.fgcolor = 'white' if map_name == 'AKVEG foliar cover' else 'black'
    trace.marker.pattern.size = 6
    trace.textposition = 'outside'
    trace.textfont = dict(size=14, color='black')

# Create tree plot
tree_plot = px.bar(tree_data,
                   x='plot_id_str',
                   y='performance',
                   color='map_name',
                   color_discrete_map=map_colors,
                   text='performance',
                   hover_data=['unit_name'],
                   category_orders={'plot_id_str': tree_ids})

for trace in tree_plot.data:
    map_name = trace.name
    pattern_shape = map_patterns.get(map_name, '')
    trace.marker.line.width = 1
    trace.marker.line.color = 'black'
    trace.marker.pattern.shape = pattern_shape
    trace.marker.pattern.fillmode = 'overlay'
    trace.marker.pattern.fgcolor = 'white' if map_name == 'AKVEG foliar cover' else 'black'
    trace.marker.pattern.size = 6
    trace.textposition = 'outside'
    trace.textfont = dict(size=14, color='black')

# Create combined plot
combined_plot = make_subplots(rows=3, cols=1,
                              subplot_titles=('a. Treeless subregions',
                                              'b. Non-forest subregion units',
                                              'c. Forest subregion units'),
                              horizontal_spacing=0.1,
                              shared_yaxes=False)

for trace in arctic_plot.data:
    combined_plot.add_trace(trace, row=1, col=1)
for trace in treeless_plot.data:
    trace.showlegend = False
    combined_plot.add_trace(trace, row=2, col=1)
for trace in tree_plot.data:
    trace.showlegend = False
    combined_plot.add_trace(trace, row=3, col=1)

# Style the plot
combined_plot.update_layout(
    barmode='group',
    template='plotly_white',
    title=None,
    width=1000,
    height=1200,
    showlegend=True,
    font=dict(size=18, color='black'),
    margin=dict(r=100, t=100), # Create a right margin to absorb some of the subregion key

    # Updated ranges to 105
    xaxis=dict(tickfont=dict(size=16, color='black'), domain=[0.0, 0.667]),
    yaxis=dict(range=[0, 105], tick0=0, dtick=20, tickfont=dict(size=16, color='black'),
               title=dict(text='Relative performance %'), domain=[0.71, 1.0]),

    xaxis2=dict(tickfont=dict(size=16, color='black'), domain=[0.0, 0.75]),
    yaxis2=dict(range=[0, 105], tick0=0, dtick=20, tickfont=dict(size=16, color='black'),
                title=dict(text='Relative performance %'), domain=[0.355, 0.645]),

    xaxis3=dict(tickfont=dict(size=16, color='black'), domain=[0.0, 1.0]),
    yaxis3=dict(range=[0, 105], tick0=0, dtick=20, tickfont=dict(size=16, color='black'),
                title=dict(text='Relative performance %'), domain=[0.0, 0.29]),

    # Adjusted legend center to keep it in a single row
    legend=dict(orientation='h', yanchor='bottom', y=1.04, xanchor='center', x=0.45)
)

# Set x-axis labels to be straight
combined_plot.update_xaxes(tickangle=0)

# Update the sort order using the sequential lists
combined_plot.update_xaxes(categoryorder='array', categoryarray=arctic_ids, row=1, col=1)
combined_plot.update_xaxes(categoryorder='array', categoryarray=treeless_ids, row=2, col=1)
combined_plot.update_xaxes(categoryorder='array', categoryarray=tree_ids, row=3, col=1)

# Generate Text for the Custom "Subregion Key" Legend
arctic_text = "<br>".join(
    [f"{sequential_id_map[unit]}: {unit}" for unit in arctic_list if unit in sequential_id_map]
)
treeless_text = "<br>".join(
    [f"{sequential_id_map[unit]}: {unit.replace(' (non-forest)', '')}" for unit in treeless_list if unit in sequential_id_map]
)
tree_text = "<br>".join(
    [f"{sequential_id_map[unit]}: {unit.replace(' (forest)', '')}" for unit in tree_list if unit in sequential_id_map]
)

# Combine the sections using the spacer, AND wrap the entire block in a span to force the font size
legend_text = (
    "<span style='font-size: 18px;'><b>Subregion Key</b></span><br>"
    f"<span style='font-size: 16px;'>{arctic_text}<br>{treeless_text}<br>{tree_text}</span>"
)

# Add the Subregion Key to the right margin
combined_plot.add_annotation(
    text=legend_text,
    align='left',
    showarrow=False,
    xref='paper', yref='paper',
    x=1.02, y=1.0,
    xshift=-200,
    yshift=40,
    xanchor='left', yanchor='top',
    bgcolor='white', borderpad=10
)

# Align subplot titles to the left
subplot_domains = [0.0, 0.0, 0.0]
for i, annotation in enumerate(combined_plot['layout']['annotations']):
    if 'text' in annotation and annotation['text'].startswith(('a.', 'b.', 'c.')):
        annotation['xanchor'] = 'left'
        annotation['x'] = subplot_domains[i] + 0.01

# Move the titles higher to prevent overlapping
combined_plot.layout.annotations[1].y += 0.03
combined_plot.layout.annotations[2].y += 0.06

# Increase the font size of the subplot titles
combined_plot.update_annotations(font=dict(size=20, color='black'))

# Export to HTML (interactive) and PNG (publication)
combined_plot.write_html(html_output)
pio.write_image(combined_plot, plot_output, width=1000, height=1200, scale=10)