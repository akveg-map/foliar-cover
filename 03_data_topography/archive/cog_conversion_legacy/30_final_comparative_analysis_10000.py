import pandas as pd
import numpy as np
import json

def analyze():
    # Load config to get scales and suffixes
    with open("03_data_topography/cog_conversion/scaling_config.json", "r") as f:
        config = json.load(f)

    print("Loading 10,000 point datasets...")
    orig = pd.read_csv("03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_orig_10000.csv")
    scaled = pd.read_csv("03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_scaled_10000.csv")
    
    # Ensure they are aligned by index
    orig = orig.sort_values("system:index").reset_index(drop=True)
    scaled = scaled.sort_values("system:index").reset_index(drop=True)
    
    gee_bands = [c for c in orig.columns if c not in ["system:index", ".geo"]]
    results = []
    config_keys_sorted = sorted(config.keys(), key=len, reverse=True)

    for b in gee_bands:
        orig_key = None
        for key in config_keys_sorted:
            safe_key = key.replace(".", "p")
            if b == safe_key or b.startswith(safe_key + "_"):
                orig_key = key
                break
        
        if not orig_key:
            orig_key = b
            scale = 1.0
            dtype = "Int16"
        else:
            scale = config[orig_key]["scale"]
            dtype = config[orig_key]["type"]

        # 1. Mask Check
        orig_mask = (orig[b] == -99999)
        
        # In GEE sampling, we unmasked both stacks to -99999.
        # But the scaled COGs might also return their internal NoData values.
        if dtype == "Float32":
            nodata_val = -99999
        elif dtype == "Byte":
            nodata_val = 0
        else: # Int16
            nodata_val = -32768
            
        scaled_nodata = (scaled[b] == -99999) | (scaled[b] == nodata_val) | (scaled[b] == -32000)
        
        mask_diff = (orig_mask != scaled_nodata).sum()
        
        # 2. Clamping check (only for real data points)
        if dtype == "Int16":
            is_clamped = ((scaled[b] == 32000) | (scaled[b] == -32000)) & ~orig_mask
            scaled_clamped = is_clamped.sum()
        else:
            scaled_clamped = 0
        
        # 3. Value Accuracy Check (only for non-masked, non-clamped data)
        valid_idx = ~orig_mask & ~scaled_nodata
        if valid_idx.any():
            actual_scaled = scaled.loc[valid_idx, b]
            expected_scaled = orig.loc[valid_idx, b] * scale
            diff_scaled = np.abs(actual_scaled - expected_scaled)
            max_diff_scaled = diff_scaled.max()
            limit = 1.5 if dtype != "Float32" else 0.001
        else:
            max_diff_scaled = 0
            limit = 0

        results.append({
            "Band": b,
            "Type": dtype,
            "Scale": scale,
            "Mask_Mismatches": mask_diff,
            "Scaled_Clamped": scaled_clamped,
            "Max_Diff_Scaled": round(max_diff_scaled, 4),
            "Limit": limit
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
        cols = ["Band", "Type", "Scale", "Mask_Mismatches", "Scaled_Clamped", "Max_Diff_Scaled"]
        print(problems[cols].sort_values("Max_Diff_Scaled", ascending=False).to_string(index=False))
    else:
        print("\nALL BANDS MATCH SOURCE MASKS AND SCALE CORRECTLY.")

if __name__ == "__main__":
    analyze()
