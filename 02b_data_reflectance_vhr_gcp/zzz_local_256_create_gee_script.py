import os
import glob
import argparse
import rasterio
from collections import defaultdict

"""
256_create_gee_script.py

Description:
    Step 5.6 of VHR Workflow.
    Generates a Google Earth Engine (JavaScript) script to visualize the 
    uploaded COGs.
    Groups images into ImageCollections based on the first three parts of the filename.

Usage:
    python 256_create_gee_script.py \
        --input-dir "/path/to/05_cogs" \
        --bucket "akveg-data" \
        --prefix "vhr/vhr_cogs" \
        --output "/path/to/output/visualization.js"
"""

def main():
    parser = argparse.ArgumentParser(description="Generate GEE Visualization Script")
    parser.add_argument("--input-dir", required=True, help="Directory containing COGs")
    parser.add_argument("--bucket", required=True, help="GCS Bucket")
    parser.add_argument("--prefix", required=True, help="GCS Prefix")
    parser.add_argument("--output", required=True, help="Output JS file path")
    args = parser.parse_args()

    # Define Visualization Parameters
    js_content = [
        "// Auto-generated GEE script for VHR COGs",
        f"// Source: gs://{args.bucket}/{args.prefix}/",
        "",
        "// Visualization Parameters (False Color: NIR, Red, Green)",
        "var vis_nrg_4band = {bands: ['b04_nir', 'b03_red', 'b02_green'], min: 0, max: [5000, 2000, 2000]};",
        "var vis_nrg_8band = {bands: ['b07_nir', 'b05_red', 'b03_green'], min: 0, max: [5000, 2000, 2000]};",
        "var vis_pan = {bands: ['b01_pan'], min: 0, max: 5000};",
        "var vis_cloud = {min: 0, max: 1, palette: ['black', 'white']};",
        "var vis_rgb = {bands: ['b03_red', 'b02_green', 'b01_blue'], min: 0, max: 5000};",
        "",
        "// Image Collections",
    ]

    files = sorted(glob.glob(os.path.join(args.input_dir, "*.tif")))
    
    if not files:
        print("No TIF files found.")
        return

    print(f"Found {len(files)} COGs. Grouping and generating script...")

    # Group files by prefix (first 3 parts)
    groups = defaultdict(list)
    
    for f in files:
        filename = os.path.basename(f)
        name_no_ext = os.path.splitext(filename)[0]
        parts = name_no_ext.split('_')
        if len(parts) >= 3:
            key = "_".join(parts[:3])
        else:
            key = name_no_ext
            
        if name_no_ext.endswith("_30m"):
            key += "_30m"
            
        gs_path = f"gs://{args.bucket}/{args.prefix}/{filename}"
        groups[key].append(gs_path)

    # Determine Visualization for each group
    group_vis = {}
    
    for key, paths in groups.items():
        # Check first file in group for metadata
        local_filename = os.path.basename(paths[0])
        local_path = os.path.join(args.input_dir, local_filename)
        
        vis_var = "vis_nrg_4band" # Default
        
        try:
            with rasterio.open(local_path) as src:
                count = src.count
                if "cloud" in key.lower():
                    vis_var = "vis_cloud"
                elif count == 1:
                    vis_var = "vis_pan"
                elif count == 8:
                    vis_var = "vis_nrg_8band"
                elif count == 4:
                    vis_var = "vis_nrg_4band"
                elif count == 3:
                    vis_var = "vis_rgb"
        except Exception as e:
            print(f"Warning: Could not read metadata for group {key}: {e}")
            
        group_vis[key] = vis_var
        
        # Write ImageCollection definition
        js_content.append(f"var ic_{key} = ee.ImageCollection([")
        for p in paths:
            js_content.append(f"  ee.Image.loadGeoTIFF('{p}'),")
        js_content.append("]);")
        js_content.append("")

    # Determine Layer Order
    sorted_keys = sorted(groups.keys())
    
    cat_cloud = [k for k in sorted_keys if "cloud" in k.lower()]
    cat_ps_srlite = [k for k in sorted_keys if "ps_srlite" in k.lower()]
    cat_ps_toa = [k for k in sorted_keys if "ps_toa" in k.lower()]
    cat_ms_srlite = [k for k in sorted_keys if "ms_srlite" in k.lower()]
    cat_ms_toa = [k for k in sorted_keys if "ms_toa" in k.lower()]
    cat_p_toa = [k for k in sorted_keys if "p_toa" in k.lower()]
    
    used = set(cat_cloud + cat_ps_srlite + cat_ps_toa + cat_ms_srlite + cat_ms_toa + cat_p_toa)
    cat_others = [k for k in sorted_keys if k not in used]
    
    # Construct ordered list of layers to add
    layers_to_add = []
    
    # Others (Default False)
    for k in cat_others:
        layers_to_add.append((k, "false", False))
    # P_TOA (Default False)
    for k in cat_p_toa:
        layers_to_add.append((k, "false", False))
    # MS_TOA (Default False)
    for k in cat_ms_toa:
        layers_to_add.append((k, "false", False))
    # MS_SRLite (Default False)
    for k in cat_ms_srlite:
        layers_to_add.append((k, "false", False))
    # PS_TOA (Default True)
    for k in cat_ps_toa:
        layers_to_add.append((k, "true", False))
    # PS_SRLite (Default True)
    for k in cat_ps_srlite:
        layers_to_add.append((k, "true", False))
    # Cloud (Default True)
    for k in cat_cloud:
        layers_to_add.append((k, "true", True))

    js_content.append("// Map Layers")
    
    for key, visible, is_cloud in layers_to_add:
        vis = group_vis.get(key, "vis_nrg_4band")
        if is_cloud:
            js_content.append(f"Map.addLayer(ic_{key}.mosaic().selfMask(), {vis}, '{key}', {visible});")
        else:
            js_content.append(f"Map.addLayer(ic_{key}, {vis}, '{key}', {visible});")

    # Center Object
    center_key = None
    if cat_ps_srlite: center_key = cat_ps_srlite[0]
    elif cat_ps_toa: center_key = cat_ps_toa[0]
    elif cat_cloud: center_key = cat_cloud[0]
    elif cat_others: center_key = cat_others[0]
    
    if center_key:
        js_content.append("")
        js_content.append(f"Map.centerObject(ic_{center_key});")

    # Write to file
    with open(args.output, "w") as f:
        f.write("\n".join(js_content))
        
    print(f"Script written to {args.output}")

if __name__ == "__main__":
    main()