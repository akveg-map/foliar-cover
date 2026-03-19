import pandas as pd
import numpy as np
import json
import os

def analyze():
    # 1. Load data and crosswalk
    cw_path = "03_data_topography/aksdb_cog_pipeline/metadata_crosswalk.csv"
    raw_path = "03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_orig_10000.csv"
    scaled_path = "03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_scaled_10000.csv"
    
    df_cw = pd.read_csv(cw_path)
    df_raw = pd.read_csv(raw_path)
    df_scaled = pd.read_csv(scaled_path)
    
    df_raw = df_raw.sort_values("system:index").reset_index(drop=True)
    df_scaled = df_scaled.sort_values("system:index").reset_index(drop=True)
    
    print(f"Analyzing 111 bands (10,000 points) with POSITIVE-ONLY HEALING for Fluvial...")
    results = []

    for _, row in df_cw.iterrows():
        r_id = row['raw_id']
        s_id = row['scaled_id']
        scale = row['scale']
        dtype = row['data_type']
        
        b_raw = f"{r_id.replace('.', 'p')}"
        b_scaled = f"{s_id.replace('.', 'p')}_B0"
        
        if b_raw not in df_raw.columns and f"{b_raw}_B0" in df_raw.columns:
            b_raw = f"{b_raw}_B0"
        if b_scaled not in df_scaled.columns and s_id.replace('.', 'p') in df_scaled.columns:
            b_scaled = s_id.replace('.', 'p')

        if b_raw not in df_raw.columns or b_scaled not in df_scaled.columns:
            continue

        raw_vals_full = df_raw[b_raw]
        scaled_vals_full = df_scaled[b_scaled]
        nodata_internal = -32768 if dtype == "Int16" else (-99999.0 if dtype == "Float32" else 0)

        def get_stats(raw_in, scaled_in, fluvial_healing=False):
            # Standard GEE NoData
            r_mask = (raw_in == -99999)
            s_mask = (scaled_in == -99999) | (scaled_in == nodata_internal)
            
            # FLUVIAL HEALING: Metrics like DFA/SPI should be positive. 
            # Ocean/NoData values are messy negatives in source.
            if fluvial_healing:
                r_mask = r_mask | (raw_in < 0)
                s_mask = s_mask | (scaled_in < 0)
            
            mask_err = (r_mask != s_mask).sum()
            valid_idx = ~r_mask & ~s_mask
            
            if not valid_idx.any():
                return mask_err, 0, 0, 0
                
            v_raw = raw_in[valid_idx]
            v_scaled = scaled_in[valid_idx]
            v_recon = v_scaled / scale
            
            abs_err = np.abs(v_raw - v_recon)
            rmse = np.sqrt((abs_err**2).mean())
            max_err = abs_err.max()
            clamped = ((v_scaled >= 32000) | (v_scaled <= -32000)).sum()
            return mask_err, rmse, max_err, (clamped / len(v_raw) * 100)

        # Standard Comparison
        m_err, rmse, max_e, clamp_pct = get_stats(raw_vals_full, scaled_vals_full, fluvial_healing=False)
        results.append({
            "Band": r_id,
            "Type": dtype,
            "Scale": scale,
            "Mask_Err": m_err,
            "RMSE": rmse,
            "Max_Err": max_e,
            "Tol": 0.5001 / scale if scale != 0 else 0,
            "Clamped_%": round(clamp_pct, 2),
            "Status": "Raw"
        })

        # Healed Comparison (Only for dfa/spi)
        if r_id in ['dfa', 'spi']:
            m_err_h, rmse_h, max_e_h, clamp_pct_h = get_stats(raw_vals_full, scaled_vals_full, fluvial_healing=True)
            results.append({
                "Band": r_id + " (Healed)",
                "Type": dtype,
                "Scale": scale,
                "Mask_Err": m_err_h,
                "RMSE": rmse_h,
                "Max_Err": max_e_h,
                "Tol": 0.5001 / scale,
                "Clamped_%": round(clamp_pct_h, 2),
                "Status": "Fixed"
            })

    res_df = pd.DataFrame(results)
    
    print("\n--- POINT-BY-POINT SCALING ASSESSMENT ---")
    cols = ["Band", "Scale", "Mask_Err", "RMSE", "Max_Err", "Tol", "Clamped_%"]
    # Show clean table (Healed version for problematic ones)
    clean_df = res_df[~((res_df["Band"].isin(['dfa', 'spi'])) & (res_df["Status"] == "Raw"))]
    print(clean_df[cols].sort_values("RMSE", ascending=False).head(20).to_string(index=False))
    
    fluvial = res_df[res_df["Band"].str.contains("dfa|spi")]
    print("\n--- FLUVIAL (DFA/SPI) VERIFICATION DETAIL ---")
    print(fluvial[cols].to_string(index=False))

if __name__ == "__main__":
    analyze()
