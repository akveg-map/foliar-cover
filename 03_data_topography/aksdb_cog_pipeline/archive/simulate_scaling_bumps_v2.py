import pandas as pd
import numpy as np
import os

# Load 10k point raw dataset
csv_path = "assessment_orig_10000.csv"
if not os.path.exists(csv_path):
    csv_path = "03_data_topography/aksdb_cog_pipeline/assessment_orig_10000.csv"

df = pd.read_csv(csv_path)

# Surgical safe bumps
PROPOSALS = {
    "devmeanelev_4": 10000,
    "devmeanelev_16": 10000,
    "devmeanelev_32": 10000,
    "diffmeanelev_4": 1000,
    "relmeanelev_4": 1000,
    "relelev_4": 100,
    "relelev_16": 100
}

results = []
for band, new_scale in PROPOSALS.items():
    if band not in df.columns: continue
    series = df[band].replace(-99999.0, np.nan).dropna()
    if series.empty: continue
    
    raw_min, raw_max = series.min(), series.max()
    p25, p75 = np.percentile(series, [25, 75])
    iqr = p75 - p25
    
    # Count potential clamped points in the 10k sample
    clamped_count = ((series * new_scale).abs() > 32000).sum()
    clamped_pct = (clamped_count / len(series)) * 100
    
    clamping_status = "SAFE" if clamped_pct < 0.01 else f"RISK ({clamped_pct:.2f}%)"
    step_iqr = (1.0/new_scale) / iqr * 100 if iqr > 0 else 0
    
    results.append({
        "Band": band,
        "New Scale": new_scale,
        "Raw Min": round(raw_min, 4),
        "Raw Max": round(raw_max, 4),
        "Clamping": clamping_status,
        "New Step/IQR": f"{step_iqr:.4f}%"
    })

res_df = pd.DataFrame(results)
print(res_df.to_string(index=False))
