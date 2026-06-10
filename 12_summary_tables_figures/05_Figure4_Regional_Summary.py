# ---------------------------------------------------------------------------
# Plot regional summary
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-05-30
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Plot regional summary" plots the mean composition for each region.
# ---------------------------------------------------------------------------

# Import packages
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats
from osgeo import gdal
from osgeo.gdalconst import GDT_Int8
from akutils import raster_bounds
import plotly.express as px
import plotly.io as pio
import os
import kaleido

# Configure GDAL
gdal.UseExceptions()

# Initialize kaleido
kaleido.get_chrome_sync()

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set version date
version_date = '20260415'

# Define diagnostic_sets
diagnostic_sets = ['picsit', 'tsumer', 'picgla', 'picmar', 'bettre', 'poptre',
                   'alnus', 'ndsalix', 'betshr', 'rubspe', 'bderishr', 'vaculi', 'nerishr',
                   'dsalix', 'dryas', 'erivag', 'mwcalama', 'wetsed', 'sphagn', 'lichen']

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
raster_folder = os.path.join(project_folder, f'Data_Output/rasters_final/version_{version_date}')
region_folder = os.path.join(project_folder, 'Data_Input/region_data')
output_folder = os.path.join(project_folder, f'Data_Output/summary_results/version_{version_date}')

# Define input file
region_input = os.path.join(region_folder, 'AlaskaYukon_USNVC_ZonesRegions_v2p1_3338.shp')

# Define output files
count_output = os.path.join(output_folder, 'data', 'zonal_count_total.tif')
zonal_output = os.path.join(output_folder, 'data', 'Figure4_Regional_Summary.xlsx')
html_output = os.path.join(output_folder, 'Figure4_Regional_Summary.html')
plot_output = os.path.join(output_folder, 'Figure4_Regional_Summary.png')

#### CALCULATE ZONAL STATISTICS
####____________________________________________________

# Create regional summary table if it does not already exist
print('Creating regional summary table...')

# Open region shapefile
region_data = gpd.read_file(region_input)

# Select regions with valid data
region_data = region_data[region_data['region'] != 'North Pacific']

# Create null array to store results
count_data = None

# Calculate zonal statistics for each diagnostic species set
for diagnostic_set in diagnostic_sets:
    print(f'\tCalculating zonal statistics for {diagnostic_set}...')

    # Define raster input
    raster_input = os.path.join(raster_folder, f'{diagnostic_set}_Cvr_10m_3338.tif')

    # Define raster output
    raster_output = os.path.join(output_folder, 'data', f'{diagnostic_set}_100m_3338.tif')

    # Reproject the raster to 100 m resolution for zonal statistics
    if not os.path.exists(raster_output):
        area_bounds = raster_bounds(raster_input)
        warp_data = gdal.Warp(raster_output,
                              raster_input,
                              srcSRS='EPSG:3338',
                              dstSRS='EPSG:3338',
                              outputType=GDT_Int8,
                              workingType=GDT_Int8,
                              xRes=100,
                              yRes=-100,
                              srcNodata=-128,
                              dstNodata=-128,
                              outputBounds=area_bounds,
                              resampleAlg='average',
                              targetAlignedPixels=False,
                              creationOptions=['COMPRESS=LZW', 'BIGTIFF=YES'])
        warp_data = None # Release GDAL file lock

    # Read raster data
    with rasterio.open(raster_output) as raster_open:
        nodata_value = raster_open.nodatavals[0]
        raster_data = raster_open.read(1).astype('float64')
        raster_data[raster_data == -128] = np.nan
        affine_transform = raster_open.transform
        export_profile = raster_open.profile

    # Safely add raster arrays without propagating NaNs
    if count_data is None:
        count_data = np.nan_to_num(raster_data, nan=0.0)
    else:
        count_data += np.nan_to_num(raster_data, nan=0.0)

    # Calculate zonal statistics
    zonal_results = zonal_stats(region_data,
                                raster_data,
                                affine=affine_transform,
                                stats=['sum'],
                                nodata=np.nan,
                                all_touched=True,
                                geojson_out=False)

    # Directly assign the 'sum' list to a new column
    region_data[diagnostic_set] = [feature['sum'] for feature in zonal_results]

# Convert count data to vegetated presence-absence
count_data = np.where(count_data > 0, 1, 0)

# Calculate the sum of vegetated grid cells
count_results = zonal_stats(region_data,
                            count_data,
                            affine=affine_transform,
                            stats=['sum'],
                            nodata=-128,
                            all_touched=True,
                            geojson_out=False)

# Export count data to raster
print('Exporting count raster...')
count_data = count_data.astype(np.uint8)
with rasterio.open(count_output,
                   'w',
                   driver='GTiff',
                   height=count_data.shape[0],
                   width=count_data.shape[1],
                   count=1,
                   dtype=rasterio.int8,
                   crs='EPSG:3338',
                   transform=affine_transform,
                   nodata=-128) as dst:
    dst.write(count_data, 1)

# Join count results to data frame using direct assignment
print('Exporting regional summary to excel...')
region_data['sum'] = [feature['sum'] for feature in count_results]

# Standardize diagnostic_set cover sums to region count sum
region_data[diagnostic_sets] = region_data[diagnostic_sets].div(region_data['sum'], axis=0)

# Export zonal summary
(region_data
 .drop(columns=['geometry', 'Shape_Leng', 'Shape_Area', 'sum'], errors='ignore')
 .to_excel(zonal_output, sheet_name='summary', index=False))

#### CREATE PLOT
####____________________________________________________

# Load regional summary data
print('Creating plot...')
summary_data = (pd.read_excel(zonal_output, sheet_name='summary')
                .drop(columns=['biome', 'zone', 'wetland'], errors='ignore'))

# Round summary data to one decimal
summary_data[diagnostic_sets] = summary_data[diagnostic_sets].round(1)

# Replace diagnostic_set abbreviations with full names
summary_data = summary_data.rename(columns={'picsit': 'Sitka spruce',
                                            'tsumer': 'mountain hemlock',
                                            'picgla': 'white spruce',
                                            'picmar': 'black spruce',
                                            'bettre': 'birch trees',
                                            'poptre': 'aspen',
                                            'alnus': 'alder shrubs',
                                            'ndsalix': 'willow shrubs',
                                            'betshr': 'birch shrubs',
                                            'rubspe': 'salmonberry',
                                            'bderishr': 'tall blueberries',
                                            'vaculi': 'bog blueberry',
                                            'nerishr': 'needleleaf ericaceous',
                                            'dsalix': 'willow dwarf shrubs',
                                            'dryas': 'Dryas shrubs',
                                            'erivag': 'tussock cottongrass',
                                            'mwcalama': 'mesic-wet Calamagrostis',
                                            'wetsed': 'wetland sedges',
                                            'sphagn': 'Sphagnum mosses',
                                            'lichen': 'lichens'})

# Define the custom order for regions
custom_order = ['Arctic Northern',
                'Arctic Western',
                'Aleutian-Kamchatka',
                'Alaska Southwest',
                'Alaska Western',
                'Alaska-Yukon Northern',
                'Alaska-Yukon Central',
                'Alaska-Yukon Southern',
                'Alaska Pacific']

# Convert the 'region' column to Categorical with the custom order
summary_data['region'] = pd.Categorical(summary_data['region'], categories=custom_order, ordered=True)

# Sort the DataFrame by the 'region' column
summary_data = (summary_data
                .sort_values(by='region')
                .set_index('region')
                .transpose())

# Clear the index and column axis names
summary_data = summary_data.rename_axis(index=None, columns=None)

# Create 2d histogram plot
summary_plot = px.imshow(
    summary_data,
    text_auto=True,
    x=summary_data.columns,
    y=summary_data.index,
    color_continuous_scale=[
        '#E1E5EE',
        '#B2B7C3',
        '#838897',
        '#535A6C',
        '#242B40'
    ]
)

# Prevent color blending
summary_plot.update_traces(zsmooth=False)

# Style the plot
summary_plot.update_layout(
    template='plotly_white',
    title=None,
    width=800,
    height=1000,
    showlegend=True,
    font=dict(size=18, color='black'),
    margin=dict(
        pad=10
    ),
    xaxis=dict(title='',
               tickangle=90,
               tickfont=dict(size=16, color='black'),
               scaleanchor=None),
    yaxis=dict(tickfont=dict(size=16, color='black'),
               scaleanchor=None)
)

# Export to HTML (interactive) and PNG (publication)
summary_plot.write_html(html_output)
pio.write_image(summary_plot, plot_output, width=800, height=1000, scale=10)
