# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Figure A.1. Training data map
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-06-08
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Figure A.1. Training data map" creates a map figure for publication that shows the training and validation data selected for the AKVEG foliar cover maps.
# ---------------------------------------------------------------------------

# Import required libraries
library(dplyr)
library(fs)
library(ggplot2)
library(ggrepel)
library(ggpattern)
library(readr)
library(readxl)
library(writexl)
library(sf)
library(stringr)
library(terra)
library(tidyterra)
library(tibble)
library(tidyr)

# Set round date
round_date = 'version_20260415'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = path(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
site_folder = path(project_folder, 'Data_Input/site_data', round_date)
base_folder = path(project_folder, 'Data_Input/basemap')
region_folder = path(project_folder, 'Data_Input/region_data')
output_folder = path(project_folder, 'Data_Output/summary_results', round_date)

# Define input files
site_input = path(site_folder, 'akveg_site_visits_3338.csv')
ocean_input = path(base_folder, 'Basemap_Ocean_3338.shp')
russia_input = path(region_folder, 'Russia_Coastline_3571.shp')
na_input = path(region_folder, 'NorthAmerica_Coastline_4269.shp')
river_input = path(base_folder, 'NaturalEarth_10m_Rivers_Centerlines.shp')
domain_input = path(region_folder, 'AlaskaYukon_MapDomain_v2p1_3338.shp')
region_input = path(region_folder, 'AlaskaYukon_USNVC_ZonesRegions_v2p1_3338.shp')

# Define output files
figure_output = path(output_folder, 'FigureA1a_Training_Data.jpg')

#### CREATE MAP PLOT
####____________________________________________________

# Read input data
site_visit_selected = read_csv(site_input) %>%
  # Convert geometries to points with EPSG:3338
  st_as_sf(x = ., coords = c('cent_x', 'cent_y'), crs = 3338, remove = FALSE) %>%
  # Remove the excluded sites
  filter(exclude == 0) %>%
  # Remove the absences
  filter(project_code != 'akveg_absences') %>%
  # Summarize cover version
  mutate(cover_version = case_when(cover_type == 'absolute canopy cover' ~ 'absolute',
                                   cover_type == 'absolute foliar cover' ~ 'absolute',
                                   cover_type == 'top canopy cover' ~ 'top',
                                   cover_type == 'top foliar cover' ~ 'top',
                                   TRUE ~ 'ERROR')) %>%
  # Arrange data to plot absolute cover on top
  arrange(desc(cover_version))

# Read shapes
ocean_data = st_read(ocean_input)
russia_data = st_read(russia_input) %>%
  st_transform(., crs = 3338)
na_data = st_read(na_input) %>%
  st_transform(., crs = 3338)
river_data = st_read(river_input) %>%
  st_transform(., crs = 3338)
domain_data = st_read(domain_input) %>%
  mutate(name = 'Alaska-Yukon Map Domain')
region_data = st_read(region_input) %>%
  select(zone, region)

# Define custom fill colors
custom_colors = c(
  'absolute' = '#A80000',
  'top' = '#F5B8B8',
  'Alaska-Yukon Map Domain' = 'black'
)

# Define minimum and maximum latitude and longitude (EPSG:4326)
lon_min = -130
lon_max = 174
lat_min = 50
lat_max = 70

# Create a bounding box polygon and transform to EPSG:3338
bounds_4326 = st_sfc(
  st_polygon(list(rbind(
    c(lon_min, lat_min),
    c(lon_min, lat_max),
    c(lon_max, lat_max),
    c(lon_max, lat_min),
    c(lon_min, lat_min)
  ))),
  crs = 4326
)
bounds_3338 = st_transform(bounds_4326, crs = 3338)

# Extract x and y limits from bounding box
limit_coords = st_coordinates(bounds_3338)[,1:2]
x_limits = range(limit_coords[,1])
y_limits = range(limit_coords[,2])

# Create map of AKVEG regions and map domain
map_plot = ggplot() +
  geom_sf(data = ocean_data, color = NA, fill = '#BEE8FF', alpha = 0.3) +
  geom_sf(data = russia_data, color = 'black', fill = 'lightgray', linewidth = 0.2, alpha = 0.5) +
  geom_sf(data = na_data, color = 'black', fill = 'lightgray', linewidth = 0.2, alpha = 0.5) +
  geom_sf(data = region_data, color = 'black', fill = 'white', linewidth = 0.5) +
  geom_sf(data = river_data, color = '#BFD9F2', linewidth = 1) +
  geom_sf(data = russia_data, color = 'white', fill = NA, linewidth = 1.2) +
  geom_sf(data = russia_data, color = 'black', fill = NA, linewidth = 0.2) +
  geom_sf(data = na_data, color = 'white', fill = NA, linewidth = 1.2) +
  geom_sf(data = na_data, color = 'black', fill = NA, linewidth = 0.2) +
  geom_sf(data = site_visit_selected,
          aes(fill = cover_version),
          color = 'black',
          pch = 21,
          linewidth = 0.3,
          size = 3) +
  geom_sf(data = region_data, color = 'white', fill = NA, linewidth = 1.5) +
  geom_sf(data = region_data, color = 'black', fill = NA, linewidth = 0.5) +
  geom_sf(data = domain_data, aes(color = name), fill = NA, linewidth = 1.5) +
  scale_fill_manual(values = custom_colors) +
  scale_color_manual(values = custom_colors) +
  coord_sf(
    crs = st_crs(3338),
    xlim = x_limits,
    ylim = y_limits,
    expand = FALSE
  ) +
  scale_x_continuous(breaks = seq(-180, 180, by = 20))+
  scale_y_continuous(breaks = seq(50,70, by = 5)) +
  ggtitle('a. Map of site visits by absolute or top cover') +
  theme_minimal() +
  theme(
    axis.title = element_blank(),
    axis.text = element_text(size = 14),
    panel.grid.major = element_line(colour = 'gray'),
    legend.text = element_text(size = 18),
    legend.title = element_blank(),
    legend.position = 'top',
    legend.margin = margin(t = 10),
    plot.title = element_text(size = 20)
  ) +
  guides(
    fill = guide_legend(override.aes = list(size = 5)),
    color = guide_legend(override.aes = list(size = 2))
  ) +
  labs(
    fill = "Cover Type"
  )

# Export plot
ggsave(figure_output,
       plot = map_plot,
       device = 'jpeg',
       path = NULL,
       scale = 2,
       width = 6.5,
       height = 4,
       units = 'in',
       dpi = 600,
       limitsize = TRUE)
