import pandas as pd
import numpy as np
import json
import os

def analyze():
    # Load config to get scales and suffixes
    with open("03_data_topography/aksdb_cog_pipeline/scaling_config.json", "r") as f:
        config = json.load(f)

    # Load pruned variables to ignore them
    pruned_vars = []
    if os.path.exists("03_data_topography/aksdb_cog_pipeline/dropped_covars.csv"):
        pruned_df = pd.read_csv("03_data_topography/aksdb_cog_pipeline/dropped_covars.csv")
        pruned_vars = pruned_df['raw_id'].tolist()

    print("Loading 10,000 point datasets...")
    orig = pd.read_csv("03_data_topography/aksdb_cog_pipeline/assessment_orig_10000.csv")
    scaled = pd.read_csv("03_data_topography/aksdb_cog_pipeline/assessment_scaled_10000.csv")
    
    # Ensure they are aligned by index
    orig = orig.sort_values("system:index").reset_index(drop=True)
    scaled = scaled.sort_values("system:index").reset_index(drop=True)
    
    gee_bands = [c for c in orig.columns if c not in ["system:index", ".geo", "control_band", "latitude", "longitude"] and c not in pruned_vars]
    results = []
    config_keys_sorted = sorted(config.keys(), key=len, reverse=True)

    # Pre-map scaled columns to orig band names for easy lookup
    scaled_col_map = {}
    for col in scaled.columns:
        if col in ["system:index", ".geo", "latitude", "longitude"]:
            continue
        for b in gee_bands:
            safe_b = b.replace(".", "p")
            if col.startswith(safe_b + "_"):
                scaled_col_map[b] = col
                break

    for b in gee_bands:
        orig_key = next((key for key in config_keys_sorted if b.startswith(key)), None)
        
        if not orig_key:
            print(f"Warning: No config found for {b}")
            continue
            
        scale = config[orig_key]["scale"]
        dtype = config[orig_key]["type"]

        scaled_col = scaled_col_map.get(b)
        if not scaled_col:
            print(f"Warning: Scaled column for {b} not found in scaled CSV.")
            continue

        # Dynamic NoData & Clamping
        if dtype == "Float32":
            nodata_val = -99999.0
            clamp_limit = 1e30
            err_limit = 0.001
        elif dtype == "Int32":
            nodata_val = -2147483648
            clamp_limit = 2147483647
            err_limit = 1.5
        elif dtype == "Byte":
            nodata_val = 0
            clamp_limit = 255
            err_limit = 1.5
        else: # Int16
            nodata_val = -32768
            clamp_limit = 32000
            err_limit = 1.5

        # 1. Mask Check
        orig_mask = (orig[b] == -99999) | orig[b].isna()
        scaled_nodata = (scaled[scaled_col] == -99999) | (scaled[scaled_col] == nodata_val) | scaled[scaled_col].isna()
        mask_diff = (orig_mask != scaled_nodata).sum()
        
        # Capture error coordinates
        if mask_diff > 0:
            err_idx = orig_mask != scaled_nodata
            err_coords = orig.loc[err_idx, ['latitude', 'longitude']].head(2).to_dict('records')
        else:
            err_coords = []
        
        # 2. Clamping check
        if dtype in ["Int16", "Int32"]:
            is_clamped = (scaled[scaled_col].abs() >= clamp_limit) & ~orig_mask
            scaled_clamped = is_clamped.sum()
        else:
            scaled_clamped = 0
        
        # 3. Value Accuracy Check
        valid_idx = ~orig_mask & ~scaled_nodata
        if valid_idx.any():
            actual_scaled = scaled.loc[valid_idx, scaled_col]
            expected_scaled = orig.loc[valid_idx, b] * scale
            diff_scaled = np.abs(actual_scaled - expected_scaled)
            max_diff_scaled = diff_scaled.max()
        else:
            max_diff_scaled = 0

        results.append({
            "Band": b,
            "Type": dtype,
            "Scale": scale,
            "Mask_Mismatches": mask_diff,
            "Scaled_Clamped": scaled_clamped,
            "Max_Diff_Scaled": round(max_diff_scaled, 4),
            "Limit": err_limit,
            "Err_Coords": err_coords
        })
        
    res_df = pd.DataFrame(results)
    problems = res_df[
        (res_df["Mask_Mismatches"] > 0) | 
        (res_df["Scaled_Clamped"] > 0) | 
        (res_df["Max_Diff_Scaled"] > res_df["Limit"])
    ]
    
    print(f"Total Bands Analyzed: {len(gee_bands)}")
    print(f"Bands with Issues: {len(problems)}")
    
    if not problems.empty:
        print("\n--- PROBLEM DETAIL ---")
        cols = ["Band", "Type", "Scale", "Mask_Mismatches", "Scaled_Clamped", "Max_Diff_Scaled", "Err_Coords"]
        print(problems[cols].sort_values("Max_Diff_Scaled", ascending=False).to_string(index=False))
    else:
        print("\nALL BANDS MATCH SOURCE MASKS AND SCALE CORRECTLY.")

if __name__ == "__main__":
    analyze()
