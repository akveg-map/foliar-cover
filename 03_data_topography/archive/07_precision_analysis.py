import pandas as pd
import numpy as np
import json

def analyze_precision():
    # Load config to get scales and types
    with open("03_data_topography/aksdb_cog_pipeline/scaling_config.json", "r") as f:
        config = json.load(f)

    print("Loading 10,000 point datasets...")
    orig = pd.read_csv("03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_orig_10000.csv")
    scaled = pd.read_csv("03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_scaled_10000.csv")
    
    # Ensure they are aligned by index
    orig = orig.sort_values("system:index").reset_index(drop=True)
    scaled = scaled.sort_values("system:index").reset_index(drop=True)
    
    gee_bands = [c for c in orig.columns if c not in ["system:index", ".geo", "control_band", "longitude", "latitude"]]
    
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
            continue
            
        cfg = config[orig_key]
        dtype = cfg["type"]
        scale = cfg["scale"]
        
        # We only care about Int16 conversions where precision loss happens
        if dtype != "Int16":
            continue

        # Get valid, unmasked data points where raw != 0 (to avoid division by zero in MAPE)
        orig_nodata = (orig[b] == -99999.0)
        scaled_nodata = (scaled[b] == -99999) | (scaled[b] == -32768) | (scaled[b] == -32000)
        is_clamped = ((scaled[b] == 32000) | (scaled[b] == -32000)) & ~orig_nodata
        
        valid_idx = ~orig_nodata & ~scaled_nodata & ~is_clamped & (orig[b] != 0)
        
        if not valid_idx.any():
            continue
            
        raw_vals = orig.loc[valid_idx, b]
        # Reconstruct scaled values to original units
        recon_vals = scaled.loc[valid_idx, b] / scale
        
        # 1. Unique Value Retention
        unique_raw = len(np.unique(raw_vals))
        unique_scaled = len(np.unique(recon_vals))
        retention = (unique_scaled / unique_raw) * 100 if unique_raw > 0 else 0
        
        # 2. Global Absolute Percentage Error
        abs_err = np.abs(raw_vals - recon_vals)
        rel_err = (abs_err / np.abs(raw_vals)) * 100
        global_mape = rel_err.median()
        
        # 3. IQR specific analysis
        p25, p75 = np.percentile(raw_vals, [25, 75])
        iqr_mask = (raw_vals >= p25) & (raw_vals <= p75)
        
        if iqr_mask.any():
            iqr_rel_err = rel_err[iqr_mask]
            iqr_mape = iqr_rel_err.median()
            iqr_max_err = iqr_rel_err.max()
        else:
            iqr_mape = 0
            iqr_max_err = 0

        results.append({
            "Band": b,
            "Scale": scale,
            "Unq_Raw": unique_raw,
            "Unq_Scaled": unique_scaled,
            "Retention_%": round(retention, 1),
            "Global_MAPE_%": round(global_mape, 2),
            "IQR_MAPE_%": round(iqr_mape, 2),
            "IQR_Max_Err_%": round(iqr_max_err, 2)
        })

    res_df = pd.DataFrame(results)
    
    # Flag criteria: Severe stepping (< 5% retention) OR high error in typical landscape (> 5% IQR MAPE)
    flagged = res_df[(res_df["Retention_%"] < 5.0) | (res_df["IQR_MAPE_%"] > 5.0)]
    
    print("\n--- PRECISION LOSS ANALYSIS ---")
    print(res_df.sort_values("IQR_MAPE_%", ascending=False).to_string(index=False))
    
    print("\n--- FLAGGED BANDS (Potential Gradient Loss) ---")
    if not flagged.empty:
        print(flagged.to_string(index=False))
        print("\nRecommendation: Consider analyzing these bands further. If local gradients")
        print("within the IQR are functionally critical to the model, Float32 may be required.")
    else:
        print("None. All Int16 scaled bands maintain acceptable relative precision across their typical range.")

if __name__ == "__main__":
    analyze_precision()
