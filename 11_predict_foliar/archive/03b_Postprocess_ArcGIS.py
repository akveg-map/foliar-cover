# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Convert raster grids to cloud-optimized geotiff
# Author: Timm Nawrocki
# Last Updated: 2025-01-03
# Usage: Must be executed in a Python 3.11+ installation with GDAL 3.9+.
# Description: "Convert raster grids to cloud-optimized geotiff" compiles raster grids and creates a cloud-optimized geotiff version.
# ---------------------------------------------------------------------------

# Define model targets
group = 'sphagn'
range_boolean = False
barren_boolean = True
water_boolean = True
round_date = 'round_20241124'
presence_threshold = 3

# Import packages
import os
import time
import arcpy
from arcpy.sa import Con
from arcpy.sa import ExtractByMask
from arcpy.sa import IsNull
from arcpy.sa import Raster
from akutils import *

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work/Projects/VegetationEcology/AKVEG_Map/Data'

# Define folder structure
postprocess_folder = os.path.join(drive, root_folder, 'Data_Input/postprocess_v20241230')
input_folder = os.path.join(drive, root_folder, 'Data_Output/rasters_gridded', round_date, group)
intermediate_folder = os.path.join(drive, root_folder, 'Data_Output/rasters_intermediate/round_20241124')
output_folder = os.path.join(drive, root_folder, 'Data_Output/rasters_final/round_20241124')
cog_folder = os.path.join(drive, root_folder, 'Data_Output/rasters_cog/round_20241124')
if os.path.exists(intermediate_folder) == 0:
    os.mkdir(intermediate_folder)
if os.path.exists(output_folder) == 0:
    os.mkdir(output_folder)
if os.path.exists(cog_folder) == 0:
    os.mkdir(cog_folder)

# Define work geodatabase
work_geodatabase = os.path.join(drive, root_folder, 'AKVEG_Workspace.gdb')

# Define input files
area_input = os.path.join(postprocess_folder, 'AKVEG_FoliarCover_v2_ModelArea_3338.tif')
esa_input = os.path.join(postprocess_folder, 'AlaskaYukon_ESAWorldCover2_v2_10m_3338.tif')
if range_boolean == True:
    range_input = os.path.join(postprocess_folder, f'range_{group}_v20241226.tif')
else:
    range_input = area_input

# Define intermediate files
merged_file = os.path.join(intermediate_folder, f'{group}_merged.tif')

# Define output files
foliar_output = os.path.join(output_folder, f'{group}_10m_3338.tif')

# Set overwrite option
arcpy.env.overwriteOutput = True

# Specify core usage
arcpy.env.parallelProcessingFactor = "75%"

# Set snap raster and extent
area_raster = Raster(area_input)
arcpy.env.snapRaster = area_raster
arcpy.env.extent = area_raster.extent

# Set cell size environment
cell_size = arcpy.management.GetRasterProperties(area_raster, 'CELLSIZEX', '').getOutput(0)
arcpy.env.cellSize = int(cell_size)

# Set environment workspace
arcpy.env.workspace = work_geodatabase

# Apply model corrections
if os.path.exists(foliar_output) == 0:
    print(f'Enforcing model domain...')
    iteration_start = time.time()
    merged_raster = Raster(merged_file)
    esa_raster = Raster(esa_input)
    if range_boolean == True:
        range_raster = Raster(range_input)
    else:
        range_raster = area_raster
    # Set no data to zero
    print('\tSetting no data to zero...')
    nodata_raster = Con(IsNull(merged_raster), 0, merged_raster)
    # Correct erroneous data
    print('\tCorrecting data errors...')
    if (barren_boolean == True) & (water_boolean == True) & (range_boolean == True):
        remove_raster = Con(((nodata_raster >= presence_threshold) & (nodata_raster <= 100))
                            & ((esa_raster != 70) & (esa_raster != 50) & (esa_raster != 60) & (esa_raster != 80))
                            & (range_raster == 1), nodata_raster, 0)
    elif (barren_boolean == True) & (water_boolean == True) & (range_boolean == False):
        remove_raster = Con(((nodata_raster >= presence_threshold) & (nodata_raster <= 100))
                            & ((esa_raster != 70) & (esa_raster != 50) & (esa_raster != 60) & (esa_raster != 80)),
                            nodata_raster, 0)
    elif (barren_boolean == True) & (water_boolean == False) & (range_boolean == True):
        remove_raster = Con(((nodata_raster >= presence_threshold) & (nodata_raster <= 100))
                            & ((esa_raster != 70) & (esa_raster != 50) & (esa_raster != 60))
                            & (range_raster == 1), nodata_raster, 0)
    elif (barren_boolean == False) & (water_boolean == True) & (range_boolean == True):
        remove_raster = Con(((nodata_raster >= presence_threshold) & (nodata_raster <= 100))
                            & ((esa_raster != 70) & (esa_raster != 50) & (esa_raster != 80))
                            & (range_raster == 1), nodata_raster, 0)
    elif (barren_boolean == True) & (water_boolean == False) & (range_boolean == False):
        remove_raster = Con(((nodata_raster >= presence_threshold) & (nodata_raster <= 100))
                            & ((esa_raster != 70) & (esa_raster != 50) & (esa_raster != 60)),
                            nodata_raster, 0)
    elif (barren_boolean == False) & (water_boolean == True) & (range_boolean == False):
        remove_raster = Con(((nodata_raster >= presence_threshold) & (nodata_raster <= 100))
                            & ((esa_raster != 70) & (esa_raster != 50) & (esa_raster != 80)),
                            nodata_raster, 0)
    if (barren_boolean == False) & (water_boolean == False) & (range_boolean == True):
        remove_raster = Con(((nodata_raster >= presence_threshold) & (nodata_raster <= 100))
                            & ((esa_raster != 70) & (esa_raster != 50))
                            & (range_raster == 1), nodata_raster, 0)
    else:
        remove_raster = Con(((nodata_raster >= presence_threshold) & (nodata_raster <= 100))
                            & ((esa_raster != 70) & (esa_raster != 50)),
                            nodata_raster, 0)
    # Enforce study area boundary
    print('\tExtracting to study area boundary...')
    extract_raster = ExtractByMask(remove_raster, area_raster, 'INSIDE', area_raster.extent)
    # Write results
    print('\tExporting raster as 8-bit unsigned...')
    arcpy.management.CopyRaster(extract_raster,
                                foliar_output,
                                '',
                                '',
                                '255',
                                'NONE',
                                'NONE',
                                '8_BIT_UNSIGNED',
                                'NONE',
                                'NONE',
                                'TIFF',
                                'NONE',
                                'CURRENT_SLICE',
                                'NO_TRANSPOSE')
    end_timing(iteration_start)
else:
    print('Model domain already enforced.')
    print('----------')
