import pandas as pd
import numpy as np
import os

# Load 10k point raw dataset
csv_path = "03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_orig_10000.csv"

df = pd.read_csv(csv_path)

PROPOSALS = {
    "planc": 1000000,
    "no": 100000,
    "po": 100000,
    "pisrdir": 10000,
    "devmeanelev": 10000,
    "diffmeanelev": 1000,
    "relmeanelev": 1000,
    "relelev": 100,
    "vrm": 1000000,
    "dis": 1000
}

results = []
# Sort proposals to keep output clean
for prefix in sorted(PROPOSALS.keys()):
    new_scale = PROPOSALS[prefix]
    # Find all columns matching this prefix
    cols = [c for c in df.columns if c.startswith(prefix)]
    for c in cols:
        series = df[c].replace(-99999.0, np.nan).dropna()
        if series.empty: continue
        
        raw_min, raw_max = series.min(), series.max()
        p25, p75 = np.percentile(series, [25, 75])
        iqr = p75 - p25
        
        sim_min = raw_min * new_scale
        sim_max = raw_max * new_scale
        
        # Count potential clamped points in the 10k sample
        clamped_count = ((series * new_scale).abs() > 32000).sum()
        clamped_pct = (clamped_count / len(series)) * 100
        
        clamping_status = "SAFE" if clamped_pct < 0.1 else f"RISK ({clamped_pct:.2f}%)"
        
        step_iqr = (1.0/new_scale) / iqr * 100 if iqr > 0 else 0
        
        results.append({
            "Band": c,
            "New Scale": new_scale,
            "Raw Min": round(raw_min, 4),
            "Raw Max": round(raw_max, 4),
            "Sim Min": round(sim_min, 1),
            "Sim Max": round(sim_max, 1),
            "Clamping": clamping_status,
            "New Step/IQR": f"{step_iqr:.4f}%"
        })

res_df = pd.DataFrame(results)
print(res_df.to_string(index=False))
