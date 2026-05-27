# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Figure 6. Arctic map results
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Figure 6. Arctic map results" creates a map figure for publication that shows three select foliar cover maps in the Arctic Northern region.
# ---------------------------------------------------------------------------

# Import required libraries
library(dplyr)
library(fs)
library(ggplot2)
library(ggpubr)
library(ggspatial)
library(sf)
library(terra)
library(tidyterra)
library(magick)

# Set round date
round_date = 'version_2.0_20250103'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = path(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
raster_folder = path(project_folder, 'Data/Data_Output/data_package', round_date)
base_folder = path(project_folder, 'Data/Data_Input/basemap')
region_folder = path(project_folder, 'Data/Data_Input/region_data')
output_folder = path(project_folder, 'Documents/Manuscript_FoliarCover_FloristicGradients/figures')

# Define input files
imagery_input = path(output_folder, 'data', 'Figure6_Imagery_0.5m_3338.tif')
nerishr_input = path(raster_folder, 'nerishr/nerishr_10m_3338.tif')
wetsed_input = path(raster_folder, 'wetsed/wetsed_10m_3338.tif')
erivag_input = path(raster_folder, 'erivag/erivag_10m_3338.tif')
photo_input = path(output_folder, 'data', 'Figure6f_Needleleaf_Ericaceous.jpg')
ocean_input = path(base_folder, 'Basemap_Ocean_3338.shp')
russia_input = path(region_folder, 'Russia_Coastline_3571.shp')
na_input = path(region_folder, 'NorthAmerica_Coastline_4269.shp')
river_input = path(base_folder, 'NaturalEarth_10m_Rivers_Centerlines.shp')
domain_input = path(region_folder, 'AlaskaYukon_MapDomain_v2.0_3338.shp')
region_input = path(region_folder, 'AlaskaYukon_Regions_v2.0_3338.shp')

# Define output files
figure_output = path(output_folder, 'Figure6_Arctic_Map_Results.jpg')

#### CREATE DETAIL PLOTS
####____________________________________________________

# Define center coordinates
center_lon = -151.5377
center_lat = 70.3698

# Set buffer distance for an approximate display scale of 1:12,000
buffer_meters = 1000

# Convert center to point
center_point = st_sfc(st_point(c(center_lon, center_lat)), crs = 4326)
center_3338 = st_transform(center_point, crs = 3338)

# Create a bounding box around the center
bounding_box = st_bbox(center_3338) + c(-buffer_meters, -buffer_meters, buffer_meters, buffer_meters)
bounding_3338 = st_as_sfc(bounding_box)

# Extract x and y limits from bounding box
limit_coords = st_coordinates(bounding_3338)[,1:2]
x_limits = range(limit_coords[,1])
y_limits = range(limit_coords[,2])

# Prepare axis ticks
bounding_4326 = st_transform(bounding_3338, crs = 4326)
coords_4326 = st_bbox(bounding_4326)
lon_breaks = seq(floor(coords_4326$xmin * 100) / 100, ceiling(coords_4326$xmax * 100) / 100, by = 0.02)
lat_breaks = seq(floor(coords_4326$ymin * 100) / 100, ceiling(coords_4326$ymax * 100) / 100, by = 0.01)

# Prepare imagery
imagery_raster = rast(imagery_input)
imagery_crop = crop(imagery_raster, bounding_3338)

# Prepare nerishr
nerishr_raster = rast(nerishr_input)
nerishr_crop = crop(nerishr_raster, bounding_3338)
nerishr_crop[nerishr_crop < 5] = NA

# Prepare wetsed
wetsed_raster = rast(wetsed_input)
wetsed_crop = crop(wetsed_raster, bounding_3338)
wetsed_crop[wetsed_crop < 5] = NA

# Prepare erivag
erivag_raster = rast(erivag_input)
erivag_crop = crop(erivag_raster, bounding_3338)
erivag_crop[erivag_crop < 5] = NA

# Create custom color palette
custom_palette = colorRampPalette(c("#FCFECC",
                                    "#CBECB2",
                                    "#90D8A4",
                                    '#67C3A4',
                                    '#53AAA4',
                                    '#488E9E',
                                    '#417699',
                                    '#3E5C93',
                                    '#42427D',
                                    '#382D51',
                                    '#281A2C'))(100)

# Create base imagery plot
base_plot = ggplot() +
  geom_spatraster_rgb(data = imagery_crop, r = 4, g = 3, b = 2) +
  coord_sf(
    crs = st_crs(3338),
    xlim = x_limits,
    ylim = y_limits,
    expand = FALSE
  ) +
  scale_x_continuous(breaks = lon_breaks) +
  scale_y_continuous(breaks = lat_breaks) +
  ggtitle('b. High-resolution (0.5 m) imagery') +
  annotate("text",
           x = x_limits[2] - 100,  # small offset from right edge
           y = y_limits[1] + 100,  # small offset from bottom
           label = "Imagery © 2020 Maxar Technologies Inc.",
           hjust = 1,
           vjust = 0,
           size = 6,
           color = "white") +
  theme_minimal() +
  theme(plot.margin = margin(2,2,2,2),
        axis.title = element_blank(),
        axis.text = element_text(size = 14),
        panel.grid.major = element_line(colour = 'gray'),
        plot.title = element_text(size = 20)
  )

# Create nerishr plot
nerishr_plot = ggplot() +
  geom_spatraster_rgb(data = imagery_crop, r = 4, g = 3, b = 2) +
  geom_spatraster(data = nerishr_crop) +
  scale_fill_gradientn(
    colors = custom_palette,
    limits = c(3, 50),
    oob = scales::squish,
    name = 'Cover %',
    na.value = 'transparent'
  ) +
  coord_sf(
    crs = st_crs(3338),
    xlim = x_limits,
    ylim = y_limits,
    expand = FALSE
  ) +
  scale_x_continuous(breaks = lon_breaks) +
  scale_y_continuous(breaks = lat_breaks) +
  ggtitle('c. Needleleaf ericaceous shrubs') +
  theme_minimal() +
  theme(plot.margin = margin(2,2,2,2),
        axis.title = element_blank(),
        axis.text = element_text(size = 14),
        panel.grid.major = element_line(colour = 'gray'),
        plot.title = element_text(size = 20),
        legend.title = element_text(size = 16, margin = margin(b = 20)),
        legend.text = element_text(size = 14)
  ) +
  guides(fill = guide_colorbar(barwidth = 2, barheight = 15))

# Create erivag plot
erivag_plot = ggplot() +
  geom_spatraster_rgb(data = imagery_crop, r = 4, g = 3, b = 2) +
  geom_spatraster(data = erivag_crop) +
  scale_fill_gradientn(
    colors = custom_palette,
    limits = c(3, 50),
    oob = scales::squish,
    name = 'Cover %',
    na.value = 'transparent'
  ) +
  coord_sf(
    crs = st_crs(3338),
    xlim = x_limits,
    ylim = y_limits,
    expand = FALSE
  ) +
  scale_x_continuous(breaks = lon_breaks) +
  scale_y_continuous(breaks = lat_breaks) +
  ggtitle('d. Tussock cottongrass') +
  theme_minimal() +
  theme(plot.margin = margin(2,2,2,2),
        axis.title = element_blank(),
        axis.text = element_text(size = 14),
        panel.grid.major = element_line(colour = 'gray'),
        plot.title = element_text(size = 20),
        legend.title = element_text(size = 16, margin = margin(b = 20)),
        legend.text = element_text(size = 14)
  ) +
  guides(fill = guide_colorbar(barwidth = 2, barheight = 15))

# Create wetsed plot
wetsed_plot = ggplot() +
  geom_spatraster_rgb(data = imagery_crop, r = 4, g = 3, b = 2) +
  geom_spatraster(data = wetsed_crop) +
  scale_fill_gradientn(
    colors = custom_palette,
    limits = c(3, 50),
    oob = scales::squish,
    name = 'Cover %',
    na.value = 'transparent'
  ) +
  coord_sf(
    crs = st_crs(3338),
    xlim = x_limits,
    ylim = y_limits,
    expand = FALSE
  ) +
  scale_x_continuous(breaks = lon_breaks) +
  scale_y_continuous(breaks = lat_breaks) +
  ggtitle('e. Wetland sedges') +
  theme_minimal() +
  theme(plot.margin = margin(2,2,2,2),
        axis.title = element_blank(),
        axis.text = element_text(size = 14),
        panel.grid.major = element_line(colour = 'gray'),
        plot.title = element_text(size = 20),
        legend.title = element_text(size = 16, margin = margin(b = 20)),
        legend.text = element_text(size = 14)
  ) +
  guides(fill = guide_colorbar(barwidth = 2, barheight = 15))

#### CREATE LOCATOR PLOT
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

# Define minimum and maximum latitude and longitude (EPSG:4326)
lon_min = -179
lon_max = -134
lat_min = 45
lat_max = 75

# Create a bounding box polygon and transform to EPSG:3338
locator_4326 = st_sfc(
  st_polygon(list(rbind(
    c(lon_min, lat_min),
    c(lon_min, lat_max),
    c(lon_max, lat_max),
    c(lon_max, lat_min),
    c(lon_min, lat_min)
  ))),
  crs = 4326
)
locator_3338 = st_transform(locator_4326, crs = 3338)

# Extract x and y limits from bounding box
locator_coords = st_coordinates(locator_3338)[,1:2]
x_limits_loc = range(locator_coords[,1])
y_limits_loc = range(locator_coords[,2])

# Create locator map
locator_plot = ggplot() +
  geom_sf(data = ocean_data, color = NA, fill = '#BEE8FF', alpha = 0.3) +
  geom_sf(data = russia_data, color = 'black', fill = NA, linewidth = 0.2, alpha = 0.5) +
  geom_sf(data = na_data, color = 'black', fill = NA, linewidth = 0.2, alpha = 0.5) +
  geom_sf(data = region_data, color = 'black', fill = NA, linewidth = 0.5) +
  geom_point(data = center_3338, aes(x = center_3338[[1]][1], y = center_3338[[1]][2]), color = "#C90000", size = 6) +
  coord_sf(
    crs = st_crs(3338),
    xlim = x_limits_loc,
    ylim = y_limits_loc,
    expand = FALSE
  ) +
  scale_x_continuous(breaks = seq(-160, -140, by = 20))+
  scale_y_continuous(breaks = seq(40,70, by = 5)) +
  ggtitle('a. Detail location (red point)') +
  theme_minimal() +
  theme(
    axis.title = element_blank(),
    axis.text = element_text(size = 14),
    panel.grid.major = element_line(colour = 'gray'),
    plot.title = element_text(size = 20),
  )

#### MERGE AND EXPORT PLOTS
####____________________________________________________

# Read photo file
photo_data = image_read(photo_input)

image_plot = image_ggplot(photo_data, interpolate = FALSE) +
  theme_minimal() +
  ggtitle('f. Ericaceous sandy ridge (photo)') +
  theme(
    plot.title = element_text(size = 20),
    axis.title.x = element_blank(),
    axis.text.x = element_blank(),
    axis.ticks.x = element_blank(),
    axis.title.y = element_blank(),
    axis.text.y = element_blank(),
    axis.ticks.y = element_blank() 
  )

# Create merged plot
combine_plot = ggarrange(locator_plot,
                         base_plot,
                         nerishr_plot,
                         erivag_plot,
                         wetsed_plot,
                         image_plot,
                         ncol = 2,
                         nrow = 3,
                         common.legend = TRUE,
                         legend = "right",
                         align = "hv",
                         widths = c(1, 1))

# Export plot
ggsave(figure_output,
       plot = combine_plot,
       device = 'jpeg',
       path = NULL,
       scale = 2,
       width = 6.5,
       height = 8,
       units = 'in',
       dpi = 600,
       limitsize = TRUE)
