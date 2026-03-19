import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.image as mpimg
import numpy as np

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

# Calculated Final Viewport (matching background_final.png)
view_extent = {
    'xmin': -2361901.1,
    'ymin': 306328.0,
    'xmax': 1736885.8,
    'ymax': 2482964.0
}

fig, ax = plt.subplots(figsize=(14, 10))

# Load basemap
bg_path = '03_data_topography/cog_pipeline/reports/background_final.png'
bg_img = mpimg.imread(bg_path)

# Display background exactly over the view extent
ax.imshow(bg_img, extent=[view_extent['xmin'], view_extent['xmax'], view_extent['ymin'], view_extent['ymax']])

# Add bounding boxes
rect_full = patches.Rectangle(
    (full_extent['xmin'], full_extent['ymin']),
    full_extent['xmax'] - full_extent['xmin'],
    full_extent['ymax'] - full_extent['ymin'],
    linewidth=2.5, edgecolor='#1f77b4', facecolor='none', label='Full Study Area (Most Variables)'
)
ax.add_patch(rect_full)

rect_partial = patches.Rectangle(
    (partial_extent['xmin'], partial_extent['ymin']),
    partial_extent['xmax'] - partial_extent['xmin'],
    partial_extent['ymax'] - partial_extent['ymin'],
    linewidth=2.5, edgecolor='#d62728', linestyle='--', facecolor='none', label='Hydrological / Unverified Extent'
)
ax.add_patch(rect_partial)

# Force view to match
ax.set_xlim(view_extent['xmin'], view_extent['xmax'])
ax.set_ylim(view_extent['ymin'], view_extent['ymax'])

# Styling: Clean, no labels
ax.axis('off')

ax.set_title('Topographic Covariate Spatial Extents', fontsize=18, pad=20)
# Legend adjustment: slightly inward to avoid cropping
ax.legend(loc='lower left', frameon=True, framealpha=0.9, fontsize=12, borderaxespad=1.5)

plt.savefig('03_data_topography/cog_pipeline/reports/extents_map.png', dpi=150, bbox_inches='tight')
print("Extents map updated.")
