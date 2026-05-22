# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Figure 2. AKVEG domain and regions
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Figure 2. AKVEG domain and regions" creates a map figure for publication that shows the AKVEG map domain overlaying the regions and biomes.
# ---------------------------------------------------------------------------

# Import required libraries
library(fs)
library(ggplot2)
library(ggrepel)
library(ggpattern)
library(sf)
library(terra)
library(tidyterra)

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = path(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
base_folder = path(project_folder, 'Data/Data_Input/basemap')
region_folder = path(project_folder, 'Data/Data_Input/region_data')
output_folder = path(project_folder, 'Documents/Manuscript_FoliarCover_FloristicGradients/figures')

# Define input files
ocean_input = path(base_folder, 'Basemap_Ocean_3338.shp')
russia_input = path(region_folder, 'Russia_Coastline_3571.shp')
na_input = path(region_folder, 'NorthAmerica_Coastline_4269.shp')
river_input = path(base_folder, 'NaturalEarth_10m_Rivers_Centerlines.shp')
domain_input = path(region_folder, 'AlaskaYukon_MapDomain_v2.0_3338.shp')
region_input = path(region_folder, 'AlaskaYukon_Regions_v2.0_3338.shp')

# Define output files
figure_output = path(output_folder, 'Figure2_AKVEG_Domain_Region.jpg')

#### CREATE MAP PLOT
####____________________________________________________

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
region_data = st_read(region_input)
region_centroids = st_point_on_surface(region_data)

# Subset the biomes
arctic_data = region_data %>%
  filter(biome == 'Arctic')
boreal_data = region_data %>%
  filter(biome == 'Boreal')
subpolar_data = region_data %>%
  filter(biome == 'Northern Subpolar Oceanic')
temperate_data = region_data %>%
  filter(biome == 'Temperate')

# Define custom fill colors
custom_colors = c(
  'Boreal' = 'white',
  'Alaska-Yukon Map Domain' = 'black'
)


# Define pattern mapping for four biomes (excluding wave and none)
pattern_map = c(
  "Arctic" = "stripe",
  "Boreal" = "none",
  "Northern Subpolar Oceanic" = "crosshatch",
  "Temperate" = "circle"
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
  geom_sf(data = region_data, color = 'white', fill = 'white', linewidth = 0.2) +
  geom_sf_pattern(
    data = temperate_data,
    aes(pattern = biome),
    color = 'black',
    linewidth = 0.5,
    fill = "white",
    pattern_fill = "black",
    pattern_density = .25,
    pattern_spacing = .01,
    pattern_angle = 45
  ) +
  geom_sf(data = boreal_data, aes(fill = biome), color = 'black', linewidth = 0.5) +
  geom_sf_pattern(
    data = arctic_data,
    aes(pattern = biome),
    color = 'black',
    linewidth = 0.5,
    fill = "white",
    pattern_fill = "black",
    pattern_density = .05,
    pattern_spacing = .01,
    pattern_angle = 45
  ) +
  geom_sf(data = river_data, color = '#BFD9F2', linewidth = 1) +
  geom_sf(data = russia_data, color = 'white', fill = NA, linewidth = 1.2) +
  geom_sf(data = russia_data, color = 'black', fill = NA, linewidth = 0.2) +
  geom_sf(data = na_data, color = 'white', fill = NA, linewidth = 1.2) +
  geom_sf(data = na_data, color = 'black', fill = NA, linewidth = 0.2) +
  geom_sf(data = region_data, color = 'white', fill = NA, linewidth = 2) +
  geom_sf_pattern(
    data = subpolar_data,
    aes(pattern = biome),
    color = 'black',
    linewidth = 0.5,
    fill = "white",
    pattern_fill = "black",
    pattern_density = .05,
    pattern_spacing = .01,
    pattern_angle = 45
  ) +
  geom_sf(data = region_data, color = 'black', fill = NA, linewidth = 0.5) +
  geom_sf(data = domain_data, aes(color = name), fill = NA, linewidth = 1.5) +
  geom_label_repel(
    data = region_centroids,
    aes(geometry = geometry, label = region),
    stat = "sf_coordinates",
    segment.color = NA,
    min.segment.length = 0,
    seed = 6,
    size = 5,
    box.padding = 0.2,
    point.padding = 0,
    max.overlaps = Inf,
    label.size = NA,
    fill = alpha(c('white'), 1)
  ) +
  scale_fill_manual(values = custom_colors) +
  scale_color_manual(values = custom_colors) +
  scale_pattern_manual(values = pattern_map) +
  coord_sf(
    crs = st_crs(3338),
    xlim = x_limits,
    ylim = y_limits,
    expand = FALSE
  ) +
  scale_x_continuous(breaks = seq(-180, 180, by = 20))+
  scale_y_continuous(breaks = seq(50,70, by = 5)) +
  theme_minimal() +
  theme(
    axis.title = element_blank(),
    axis.text = element_text(size = 14),
    panel.grid.major = element_line(colour = 'gray'),
    legend.text = element_text(size = 18),
    legend.title = element_blank(),
    legend.position = 'top',
    legend.margin = margin(t = 10)
  ) +
  labs(
    fill = "Biome"
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
