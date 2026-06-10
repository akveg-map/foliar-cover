# ---------------------------------------------------------------------------
# Prepare data package for zones and regions
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-05-30
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Prepare data package for zones and regions" converts the shapefile zones and regions to a geopackage after ensuring geometry validity.
# ---------------------------------------------------------------------------

# Import packages
import os
import geopandas as gpd

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set version date
version_date = '20260415'

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
region_folder = os.path.join(project_folder, 'Data_Input/region_data')
output_folder = os.path.join(project_folder, f'Data_Output/data_package')

# Define input file
region_input = os.path.join(region_folder, 'AlaskaYukon_USNVC_ZonesRegions_v2p1_3338.shp')

#### CONVERT VECTOR TO GEOPACKAGE
####____________________________________________________

# Define layer name
layer_name = os.path.splitext(os.path.split(region_input)[1])[0]

# Define output path
output_path = os.path.join(output_folder, f'ZonesRegions_v2p1_{version_date}')

# Ensure the destination folder exists
os.makedirs(output_path, exist_ok=True)

# Define output file name
vector_output = os.path.join(output_path, layer_name + '.gpkg')

# Convert vector to geopackage
vector_data = gpd.read_file(region_input)[['zone', 'region', 'wetland', 'geometry']]

# Ensure that features do not overlap
geometries = []
for i, row in vector_data.iterrows():
    geom = row.geometry
    if i > 0:
        # Union all previously processed geometries
        previous_union = gpd.GeoSeries(geometries).union_all()
        # Subtract the union from the current geometry
        geom = geom.difference(previous_union)
    geometries.append(geom)

# Assign the cleaned geometries back to the GeoDataFrame
vector_data.geometry = geometries

# Remove any polygons that were completely erased (empty geometries)
vector_data = vector_data[~vector_data.is_empty].reset_index(drop=True)

# Calculate shape length and shape area
vector_data['shape_length'] = vector_data.geometry.length
vector_data['shape_area'] = vector_data.geometry.area

# Determine validity
reasons = vector_data[~vector_data.geometry.is_valid].geometry.is_valid_reason
print(reasons)

# Repair all geometries in geodataframe
vector_data.geometry = vector_data.geometry.make_valid()

# Export data to geopackage
vector_data.to_file(vector_output, layer=layer_name, driver='GPKG')
