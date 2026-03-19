import pandas as pd
import numpy as np
import math
import os

print("Loading metadata and stats...")
cw = pd.read_csv('03_data_topography/aksdb_cog_pipeline/metadata_crosswalk.csv')
stats = pd.read_csv('03_data_topography/aksdb_cog_pipeline/reports/sample_stats_scaled.csv')

# Merge
df = pd.merge(cw, stats, on='scaled_id', how='left')
df = df.sort_values(by=['category', 'title'])
variables = df.to_dict('records')

seq_hex = ['440154', '414487', '2a788e', '22a884', '7ad151', 'fde725']
div_hex = ['053061', '2166ac', '4393c3', '92c5de', 'd1e5f0', 'f7f7f7', 'fddbc7', 'f4a582', 'd6604d', 'b2182b', '67001f']
cat_hex = ['7fc97f', 'beaed4', 'fdc086', 'ffff99', '386cb0', 'f0027f', 'bf5b17', '666666']

js_lines = [
    "// AKVEG Topography Covariates Viz Script",
    "// Auto-generated to match 'Effective Contrast' from report",
    "",
    "var ic = ee.ImageCollection('projects/akveg-map/assets/covariates/aksdb/aksdb_topo_v20250422_scaled_i32');",
    "var img = ic.mosaic(); // Note: Assets are single images, but registered as IC?",
    "// Correction: The python script uses ee.Image('.../asset_name')",
    "// So let's load them as a single multi-band image or from IC",
    "var getImg = function(assetId) { return ee.Image('projects/akveg-map/assets/covariates/aksdb/aksdb_topo_v20250422_scaled_i32/' + assetId); };",
    ""
]

layer_adds = []

for i, var in enumerate(variables):
    mean = var.get('s_mean', 0)
    std = var.get('s_std', 0)
    p1, p5, p10, p25, p50, p75, p90, p95, p99 = [var.get(f's_p{x}', 0) for x in [1, 5, 10, 25, 50, 75, 90, 95, 99]]
    scale = var.get('scale', 1)
    
    asset_name = var['scaled_id'].replace('.', 'p')
    
    is_categorical = var['data_type'] == 'Byte'
    is_divergent = any(x in str(var['raw_id']) for x in ['diff', 'dev', 'tpi', 'rel'])
    is_hydrology = any(x in str(var['raw_id']) for x in ['ca_', 'dfa', 'spi', 'swi', 'vlyd'])
    
    v_min, v_max = p1, p99
    is_log = False
    
    if is_categorical:
        v_min, v_max = var.get('s_min', 1), var.get('s_max', 10)
    else:
        if is_hydrology:
            p1_clean = max(1, p1)
            if p99 > p1_clean:
                v_min, v_max = math.log10(p1_clean), math.log10(p99)
                is_log = True
            else:
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
            is_bounded = any(x in str(var['raw_id']) for x in ['perct', 'percl', 'percc'])
            
            if iqr > 0 and not is_bounded and 'twi' not in str(var['raw_id']):
                for method in ["SD0.5", "P10", "SD1", "P5", "SD2", "P1"]:
                    cmin, cmax = candidates[method]
                    
                    if is_divergent and abs(p50 / scale) < 0.1:
                        limit = max(abs(cmin), abs(cmax))
                        cmin, cmax = -limit, limit
                        
                    crange = cmax - cmin
                    if crange > 0:
                        if (iqr / crange) > 0.25:
                            v_min, v_max = cmin, cmax
                            break
                else:
                    v_min, v_max = p1, p99
                    if is_divergent and abs(p50 / scale) < 0.1:
                        limit = max(abs(v_min), abs(v_max))
                        v_min, v_max = -limit, limit
            else:
                v_min, v_max = p1, p99
                if is_divergent and abs(p50 / scale) < 0.1:
                    limit = max(abs(v_min), abs(v_max))
                    v_min, v_max = -limit, limit

    current_hex = cat_hex if is_categorical else (div_hex if is_divergent else seq_hex)
    
    nodata_val = -2147483648 if 'Int32' in var['data_type'] else (-32768 if 'Int16' in var['data_type'] else 0)
    
    # Build JS snippet
    layer_name = f"{var['raw_id']} ({var['scaled_id']})"
    show_flag = "true" if i == 0 else "false"
    
    palette_str = "['" + "', '".join(current_hex) + "']"
    
    img_js = f"getImg('{asset_name}')"
    if is_log:
        img_js = f"{img_js}.where({img_js}.lte(0), 1).log10()"
    
    img_js = f"{img_js}.updateMask({img_js}.neq({nodata_val}))"
    
    add_layer = f"Map.addLayer({img_js}, {{min: {v_min:.4f}, max: {v_max:.4f}, palette: {palette_str}}}, '{layer_name}', {show_flag});"
    layer_adds.append(add_layer)

js_lines.extend(layer_adds)
js_lines.append("")
js_lines.append("Map.setCenter(-150.0, 64.0, 4);")

out_file = '03_data_topography/aksdb_cog_pipeline/reports/viz_topo_cogs.js'
with open(out_file, 'w') as f:
    f.write('\n'.join(js_lines))

print(f"Wrote GEE JS script to {out_file}")
