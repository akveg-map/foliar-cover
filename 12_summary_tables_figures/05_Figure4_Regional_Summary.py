# ---------------------------------------------------------------------------
# Plot regional summary
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Plot regional summary" plots the mean composition for each region.
# ---------------------------------------------------------------------------

# Import libraries
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats
from osgeo import gdal
from osgeo.gdalconst import GDT_Byte
from akutils import raster_bounds
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import os
import kaleido

# Configure GDAL
gdal.UseExceptions()

# Initialize kaleido
kaleido.get_chrome_sync()

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set round date
round_date = 'round_20241124'

# Define indicators
indicators = ['picsit', 'tsumer', 'picgla', 'picmar', 'bettre', 'populbt', 'poptre',
              'alnus', 'ndsalix', 'betshr', 'rubspe', 'rhoshr', 'vaculi', 'vacvit', 'nerishr', 'empnig',
              'dsalix', 'dryas', 'erivag', 'mwcalama', 'wetsed', 'sphagn']

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work/Projects/VegetationEcology/AKVEG_Map'

# Define folder structure
raster_folder = os.path.join(drive, root_folder, 'Data/Data_Output/data_package/version_2.0_20250103')
region_folder = os.path.join(drive, root_folder, 'Data/Data_Input/region_data')
output_folder = os.path.join(drive, root_folder, 'Documents/Manuscript_FoliarCover_FloristicGradients/figures')

# Define input file
region_input = os.path.join(region_folder, 'AlaskaYukon_Regions_v2.0_3338.shp')

# Define output files
count_output = os.path.join(output_folder, 'data', 'zonal_count_total.tif')
zonal_output = os.path.join(output_folder, 'Figure5_Regional_Summary.xlsx')
html_output = os.path.join(output_folder, 'Figure5_Regional_Summary.html')
plot_output = os.path.join(output_folder, 'Figure5_Regional_Summary.png')

#### CALCULATE ZONAL STATISTICS
####____________________________________________________

# Create regional summary table if it does not already exist
if os.path.exists(zonal_output) == 0:
    print('Creating regional summary table...')

    # Open region shapefile
    region_data = gpd.read_file(region_input)

    # Select regions with valid data
    region_data = region_data[region_data['region'] != 'North Pacific']

    # Create null array to store results
    count_data = None

    # For each indicator, calculate the zonal statistics
    for indicator in indicators:
        print(f'\tCalculating zonal statistics for {indicator}...')

        # Define raster input
        raster_input = os.path.join(raster_folder, indicator, f'{indicator}_10m_3338.tif')

        # Define raster output
        raster_output = os.path.join(output_folder, 'data', f'{indicator}_100m_3338.tif')

        # Reproject data
        area_bounds = raster_bounds(raster_input)
        raster_warp = gdal.Warp(raster_output,
                                raster_input,
                                srcSRS='EPSG:3338',
                                dstSRS='EPSG:3338',
                                outputType=GDT_Byte,
                                workingType=GDT_Byte,
                                xRes=100,
                                yRes=-100,
                                srcNodata=255,
                                dstNodata=255,
                                outputBounds=area_bounds,
                                resampleAlg='bilinear',
                                targetAlignedPixels=False,
                                creationOptions=['COMPRESS=LZW', 'BIGTIFF=YES'])
        raster_warp = None

        # Read raster data
        with rasterio.open(raster_output) as raster_open:
            ndval = raster_open.nodatavals[0]
            raster_data = raster_open.read(1).astype('float64')
            raster_data[raster_data == 255] = np.nan
            affine_transform = raster_open.transform
            export_profile = raster_open.profile

        # Add raster arrays
        if isinstance(count_data, np.ndarray) == False:
            count_data = raster_data
        else:
            count_data = count_data + raster_data

        # Calculate zonal statistics
        zonal_results = zonal_stats(region_data,
                                    raster_data,
                                    affine=affine_transform,
                                    stats=['sum'],
                                    nodata=np.nan,
                                    all_touched=True,
                                    geojson_out=False)

        # Join zonal results to data frame
        zonal_data = pd.DataFrame(zonal_results)
        region_data = pd.concat([region_data, zonal_data], axis=1).rename(columns={'sum': indicator})

    # Convert count data to vegetated presence-absence
    count_data[np.isnan(count_data)] = 0
    count_data = np.where(count_data > 0, 1, 0)

    # Calculate the sum of vegetated grid cells
    count_results = zonal_stats(region_data,
                                count_data,
                                affine=affine_transform,
                                stats=['sum'],
                                nodata=255,
                                all_touched=True,
                                geojson_out=False)

    # Export count data to raster
    print('Exporting count raster...')
    count_data = count_data.astype(np.uint8)
    with rasterio.open(
            count_output,
            'w',
            driver='GTiff',
            height=count_data.shape[0],
            width=count_data.shape[1],
            count=1,
            dtype=rasterio.uint8,
            crs='EPSG:3338',
            transform=affine_transform
    ) as dst:
        dst.write(count_data, 1)

    # Join count results to data frame
    print('Exporting regional summary to excel...')
    count_sum = pd.DataFrame(count_results)
    region_data = pd.concat([region_data, count_sum], axis=1)

    # Standardize indicator cover sums to region count sum
    region_data[indicators] = region_data[indicators].div(region_data['sum'], axis=0)

    # Export zonal summary
    (region_data
     .drop(columns=['geometry', 'Shape_Leng', 'Shape_Area', 'sum'])
     .to_excel(zonal_output, sheet_name='summary', index=False))

#### CREATE PLOT
####____________________________________________________

# Load regional summary data
print('Creating plot...')
summary_data = (pd.read_excel(zonal_output, sheet_name='summary')
                .drop(columns=['biome', 'wetland']))

# Replace indicator abbreviations with full names
summary_data = summary_data.rename(columns={'picsit': 'Sitka spruce',
                                            'tsumer': 'mountain hemlock',
                                            'picgla': 'white spruce',
                                            'picmar': 'black spruce',
                                            'bettre': 'birch trees',
                                            'populbt': 'poplar/cottonwood',
                                            'poptre': 'aspen',
                                            'alnus': 'alder shrubs',
                                            'ndsalix': 'willow non-dwarf shrubs',
                                            'betshr': 'birch shrubs',
                                            'rubspe': 'salmonberry',
                                            'rhoshr': 'Rhododendron shrubs',
                                            'vaculi': 'bog blueberry',
                                            'vacvit': 'lingonberry',
                                            'nerishr': 'needleleaf ericaceous shrubs',
                                            'empnig': 'crowberry',
                                            'dsalix': 'willow dwarf shrubs',
                                            'dryas': 'Dryas shrubs',
                                            'erivag': 'tussock cottongrass',
                                            'mwcalama': 'mesic-wet Calamagrostis',
                                            'wetsed': 'wetland sedges',
                                            'sphagn': 'Sphagnum mosses'})

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

# Convert the 'Day' column to Categorical with the custom order
summary_data['region'] = pd.Categorical(summary_data['region'], categories=custom_order, ordered=True)

# Sort the DataFrame by the 'Day' column
summary_data = (summary_data
                .sort_values(by='region')
                .set_index('region')
                .transpose()
                .round(1))

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
