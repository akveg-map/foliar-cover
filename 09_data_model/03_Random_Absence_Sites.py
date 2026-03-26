# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Select random absence sites
# Author: Timm Nawrocki
# Last Updated: 2026-03-26
# Usage: Must be executed in an ArcGIS Pro Python 3.9+ installation.
# Description: "Select random absence sites" randomly selects a sample of absence sites from polygons with a population field. This script also combines an optional set of manually derived absence sites.
# ---------------------------------------------------------------------------

# Import packages
import os
import time
from akutils import *
import arcpy

# Set version date
version_date = '20260326'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
output_folder = os.path.join(project_folder, f'Data/Data_Input/absence_data/version_{version_date}')

# Define geodatabases
project_geodatabase = os.path.join(project_folder, 'Data/AKVEG_Map.gdb')
work_geodatabase = os.path.join(project_folder, 'Data/AKVEG_Workspace.gdb')

# Define input datasets
area_input = os.path.join(project_geodatabase, 'AlaskaYukon_AbsenceAreas_3338')
manual_input = os.path.join(work_geodatabase, 'AlaskaYukon_Absences_Manual_3338')

# Define intermediate datasets
temporary_sites = os.path.join(work_geodatabase, 'AlaskaYukon_Absences_Random_3338')

# Define output datasets
absence_output = os.path.join(output_folder, 'AlaskaYukon_Absences_3338.shp')

# Set overwrite option
arcpy.env.overwriteOutput = True

# Specify core usage
arcpy.env.parallelProcessingFactor = "75%"

# Set environment workspace
arcpy.env.workspace = work_geodatabase

#### COMPILE ABSENCE DATA
####____________________________________________________

# Select random sample if it does not already exist
if arcpy.Exists(temporary_sites) == 0:
    print('Selecting random sample...')
    iteration_start = time.time()
    arcpy.management.CreateSpatialSamplingLocations(
        area_input,
        temporary_sites,
        'STRAT_POLY',
        '',
        'FIELD',
        '',
        '',
        '',
        '',
        '',
        'Population',
        'POINT',
        5000,
        'HAVE_THEIR_CENTER_IN')
    end_timing(iteration_start)
else:
    print('Random sample already exists.')
    print('----------')

# Merge manual sites if not null
if manual_input is not None:
    print('Merging manual and random samples...')
    iteration_start = time.time()
    arcpy.management.Merge([temporary_sites, manual_input],
                           absence_output)
    end_timing(iteration_start)
else:
    print('Exporting random samples...')
    iteration_start = time.time()
    arcpy.management.CopyFeatures(temporary_sites,
                                  absence_output)
    end_timing(iteration_start)
