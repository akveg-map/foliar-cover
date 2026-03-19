import pandas as pd
import numpy as np
import json

def analyze():
    # Load config to get scales and suffixes
    with open("03_data_topography/cog_conversion/scaling_config.json", "r") as f:
        config = json.load(f)

    orig = pd.read_csv("03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_orig_final.csv")
    scaled = pd.read_csv("03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_scaled_final.csv")
    
    # Ensure they are aligned by index
    orig = orig.sort_values("system:index").reset_index(drop=True)
    scaled = scaled.sort_values("system:index").reset_index(drop=True)
    
    # GEE band names in CSV have dots replaced with 'p'
    gee_bands = [c for c in orig.columns if c not in ["system:index", ".geo"]]
    
    results = []
    
    # Sort config keys by length descending to match longest prefix first (e.g. mbi_0.001 before mbi)
    config_keys_sorted = sorted(config.keys(), key=len, reverse=True)

    for b in gee_bands:
        # Find the original config key that matches this GEE band name
        orig_key = None
        for key in config_keys_sorted:
            # Match if the band name starts with the key (replacing . with p)
            # and is followed by an underscore or is an exact match
            safe_key = key.replace(".", "p")
            if b == safe_key or b.startswith(safe_key + "_"):
                orig_key = key
                break
        
        if not orig_key:
            # Fallback for simple names
            orig_key = b
            scale = 1.0
        else:
            scale = config[orig_key]["scale"]

        # 1. Mask Check
        orig_mask = (orig[b] == -99999)
        scaled_nodata = (scaled[b] == -99999) | (scaled[b] == -32000) | (scaled[b] == -32768)
        mask_diff = (orig_mask != scaled_nodata).sum()
        
        # 2. Clamping check
        is_clamped = (scaled[b] == 32000) | ((scaled[b] == -32000) & ~orig_mask)
        scaled_clamped = is_clamped.sum()
        
        # 3. Value Accuracy Check
        valid_idx = ~orig_mask & ~scaled_nodata & ~is_clamped
        if valid_idx.any():
            actual_scaled = scaled.loc[valid_idx, b]
            expected_scaled = orig.loc[valid_idx, b] * scale
            diff_scaled = np.abs(actual_scaled - expected_scaled)
            max_diff_scaled = diff_scaled.max()
            limit = 1.5 # Allow slight buffer for rounding
        else:
            max_diff_scaled = 0
            limit = 0

        results.append({
            "Band": b,
            "Scale": scale,
            "Mask_Mismatches": mask_diff,
            "Scaled_Clamped": scaled_clamped,
            "Max_Diff_Scaled": round(max_diff_scaled, 4),
            "Limit": limit
        })
        
    res_df = pd.DataFrame(results)
    
    # Print problematic bands
    problems = res_df[
        (res_df["Mask_Mismatches"] > 0) | 
        (res_df["Scaled_Clamped"] > 0) | 
        (res_df["Max_Diff_Scaled"] > res_df["Limit"])
    ]
    
    print(f"Total Bands Analyzed: {len(gee_bands)}")
    print(f"Bands with REAL Issues: {len(problems)}")
    
    if not problems.empty:
        print("\n--- PROBLEM DETAIL ---")
        cols = ["Band", "Scale", "Mask_Mismatches", "Scaled_Clamped", "Max_Diff_Scaled"]
        print(problems[cols].sort_values("Max_Diff_Scaled", ascending=False).to_string(index=False))
    else:
        print("\nALL BANDS MATCH SOURCE MASKS AND SCALE CORRECTLY.")

if __name__ == "__main__":
    analyze()
