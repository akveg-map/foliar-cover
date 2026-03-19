import ee
import requests
import PIL.Image
import io
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import geopandas as gpd
import numpy as np
import pandas as pd
import matplotlib as mpl

PROJECT_ID = "akveg-map"
ee.Initialize(project=PROJECT_ID)

# 1. Load Sample Stats
stats_df = pd.read_csv('03_data_topography/cog_pipeline/reports/sample_stats_scaled.csv')
tpi_stats = stats_df[stats_df['scaled_id'] == 'tpi_32_10k'].iloc[0]

# Stretched 1-99% using the sample stats (already scaled to Int32 values)
v_min = tpi_stats['s_p1']
v_max = tpi_stats['s_p99']

# Convert back to physical units for legend
p1_phys = v_min / 10000.0
p99_phys = v_max / 10000.0

asset_id = "projects/akveg-map/assets/covariates/aksdb/aksdb_topo_v20250422_scaled_i32/tpi_32_10k"
img = ee.Image(asset_id)

# Data Extents (EPSG:3338)
full_extent = {
    'xmin': -2175592.6,
    'ymin': 405266.0,
    'xmax': 1550577.3,
    'ymax': 2384026.0
}

# 2% buffer for consistent viewport with extents map
width = full_extent['xmax'] - full_extent['xmin']
height = full_extent['ymax'] - full_extent['ymin']
buf_x = width * 0.01
buf_y = height * 0.01

view_extent = {
    'xmin': full_extent['xmin'] - buf_x,
    'ymin': full_extent['ymin'] - buf_y,
    'xmax': full_extent['xmax'] + buf_x,
    'ymax': full_extent['ymax'] + buf_y
}

extent_geom = ee.Geometry.Rectangle(
    coords=[full_extent['xmin'], full_extent['ymin'], full_extent['xmax'], full_extent['ymax']],
    proj='EPSG:3338', geodesic=False
)

# 2. Get GEE Thumbnail for TPI
viz = {
    'min': v_min, 
    'max': v_max, 
    'palette': ['#0000ff', '#ffffff', '#ff0000']
}
overlay = img.visualize(**viz).updateMask(img.neq(-2147483648))

url = overlay.getThumbURL({
    'region': extent_geom,
    'crs': 'EPSG:3338',
    'dimensions': 2000, 
    'format': 'png'
})

print(f"Downloading TPI overlay from: {url}")
response = requests.get(url)
overlay_img = PIL.Image.open(io.BytesIO(response.content))

# 3. Load Natural Earth Background
print("Loading Natural Earth landmass data...")
ne_url = 'https://naturalearth.s3.amazonaws.com/50m_physical/ne_50m_land.zip'
land = gpd.read_file(ne_url)
land_3338 = land.to_crs(epsg=3338)

# Calculate exact aspect ratio to eliminate gutters
view_width = view_extent['xmax'] - view_extent['xmin']
view_height = view_extent['ymax'] - view_extent['ymin']
aspect_ratio = view_width / view_height

# 4. Final Assemble with Matplotlib
fig = plt.figure(figsize=(10 * aspect_ratio, 10))
fig.patch.set_facecolor('#add8e6')

ax = fig.add_axes([0, 0, 1, 1])
ax.set_facecolor('#add8e6')

# Landmasses - Darker grey for better contrast
land_3338.plot(ax=ax, facecolor='#bdbdbd', edgecolor='#969696', linewidth=0.5, zorder=1)

# TPI Overlay
ax.imshow(overlay_img, extent=[full_extent['xmin'], full_extent['xmax'], full_extent['ymin'], full_extent['ymax']], 
          zorder=5)

# Clean styling
ax.set_xlim(view_extent['xmin'], view_extent['xmax'])
ax.set_ylim(view_extent['ymin'], view_extent['ymax'])
ax.axis('off')

# Colorbar Legend
cmap = mpl.colors.LinearSegmentedColormap.from_list('tpi', ['#0000ff', '#ffffff', '#ff0000'])
norm = mpl.colors.Normalize(vmin=p1_phys, vmax=p99_phys) 
# Placement: Inside, right-side
cax = fig.add_axes([0.93, 0.25, 0.015, 0.5]) 
cb = mpl.colorbar.ColorbarBase(cax, cmap=cmap, norm=norm, orientation='vertical')
cb.set_label('Topographic Position Index', fontsize=14)

out_path = '03_data_topography/cog_pipeline/reports/representative_variable.png'
plt.savefig(out_path, dpi=150, pad_inches=0, facecolor='#add8e6', edgecolor='none')
print(f"Final representative map saved to {out_path}")
