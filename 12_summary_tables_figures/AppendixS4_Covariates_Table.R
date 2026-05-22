# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Appendix S4 covariates table
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-18
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Appendix S4 covariates table" compiles table of covariates used to develop the AKVEG foliar cover maps.
# ---------------------------------------------------------------------------

# Import required libraries
library(fs)
library(dplyr)
library(readr)
library(readxl)
library(stringr)
library(tibble)
library(writexl)

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = path(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
input_folder = path(project_folder, 'Documents/Manuscript_FoliarCover_FloristicGradients/appendix_s4')

# Define output files
table_output = path(input_folder, 'AppendixS4_Covariate_Table.xlsx')

#### COMPILE ACRONYM TABLE
####____________________________________________________

# Define a list of acronyms
acronym_list = c('3DEP', 'CRU TS', 'ESA', 'GLO', 'InSAR', 'NBR', 'NGRDI', 'NDMI', 'NDSI', 'NDVI', 'NDWI',
                 'SAR', 'SNAP', 'USGS')

# Create a table of acronyms
acronym_data = tibble(acronym = acronym_list) %>%
  mutate(name = case_when(acronym == '3DEP' ~ '3D Elevation Program',
                          acronym == 'AK' ~ 'Alaska',
                          acronym == 'BC' ~ 'British Columbia',
                          acronym == 'CRU TS' ~ 'Climate Research Unit Time-Series',
                          acronym == 'ESA' ~ 'European Space Agency',
                          acronym == 'GLO' ~ 'Global Digital Elevation Model',
                          acronym == 'InSAR' ~ 'Interferometric Synthetic Aperture Radar',
                          acronym == 'NBR' ~ 'Normalized Burn Ratio',
                          acronym == 'NGRDI' ~ 'Normalized Green Red Difference Index',
                          acronym == 'NIR' ~ 'Near-InfraRed',
                          acronym == 'NDMI' ~ 'Normalized Difference Moisture Index',
                          acronym == 'NDSI' ~ 'Normalized Difference Snow Index',
                          acronym == 'NDVI' ~ 'Normalized Difference Vegetation Index',
                          acronym == 'NDWI' ~ 'Normalized Difference Water Index',
                          acronym == 'NWT' ~ 'Northwest Territories',
                          acronym == 'SAR' ~ 'Surface Aperture Rader',
                          acronym == 'SNAP' ~ 'Scenarios Network for Alaska + Arctic Planning',
                          acronym == 'SWIR' ~ 'Short-Wave InfraRed',
                          acronym == 'USGS' ~ 'U.S. Geological Survey',
                          acronym == 'YK' ~ 'Yukon')) %>%
  rename(`Acronym` = acronym,
         `Full Name` = name)

#### COMPILE COVARIATE TABLE
####____________________________________________________

# Define list of covariates used in the foliar cover map development
predictor_all = c('summer', 'january', 'precip',
                  'elevation', 'exposure', 'heatload', 'position',
                  'aspect', 'relief', 'roughness', 'slope',
                  'coast', 'stream', 'river', 'wetness',
                  's1_1_vha', 's1_1_vhd', 's1_1_vva', 's1_1_vvd',
                  's1_2_vha', 's1_2_vhd', 's1_2_vva', 's1_2_vvd',
                  's1_3_vha', 's1_3_vhd', 's1_3_vva', 's1_3_vvd',
                  's2_1_blue', 's2_1_green', 's2_1_red', 's2_1_redge1', 's2_1_redge2',
                  's2_1_redge3', 's2_1_nir', 's2_1_redge4', 's2_1_swir1', 's2_1_swir2',
                  's2_1_nbr', 's2_1_ngrdi', 's2_1_ndmi', 's2_1_ndsi', 's2_1_ndvi', 's2_1_ndwi',
                  's2_2_blue', 's2_2_green', 's2_2_red', 's2_2_redge1', 's2_2_redge2',
                  's2_2_redge3', 's2_2_nir', 's2_2_redge4', 's2_2_swir1', 's2_2_swir2',
                  's2_2_nbr', 's2_2_ngrdi', 's2_2_ndmi', 's2_2_ndsi', 's2_2_ndvi', 's2_2_ndwi',
                  's2_3_blue', 's2_3_green', 's2_3_red', 's2_3_redge1', 's2_3_redge2',
                  's2_3_redge3', 's2_3_nir', 's2_3_redge4', 's2_3_swir1', 's2_3_swir2',
                  's2_3_nbr', 's2_3_ngrdi', 's2_3_ndmi', 's2_3_ndsi', 's2_3_ndvi', 's2_3_ndwi',
                  's2_4_blue', 's2_4_green', 's2_4_red', 's2_4_redge1', 's2_4_redge2',
                  's2_4_redge3', 's2_4_nir', 's2_4_redge4', 's2_4_swir1', 's2_4_swir2',
                  's2_4_nbr', 's2_4_ngrdi', 's2_4_ndmi', 's2_4_ndsi', 's2_4_ndvi', 's2_4_ndwi',
                  's2_5_blue', 's2_5_green', 's2_5_red', 's2_5_redge1', 's2_5_redge2',
                  's2_5_redge3', 's2_5_nir', 's2_5_redge4', 's2_5_swir1', 's2_5_swir2',
                  's2_5_nbr', 's2_5_ngrdi', 's2_5_ndmi', 's2_5_ndsi', 's2_5_ndvi', 's2_5_ndwi')

# Create a table of covariates
covariate_data = tibble(abbr = predictor_all) %>%
  mutate(name = case_when(abbr == 'summer' ~ 'Summer warmth index',
                          abbr == 'january' ~ 'January minimum air temperature',
                          abbr == 'precip' ~ 'Total annual precipitation',
                          abbr == 'elevation' ~ 'Elevation (AKVEG elevation composite)',
                          abbr == 'exposure' ~ 'Slope-weighted solar exposure',
                          abbr == 'heatload' ~ 'Heat load index',
                          abbr == 'position' ~ 'Topographic position',
                          abbr == 'aspect' ~ 'Aspect',
                          abbr == 'relief' ~ 'Surface relief ration',
                          abbr == 'roughness' ~ 'Roughness',
                          abbr == 'slope' ~ 'Slope',
                          abbr == 'coast' ~ 'Distance to marine coast',
                          abbr == 'stream' ~ 'Distance to stream or river',
                          abbr == 'river' ~ 'Distance to river',
                          abbr == 'wetness' ~ 'Slope-adjusted topographic wetness index',
                          abbr == 's1_1_vha' ~ 'Growing season SAR vertical-horizontal ascending',
                          abbr == 's1_1_vhd' ~ 'Growing season SAR vertical-horizontal descending',
                          abbr == 's1_1_vva' ~ 'Growing season SAR vertical-vertical ascending',
                          abbr == 's1_1_vvd' ~ 'Growing season SAR vertical-vertical descending',
                          abbr == 's1_2_vha' ~ 'Autumn SAR vertical-horizontal ascending',
                          abbr == 's1_2_vhd' ~ 'Autumn SAR vertical-horizontal descending',
                          abbr == 's1_2_vva' ~ 'Autumn SAR vertical-vertical ascending',
                          abbr == 's1_2_vvd' ~ 'Autumn SAR vertical-vertical descending',
                          abbr == 's1_3_vha' ~ 'Winter SAR vertical-horizontal ascending',
                          abbr == 's1_3_vhd' ~ 'Winter SAR vertical-horizontal descending',
                          abbr == 's1_3_vva' ~ 'Winter SAR vertical-vertical ascending',
                          abbr == 's1_3_vvd' ~ 'Winter SAR vertical-vertical descending',
                          abbr == 's2_1_blue' ~ 'Green-up multispectral blue',
                          abbr == 's2_1_green' ~ 'Green-up multispectral green',
                          abbr == 's2_1_red' ~ 'Green-up multispectral red',
                          abbr == 's2_1_redge1' ~ 'Green-up multispectral red edge 1',
                          abbr == 's2_1_redge2' ~ 'Green-up multispectral red edge 2',
                          abbr == 's2_1_redge3' ~ 'Green-up multispectral red edge 3',
                          abbr == 's2_1_nir' ~ 'Green-up multispectral NIR',
                          abbr == 's2_1_redge4' ~ 'Green-up multispectral red edge 4',
                          abbr == 's2_1_swir1' ~ 'Green-up multispectral SWIR 1',
                          abbr == 's2_1_swir2' ~ 'Green-up multispectral SWIR 2',
                          abbr == 's2_1_nbr' ~ 'Green-up NBR',
                          abbr == 's2_1_ngrdi' ~ 'Green-up NGRDI',
                          abbr == 's2_1_ndmi' ~ 'Green-up NDMI',
                          abbr == 's2_1_ndsi' ~ 'Green-up NDSI',
                          abbr == 's2_1_ndvi' ~ 'Green-up NDVI',
                          abbr == 's2_1_ndwi' ~ 'Green-up NDWI',
                          abbr == 's2_2_blue' ~ 'Early summer multispectral blue',
                          abbr == 's2_2_green' ~ 'Early summer multispectral green',
                          abbr == 's2_2_red' ~ 'Early summer multispectral red',
                          abbr == 's2_2_redge1' ~ 'Early summer multispectral red edge 1',
                          abbr == 's2_2_redge2' ~ 'Early summer multispectral red edge 2',
                          abbr == 's2_2_redge3' ~ 'Early summer multispectral red edge 3',
                          abbr == 's2_2_nir' ~ 'Early summer multispectral NIR',
                          abbr == 's2_2_redge4' ~ 'Early summer multispectral red edge 4',
                          abbr == 's2_2_swir1' ~ 'Early summer multispectral SWIR 1',
                          abbr == 's2_2_swir2' ~ 'Early summer multispectral SWIR 2',
                          abbr == 's2_2_nbr' ~ 'Early summer NBR',
                          abbr == 's2_2_ngrdi' ~ 'Early summer NGRDI',
                          abbr == 's2_2_ndmi' ~ 'Early summer NDMI',
                          abbr == 's2_2_ndsi' ~ 'Early summer NDSI',
                          abbr == 's2_2_ndvi' ~ 'Early summer NDVI',
                          abbr == 's2_2_ndwi' ~ 'Early summer NDWI',
                          abbr == 's2_3_blue' ~ 'Midsummer multispectral blue',
                          abbr == 's2_3_green' ~ 'Midsummer multispectral green',
                          abbr == 's2_3_red' ~ 'Midsummer multispectral red',
                          abbr == 's2_3_redge1' ~ 'Midsummer multispectral red edge 1',
                          abbr == 's2_3_redge2' ~ 'Midsummer multispectral red edge 2',
                          abbr == 's2_3_redge3' ~ 'Midsummer multispectral red edge 3',
                          abbr == 's2_3_nir' ~ 'Midsummer multispectral NIR',
                          abbr == 's2_3_redge4' ~ 'Midsummer multispectral red edge 4',
                          abbr == 's2_3_swir1' ~ 'Midsummer multispectral SWIR 1',
                          abbr == 's2_3_swir2' ~ 'Midsummer multispectral SWIR 2',
                          abbr == 's2_3_nbr' ~ 'Midsummer NBR',
                          abbr == 's2_3_ngrdi' ~ 'Midsummer NGRDI',
                          abbr == 's2_3_ndmi' ~ 'Midsummer NDMI',
                          abbr == 's2_3_ndsi' ~ 'Midsummer NDSI',
                          abbr == 's2_3_ndvi' ~ 'Midsummer NDVI',
                          abbr == 's2_3_ndwi' ~ 'Midsummer NDWI',
                          abbr == 's2_4_blue' ~ 'Late summer multispectral blue',
                          abbr == 's2_4_green' ~ 'Late summer multispectral green',
                          abbr == 's2_4_red' ~ 'Late summer multispectral red',
                          abbr == 's2_4_redge1' ~ 'Late summer multispectral red edge 1',
                          abbr == 's2_4_redge2' ~ 'Late summer multispectral red edge 2',
                          abbr == 's2_4_redge3' ~ 'Late summer multispectral red edge 3',
                          abbr == 's2_4_nir' ~ 'Late summer multispectral NIR',
                          abbr == 's2_4_redge4' ~ 'Late summer multispectral red edge 4',
                          abbr == 's2_4_swir1' ~ 'Late summer multispectral SWIR 1',
                          abbr == 's2_4_swir2' ~ 'Late summer multispectral SWIR 2',
                          abbr == 's2_4_nbr' ~ 'Late summer NBR',
                          abbr == 's2_4_ngrdi' ~ 'Late summer NGRDI',
                          abbr == 's2_4_ndmi' ~ 'Late summer NDMI',
                          abbr == 's2_4_ndsi' ~ 'Late summer NDSI',
                          abbr == 's2_4_ndvi' ~ 'Late summer NDVI',
                          abbr == 's2_4_ndwi' ~ 'Late summer NDWI',
                          abbr == 's2_5_blue' ~ 'Senescence multispectral blue',
                          abbr == 's2_5_green' ~ 'Senescence multispectral green',
                          abbr == 's2_5_red' ~ 'Senescence multispectral red',
                          abbr == 's2_5_redge1' ~ 'Senescence multispectral red edge 1',
                          abbr == 's2_5_redge2' ~ 'Senescence multispectral red edge 2',
                          abbr == 's2_5_redge3' ~ 'Senescence multispectral red edge 3',
                          abbr == 's2_5_nir' ~ 'Senescence multispectral NIR',
                          abbr == 's2_5_redge4' ~ 'Senescence multispectral red edge 4',
                          abbr == 's2_5_swir1' ~ 'Senescence multispectral SWIR 1',
                          abbr == 's2_5_swir2' ~ 'Senescence multispectral SWIR 2',
                          abbr == 's2_5_nbr' ~ 'Senescence NBR',
                          abbr == 's2_5_ngrdi' ~ 'Senescence NGRDI',
                          abbr == 's2_5_ndmi' ~ 'Senescence NDMI',
                          abbr == 's2_5_ndsi' ~ 'Senescence NDSI',
                          abbr == 's2_5_ndvi' ~ 'Senescence NDVI',
                          abbr == 's2_5_ndwi' ~ 'Senescence NDWI',
                          TRUE ~ 'ERROR')) %>%
  mutate(type = case_when(abbr == 'summer' ~ 'Climate',
                          abbr == 'january' ~ 'Climate',
                          abbr == 'precip' ~ 'Climate',
                            abbr == 'elevation' ~ 'Topography',
                            abbr == 'exposure' ~ 'Topography',
                            abbr == 'heatload' ~ 'Topography',
                            abbr == 'position' ~ 'Topography',
                            abbr == 'aspect' ~ 'Topography',
                            abbr == 'relief' ~ 'Topography',
                            abbr == 'roughness' ~ 'Topography',
                            abbr == 'slope' ~ 'Topography',
                            abbr == 'coast' ~ 'Hydrography',
                            abbr == 'stream' ~ 'Hydrography',
                            abbr == 'river' ~ 'Hydrography',
                            abbr == 'wetness' ~ 'Hydrography',
                            str_detect(abbr, 's1_') ~ 'Radiometry',
                            str_detect(abbr, 's2_') ~ 'Radiometry',
                            TRUE ~ 'ERROR')) %>%
  select(type, abbr, name) %>%
  rename(`Covariate Type` = type,
         `Abbr.` = abbr,
         `Covariate Name` = name)

#### COMPILE DATA SOURCE TABLE
####____________________________________________________

# Define a list of covariate groups
group_list = c('Climate: summer, precip (AK, BC, YK)',
               'Climate: january (AK, BC, YK)',
               'Climate: summer, precip (NWT)',
               'Climate: january (NWT)',
               'Topography: elevation (AK)',
               'Topography: elevation (BC, NWT, YK)',
               'Topography',
               'Hydrography',
               'Radiometry: SAR (all)',
               'Radiometry: Blue, Green, Red, NIR',
               'Radiometry: Red Edge (all), SWIR',
               'Radiometry: Normalized Metrics')

# Create a table of source data resolutions
source_data = tibble(group = group_list) %>%
  mutate(source = case_when(group == 'Climate: summer, precip (AK, BC, YK)' ~ 'SNAP CRU TS 4.8 (SNAP 2025)',
                            group == 'Climate: january (AK, BC, YK)' ~ 'SNAP CRU TS 4.0 (SNAP 2025)',
                            group == 'Climate: summer, precip (NWT)' ~ 'SNAP CRU TS 4.0 (SNAP 2025)',
                            group == 'Climate: january (NWT)' ~ 'SNAP CRU TS 4.0 (SNAP 2025)',
                            group == 'Topography: elevation (AK)' ~ 'USGS 3DEP InSAR (DGGS 2024)',
                            group == 'Topography: elevation (BC, NWT, YK)' ~ 'ESA GLO (ESA 2024)',
                            group == 'Topography' ~ 'AKVEG Elevation Composite (this study)',
                            group == 'Hydrography' ~ 'AKVEG Elevation Composite (this study)',
                            group == 'Radiometry: SAR (all)' ~ 'ESA Sentinel-1 (Gorelick et al. 2017)',
                            group == 'Radiometry: Blue, Green, Red, NIR' ~ 'ESA Sentinel-2 (Gorelick et al. 2017)',
                            group == 'Radiometry: Red Edge (all), SWIR' ~ 'ESA Sentinel-2 (Gorelick et al. 2017)',
                            group == 'Radiometry: Normalized Metrics' ~ 'Band Calculations (this study)',
                            TRUE ~ 'ERROR')) %>%
  mutate(resolution = case_when(group == 'Climate: summer, precip (AK, BC, YK)' ~ '2,000 m',
                                group == 'Climate: january (AK, BC, YK)' ~ '2,000 m',
                                group == 'Climate: summer, precip (NWT)' ~ '15,000 m',
                                group == 'Climate: january (NWT)' ~ '15,000 m',
                                group == 'Topography: elevation (AK)' ~ '5 m',
                                group == 'Topography: elevation (BC, NWT, YK)' ~ '30 m',
                                group == 'Topography' ~ '10 m',
                                group == 'Hydrography' ~ '10 m',
                                group == 'Radiometry: SAR (all)' ~ '10 m',
                                group == 'Radiometry: Blue, Green, Red, NIR' ~ '10 m',
                                group == 'Radiometry: Red Edge (all), SWIR' ~ '20 m',
                                group == 'Radiometry: Normalized Metrics' ~ 'N/A',
                                TRUE ~ 'ERROR')) %>%
  rename(`Covariate Group` = group,
         `Source Data (Acquired From)` = source,
         `Original Resolution` = resolution)

#### COMPILE NORMALIZED METRICS TABLE
####____________________________________________________

# Define a list of normalized metrics
metric_list = c('Norm. Burn Ration (NBR)',
                'Norm. Green Red Diff. Index (NGRDI)',
                'Norm. Diff. Moisture Index (NDMI)',
                'Norm. Diff. Snow Index (NDSI)',
                'Norm. Diff. Vegetation Index (NDVI)',
                'Norm. Diff. Water Index (NDWI)')

# Create Normalized metrics table
metric_data = tibble(name = metric_list) %>%
  mutate(equation = case_when(name == 'Norm. Burn Ration (NBR)' ~ '(NIR − SWIR2)/(NIR + SWIR2)',
                              name == 'Norm. Green Red Diff. Index (NGRDI)' ~ '(Green - Red)/(Green + Red)',
                              name == 'Norm. Diff. Moisture Index (NDMI)' ~ '(NIR − SWIR1)/(NIR + SWIR1)',
                              name == 'Norm. Diff. Snow Index (NDSI)' ~ '(Green − SWIR1)/(Green + SWIR1)',
                              name == 'Norm. Diff. Vegetation Index (NDVI)' ~ '(NIR − Red)/(NIR + Red)',
                              name == 'Norm. Diff. Water Index (NDWI)' ~ '(Green − NIR)/(Green + NIR)',
                              TRUE ~ 'ERROR')) %>%
  mutate(cite = case_when(name == 'Norm. Burn Ration (NBR)' ~ 'Key and Benson 1999',
                          name == 'Norm. Green Red Diff. Index (NGRDI)' ~ 'Hunt et al. 2005',
                          name == 'Norm. Diff. Moisture Index (NDMI)' ~ 'Gao 1996',
                          name == 'Norm. Diff. Snow Index (NDSI)' ~ 'Hall et al. 1995',
                          name == 'Norm. Diff. Vegetation Index (NDVI)' ~ 'Tucker 1979',
                          name == 'Norm. Diff. Water Index (NDWI)' ~ 'McFeeters 1996',
                          TRUE ~ 'ERROR')) %>%
  rename(`Norm. Metric` = name,
         `Calculation` = equation,
         `Reference` = cite)

#### EXPORT DATA
####____________________________________________________

# Export tables to excel
sheets = list(
  'acronyms' = acronym_data,
  'covariates' = covariate_data,
  'sources' = source_data,
  'metrics' = metric_data
)
write_xlsx(sheets, path = table_output)
