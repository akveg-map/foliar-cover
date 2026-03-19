import pandas as pd
import numpy as np

def debug_fluvial():
    df_raw = pd.read_csv('03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_orig_10000.csv')
    df_scaled = pd.read_csv('03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_scaled_10000.csv')
    
    # Align
    df_raw = df_raw.sort_values("system:index").reset_index(drop=True)
    df_scaled = df_scaled.sort_values("system:index").reset_index(drop=True)
    
    targets = ['dfa', 'spi']
    for t in targets:
        print(f"\n--- DEBUGGING {t.upper()} ---")
        r_vals = df_raw[t]
        s_vals = df_scaled[f"{t}_10_B0"]
        
        # Find where scaled is valid but raw is extreme
        mask_s = (s_vals == -32768) | (s_vals == -99999)
        bad_idx = (r_vals < -1000) & ~mask_s
        
        if bad_idx.any():
            print(f"Found {bad_idx.sum()} points where Raw is extreme (< -1000) but Scaled is NOT NoData.")
            print("Sample of Raw values at these points:")
            print(r_vals[bad_idx].head(10).tolist())
            print("Sample of Scaled values at these points:")
            print(s_vals[bad_idx].head(10).tolist())
        else:
            print("No points found where Raw is extreme and Scaled is data.")
            
        # Check reverse: where raw is valid but scaled is extreme
        bad_idx_rev = (r_vals > -1000) & mask_s
        if bad_idx_rev.any():
            print(f"Found {bad_idx_rev.sum()} points where Raw is valid but Scaled is NoData.")
            print("Sample of Raw values at these points:")
            print(r_vals[bad_idx_rev].head(10).tolist())

if __name__ == "__main__":
    debug_fluvial()
