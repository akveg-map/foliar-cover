import os
import glob
import argparse
import subprocess
import sys
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
        --input-dir "gs://akveg-data/vhr/nome_beaver/processed" \
        --output "/path/to/output/visualization.js"
"""

def list_gcs_files(gcs_path):
    """Recursive list of TIF files in GCS path."""
    cmd = ["gsutil", "ls", "-r", gcs_path]
    try:
        result = subprocess.check_output(cmd, text=True)
        files = result.strip().split('\n')
        
        # Exclude intermediate files that are not COGs
        exclude_substrings = ["/200_ortho"]
        return [
            f for f in files 
            if f.strip() and f.lower().endswith('.tif') 
            and not any(ex in f for ex in exclude_substrings)
        ]
    except subprocess.CalledProcessError as e:
        print(f"Error listing GCS files: {e}")
        return []

def get_vis_params(filename):
    """Determine visualization parameters based on filename heuristics."""
    lower = filename.lower()
    if "cloud" in lower:
        return "vis_cloud"
    if "rgb" in lower:
        return "vis_rgb"
    # Pan detection: P_TOA, _pan, but not PS (Pansharpened)
    if ("p_toa" in lower or "_pan" in lower) and not ("ps_toa" in lower or "_ps_" in lower):
        return "vis_pan"
    # Default to 4-band NRG (MS or PS)
    return "vis_nrg"

def main():
    parser = argparse.ArgumentParser(description="Generate GEE Visualization Script")
    parser.add_argument("--input-dir", required=True, help="Directory containing COGs (Local or gs://)")
    parser.add_argument("--bucket", help="GCS Bucket (Required if input is local)")
    parser.add_argument("--prefix", help="GCS Prefix (Required if input is local)")
    parser.add_argument("--output", required=True, help="Output JS file path")
    args = parser.parse_args()

    is_gcs = args.input_dir.startswith("gs://")
    
    if not is_gcs and (not args.bucket or not args.prefix):
        print("Error: --bucket and --prefix are required for local input.")
        sys.exit(1)

    # Define Visualization Parameters
    js_content = [
        "// Auto-generated GEE script for VHR COGs",
        f"// Source: {args.input_dir}",
        "",
        "// Visualization Parameters (False Color: NIR, Red, Green)",
        "var vis_nrg = {bands: ['nir', 'red', 'green'], min: 0, max: [5000, 2000, 2000]};",
        "var vis_pan = {bands: ['pan'], min: 0, max: 5000};",
        "var vis_cloud = {min: 0, max: 1, palette: ['black', 'white']};",
        "var vis_rgb = {bands: ['red', 'green', 'blue'], min: 0, max: 5000};",
        "",
        "// Image Collections",
    ]

    files = []
    if is_gcs:
        print(f"Listing files from {args.input_dir}...")
        files = list_gcs_files(args.input_dir)
    else:
        files = sorted(glob.glob(os.path.join(args.input_dir, "*.tif")))
    
    if not files:
        print("No TIF files found.")
        return

    print(f"Found {len(files)} files. Grouping and generating script...")

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
            
        if is_gcs:
            gs_path = f
        else:
            gs_path = f"gs://{args.bucket}/{args.prefix}/{filename}"
            
        groups[key].append(gs_path)

    # Determine Visualization for each group
    group_vis = {}
    
    for key, paths in groups.items():
        filename = os.path.basename(paths[0])
        
        # Use heuristics instead of opening file (faster/works on GCS)
        vis_var = get_vis_params(filename)
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
        vis = group_vis.get(key, "vis_nrg")
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