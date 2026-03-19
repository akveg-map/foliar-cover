import matplotlib.pyplot as plt
import matplotlib.patches as patches
import geopandas as gpd
import numpy as np

# Load Natural Earth landmass data
url = 'https://naturalearth.s3.amazonaws.com/50m_physical/ne_50m_land.zip'
land = gpd.read_file(url)
land_3338 = land.to_crs(epsg=3338)

# Data Extents (EPSG:3338)
full_extent = {
    'xmin': -2175592.6,
    'ymin': 405266.0,
    'xmax': 1550577.3,
    'ymax': 2384026.0
}

partial_extent = {
    'xmin': -1035461.8,
    'ymin': 417706.0,
    'xmax': 1550578.1,
    'ymax': 2384026.0
}

# Add a tiny 2% buffer to prevent box clipping while maintaining the "no gutter" feel
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

# Calculate exact aspect ratio to eliminate gutters
view_width = view_extent['xmax'] - view_extent['xmin']
view_height = view_extent['ymax'] - view_extent['ymin']
aspect_ratio = view_width / view_height

# Set figure size to match aspect ratio exactly (height=10 inches)
fig = plt.figure(figsize=(10 * aspect_ratio, 10))
fig.patch.set_facecolor('#add8e6')

ax = fig.add_axes([0, 0, 1, 1])
ax.set_facecolor('#add8e6')

# Landmasses
land_3338.plot(ax=ax, facecolor='#bdbdbd', edgecolor='#969696', linewidth=0.5, zorder=1)

# Add bounding boxes
rect_full = patches.Rectangle(
    (full_extent['xmin'], full_extent['ymin']),
    width,
    height,
    linewidth=3, edgecolor='#1f77b4', facecolor='none', label='Full Study Area (Most Variables)', zorder=10
)
ax.add_patch(rect_full)

rect_partial = patches.Rectangle(
    (partial_extent['xmin'], partial_extent['ymin']),
    partial_extent['xmax'] - partial_extent['xmin'],
    partial_extent['ymax'] - partial_extent['ymin'],
    linewidth=3, edgecolor='#d62728', linestyle='--', facecolor='none', label='Hydrological / Unverified Extent', zorder=11
)
ax.add_patch(rect_partial)

# Set map limits
ax.set_xlim(view_extent['xmin'], view_extent['xmax'])
ax.set_ylim(view_extent['ymin'], view_extent['ymax'])

# Clean styling
ax.axis('off')

# Legend - Top Right
ax.legend(loc='upper right', frameon=True, framealpha=0.95, fontsize=14, borderaxespad=2)

out_path = '03_data_topography/aksdb_cog_pipeline/reports/extents_map.png'
plt.savefig(out_path, dpi=150, pad_inches=0, facecolor='#add8e6', edgecolor='none')
print(f"Extents map saved to {out_path}")
