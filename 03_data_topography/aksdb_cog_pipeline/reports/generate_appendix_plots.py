import ee
import requests
import PIL.Image
import io
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patches as patches
import geopandas as gpd
import pandas as pd
import numpy as np
import math
import os
import time
import textwrap
from tqdm import tqdm
from matplotlib.colors import LinearSegmentedColormap, Normalize
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

PROJECT_ID = "akveg-map"
ee.Initialize(project=PROJECT_ID)

out_dir = '03_data_topography/aksdb_cog_pipeline/reports/appendix'
os.makedirs(out_dir, exist_ok=True)

# 1. Load Metadata and Stats
print("Loading metadata and stats...")
cw = pd.read_csv('03_data_topography/aksdb_cog_pipeline/metadata_crosswalk.csv')
stats = pd.read_csv('03_data_topography/aksdb_cog_pipeline/reports/sample_stats_scaled.csv')

# Merge
df = pd.merge(cw, stats, on='scaled_id', how='left')
df = df.sort_values(by=['category', 'title'])
variables = df.to_dict('records')

# 2. Setup Basemap
print("Loading Natural Earth landmass data...")
ne_url = 'https://naturalearth.s3.amazonaws.com/50m_physical/ne_50m_land.zip'
land = gpd.read_file(ne_url)
land_3338 = land.to_crs(epsg=3338)

full_extent = {
    'xmin': -2175592.6,
    'ymin': 405266.0,
    'xmax': 1550577.3,
    'ymax': 2384026.0
}

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

view_width = view_extent['xmax'] - view_extent['xmin']
view_height = view_extent['ymax'] - view_extent['ymin']
aspect_ratio = view_width / view_height

extent_geom = ee.Geometry.Rectangle(
    coords=[view_extent['xmin'], view_extent['ymin'], view_extent['xmax'], view_extent['ymax']],
    proj='EPSG:3338', geodesic=False
)

# 3. Pagination
plots_per_page = 10
rows = 5
cols = 2
num_pages = math.ceil(len(variables) / plots_per_page)

# Palettes
seq_hex = ['#440154', '#414487', '#2a788e', '#22a884', '#7ad151', '#fde725']
div_hex = ['#053061', '#2166ac', '#4393c3', '#92c5de', '#d1e5f0', '#f7f7f7', '#fddbc7', '#f4a582', '#d6604d', '#b2182b', '#67001f']
cat_hex = ['#7fc97f', '#beaed4', '#fdc086', '#ffff99', '#386cb0', '#f0027f', '#bf5b17', '#666666']

seq_cmap = LinearSegmentedColormap.from_list('seq', seq_hex)
div_cmap = LinearSegmentedColormap.from_list('div', div_hex)
cat_cmap = LinearSegmentedColormap.from_list('cat', cat_hex)

def format_num(val, scale=1):
    if pd.isna(val): return "N/A"
    phys_val = val / float(scale)
    if abs(phys_val) < 0.0001 and phys_val != 0: return f"{phys_val:.6f}"
    if abs(phys_val) > 1000: return f"{phys_val:,.1f}"
    return f"{phys_val:.3f}"

print(f"Generating {num_pages} appendix pages for {len(variables)} variables...")

for page in tqdm(range(num_pages), desc="Pages"):
    start_idx = page * plots_per_page
    end_idx = min(start_idx + plots_per_page, len(variables))
    page_vars = variables[start_idx:end_idx]
    
    fig_width = 12
    fig_height = fig_width * (rows / cols) / aspect_ratio
    fig, axes = plt.subplots(rows, cols, figsize=(fig_width, fig_height))
    fig.patch.set_facecolor('white')
    axes = axes.flatten()
    
    for i, var in enumerate(page_vars):
        ax = axes[i]
        
        # Stats (Scaled)
        mean = var.get('s_mean', 0)
        std = var.get('s_std', 0)
        p1, p5, p10, p25, p50, p75, p90, p95, p99 = [var.get(f's_p{x}', 0) for x in [1, 5, 10, 25, 50, 75, 90, 95, 99]]
        scale = var.get('scale', 1)
        scale_str = f"{scale:,.0f}" if scale >= 1 else f"{scale:g}"
        
        asset_name = var['scaled_id'].replace('.', 'p')
        asset_id = f"projects/akveg-map/assets/covariates/aksdb/aksdb_topo_v20250422_scaled_i32/{asset_name}"
        img = ee.Image(asset_id)
        
        is_categorical = var['data_type'] == 'Byte'
        is_divergent = any(x in str(var['raw_id']) for x in ['diff', 'dev', 'tpi', 'rel'])
        is_hydrology = any(x in str(var['raw_id']) for x in ['ca_', 'dfa', 'spi', 'swi', 'vlyd'])
        
        stretch_method = "P1"
        v_min, v_max = p1, p99
        
        if is_categorical:
            stretch_method = "Categorical"
            v_min, v_max = var.get('s_min', 1), var.get('s_max', 10)
        else:
            if is_hydrology:
                p1_clean = max(1, p1)
                if p99 > p1_clean:
                    img = img.where(img.lte(0), 1).log10()
                    v_min, v_max = math.log10(p1_clean), math.log10(p99)
                    stretch_method = "Log10(P1)"
                else:
                    stretch_method = "P1"
                    v_min, v_max = p1, p99
            else:
                candidates = {
                    "SD0.5": (mean - 0.5*std, mean + 0.5*std),
                    "SD1": (mean - std, mean + std),
                    "P10": (p10, p90),
                    "P5": (p5, p95),
                    "SD2": (mean - 2*std, mean + 2*std),
                    "P1": (p1, p99)
                }
                
                iqr = p75 - p25
                # Percentile and Percentage variables should use P1 to show the full 0-100 range
                is_bounded = any(x in str(var['raw_id']) for x in ['perct', 'percl', 'percc'])
                
                if iqr > 0 and not is_bounded and 'twi' not in str(var['raw_id']):
                    for method in ["SD0.5", "P10", "SD1", "P5", "SD2", "P1"]:
                        cmin, cmax = candidates[method]
                        
                        # Apply symmetric logic during selection for divergent metrics
                        if is_divergent and abs(p50 / scale) < 0.1:
                            limit = max(abs(cmin), abs(cmax))
                            cmin, cmax = -limit, limit
                            
                        crange = cmax - cmin
                        if crange > 0:
                            # If IQR covers at least 25% of the range, this is a "good enough" stretch
                            # to show landscape variance without washing out 95% of pixels.
                            if (iqr / crange) > 0.25:
                                stretch_method = method
                                v_min, v_max = cmin, cmax
                                break
                    else:
                        # Fallback if no method is tight enough
                        stretch_method = "P1"
                        v_min, v_max = p1, p99
                        if is_divergent and abs(p50 / scale) < 0.1:
                            limit = max(abs(v_min), abs(v_max))
                            v_min, v_max = -limit, limit
                else:
                    stretch_method = "P1"
                    v_min, v_max = p1, p99
                    if is_divergent and abs(p50 / scale) < 0.1:
                        limit = max(abs(v_min), abs(v_max))
                        v_min, v_max = -limit, limit

        current_cmap = cat_cmap if is_categorical else (div_cmap if is_divergent else seq_cmap)
        current_hex = cat_hex if is_categorical else (div_hex if is_divergent else seq_hex)
        
        viz = {'min': v_min, 'max': v_max, 'palette': current_hex}
        nodata_val = -2147483648 if 'Int32' in var['data_type'] else (-32768 if 'Int16' in var['data_type'] else 0)
        overlay = img.visualize(**viz).updateMask(img.neq(nodata_val))
        
        overlay_img = PIL.Image.new('RGBA', (600, 600), (0, 0, 0, 0))
        for attempt in range(3):
            try:
                url = overlay.getThumbURL({'region': extent_geom, 'crs': 'EPSG:3338', 'dimensions': 600, 'format': 'png'})
                r = requests.get(url, timeout=30)
                if r.status_code == 200:
                    overlay_img = PIL.Image.open(io.BytesIO(r.content))
                    break
            except: time.sleep(2)
        
        ax.set_facecolor('#add8e6')
        land_3338.plot(ax=ax, facecolor='#bdbdbd', edgecolor='#969696', linewidth=0.3, zorder=1)
        ax.imshow(overlay_img, extent=[view_extent['xmin'], view_extent['xmax'], view_extent['ymin'], view_extent['ymax']], zorder=5)
        
        # --- Add 10m Chip in the Ocean ---
        # Chip Location: Near Denali (-151.0, 63.5)
        chip_loc = ee.Geometry.Point([-151.0, 63.5])
        # Chip region: 2.5km x 2.5km (250x250 pixels at 10m)
        chip_region = chip_loc.buffer(1250).bounds()
        
        chip_img = PIL.Image.new('RGBA', (250, 250), (0, 0, 0, 0))
        for attempt in range(3):
            try:
                # Use same viz parameters as the main map
                url = overlay.getThumbURL({'region': chip_region, 'crs': 'EPSG:3338', 'dimensions': 250, 'format': 'png'})
                r = requests.get(url, timeout=30)
                if r.status_code == 200:
                    chip_img = PIL.Image.open(io.BytesIO(r.content))
                    break
            except: time.sleep(2)
            
        # Position chip in ocean (West of mainland, North of Aleutians)
        # Bounding box in EPSG:3338 for the chip (moved lower to clear legend):
        chip_x_min, chip_y_min = -1800000, 800000
        chip_x_max, chip_y_max = -1300000, 1300000
        ax.imshow(chip_img, extent=[chip_x_min, chip_x_max, chip_y_min, chip_y_max], zorder=10)
        # Add a border to the chip
        rect = patches.Rectangle((chip_x_min, chip_y_min), chip_x_max - chip_x_min, chip_y_max - chip_y_min, 
                                 linewidth=1, edgecolor='black', facecolor='none', zorder=11)
        ax.add_patch(rect)
        ax.text(chip_x_min, chip_y_max + 20000, "Full Res. Chip\n(2.5 km)", fontsize=6, verticalalignment='bottom', horizontalalignment='left', zorder=11)
        
        # Add a red dot at the chip geographic location (EPSG:3338 for Denali is ~149038, 1507004)
        dot_x, dot_y = 149038.67, 1507004.13
        ax.plot(dot_x, dot_y, marker='o', markersize=3, color='red', markeredgecolor='black', markeredgewidth=0.5, zorder=12)
        
        ax.set_xlim(view_extent['xmin'], view_extent['xmax'])
        ax.set_ylim(view_extent['ymin'], view_extent['ymax'])
        ax.set_xticks([]); ax.set_yticks([])
        
        title_text = f"{var['title']} ({var['raw_id']})"
        wrapped_title = "\n".join(textwrap.wrap(title_text, width=45))
        ax.set_title(wrapped_title, fontsize=10, pad=15)
        
        # Legend labels: show raw Int32 values
        stats_text = f"Scale: {scale_str} | 1%: {format_num(p1, scale)} | Med: {format_num(p50, scale)} | 99%: {format_num(p99, scale)}\nMean: {format_num(mean, scale)} | SD: {format_num(std, scale)}"
        if is_categorical:
            stats_text = f"Scale: None | Mean: {mean:.1f} | SD: {std:.1f}"
        ax.text(0.5, -0.02, stats_text, transform=ax.transAxes, fontsize=8, horizontalalignment='center', verticalalignment='top')

        ax_ins = inset_axes(ax, width="30%", height="4%", loc='upper left', borderpad=2)
        cb = mpl.colorbar.ColorbarBase(ax_ins, cmap=current_cmap, orientation='horizontal')
        ax_ins.set_xticks([])
        
        ax_ins.text(0.5, 1.2, stretch_method, transform=ax_ins.transAxes, fontsize=7, horizontalalignment='center', verticalalignment='bottom')
        
        # For legend, show the raw Int32 values used in the 'viz' params
        if is_categorical or 'Log10' not in stretch_method:
            low_val_str = f"{v_min:,.0f}"
            high_val_str = f"{v_max:,.0f}"
        else:
            # For Log10, show the actual log value of the Int32
            low_val_str = f"{v_min:.2f}"
            high_val_str = f"{v_max:.2f}"
            
        ax_ins.text(0.0, -0.2, low_val_str, transform=ax_ins.transAxes, fontsize=7, horizontalalignment='left', verticalalignment='top')
        ax_ins.text(1.0, -0.2, high_val_str, transform=ax_ins.transAxes, fontsize=7, horizontalalignment='right', verticalalignment='top')

    for j in range(len(page_vars), len(axes)):
        axes[j].axis('off')
        
    plt.tight_layout(pad=2.0, h_pad=3.5, w_pad=1.5)
    plt.savefig(f"{out_dir}/appendix_page_{page+1:02d}.png", dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)

print("Appendix generation complete.")
