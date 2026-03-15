import pandas as pd
import numpy as np
import json
import re

def sort_key(row):
    group = row["Group"]
    name = row["Variable Name"]
    abbr = row["Abbr"]
    param_str = str(row["Param"])
    
    # Priority 1: Categorical vs Continuous
    prio = 0 if row["Out Type"] != "Byte" else 1
    
    # Priority 2: Group (Maintain alphabetical groups)
    
    # Priority 3: Within Group Sorting
    # Handle PISR: Type first, then Date
    if "pisr" in abbr:
        p_type = "0_direct" if "dir" in abbr else "1_diffuse"
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", param_str)
        date_val = date_match.group(1) if date_match else "0000-00-00"
        return (prio, group, "pisr", p_type, date_val)
    
    # Handle Numerical Params (Window/Radius)
    try:
        match = re.search(r"([0-9.]+)", param_str)
        param_num = float(match.group(1)) if match else 0
    except:
        param_num = 0
        
    # Base name for grouping similar variables
    base_name = name.split(" (")[0]
    return (prio, group, base_name, param_num)

def format_section(group_name, df):
    cols = ["Variable Name", "Abbr", "Suffix", "Res", "Match", "Raw GB", "Scaled GB", "Scale", "Type", "% Clamp", "Step/IQR"]
    md = [f"#### {group_name}\n"]
    md.append("| " + " | ".join(cols) + " |")
    md.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    
    for _, row in df.iterrows():
        scale_val = row["Scale"]
        scale_str = "{:,.0f}".format(scale_val) if scale_val >= 1 else "{:g}".format(scale_val)
        
        r = [
            str(row["Variable Name"]),
            str(row["Abbr"]),
            str(row["Suffix"]),
            str(row["Res"]),
            str(row["Match"]),
            "{:.1f}".format(row["Raw GB"]),
            "{:.1f}".format(row["Scaled GB"]),
            scale_str,
            str(row["Out Type"]),
            "{:.2f}%".format(row["% Clamped"]),
            str(row["IQR Max Error"])
        ]
        md.append("| " + " | ".join(r) + " |")
    md.append("\n: {tbl-colwidths=\"[24,10,8,5,8,7,7,10,7,7,7]\"}")
    return "\n".join(md)

# Load inputs
with open("03_data_topography/cog_pipeline/scaling_config.json", "r") as f:
    config = json.load(f)
with open("03_data_topography/cog_pipeline/reports/file_sizes.json", "r") as f:
    sizes = json.load(f)
cw = pd.read_csv("03_data_topography/cog_pipeline/metadata_crosswalk.csv")
orig_10k = pd.read_csv("assessment_orig_10000.csv")
scaled_10k = pd.read_csv("assessment_scaled_10000.csv")

orig_10k = orig_10k.sort_values("system:index").reset_index(drop=True)
scaled_10k = scaled_10k.sort_values("system:index").reset_index(drop=True)

data = []
config_keys_sorted = sorted(config.keys(), key=len, reverse=True)

for _, row in cw.iterrows():
    raw_id = row["raw_id"]
    scaled_id = row["scaled_id"]
    scale = row["scale"]
    out_dtype = row["data_type"]
    
    suffix = "N/A"
    for key in config_keys_sorted:
        if raw_id.startswith(key):
            suffix = config[key].get("suffix", "N/A")
            break

    raw_gb = sizes["raw"].get(raw_id, 0) / (1024**3)
    scaled_gb = sizes["scaled"].get(scaled_id, 0) / (1024**3)
    
    clamped_pts, prec_iqr = 0.0, "N/A"
    b_raw = raw_id.replace(".", "p")
    b_scaled = scaled_id.replace(".", "p")
    
    if b_raw not in orig_10k.columns and f"{b_raw}_B0" in orig_10k.columns: b_raw = f"{b_raw}_B0"
    if b_scaled not in scaled_10k.columns and f"{b_scaled}_B0" in scaled_10k.columns: b_scaled = f"{b_scaled}_B0"

    if b_raw in orig_10k.columns and b_scaled in scaled_10k.columns:
        raw_series = orig_10k[b_raw]
        scaled_series = scaled_10k[b_scaled]
        valid_mask = (raw_series.notna()) & (raw_series != -99999.0)
        
        # HEALING: For fluvial/indices, only terrestrial (positive) values are valid for stats
        if raw_id in ['dfa', 'spi', 'fel']:
            valid_mask = valid_mask & (raw_series > 0)
            
        v_orig = raw_series[valid_mask]
        v_scaled = scaled_series[valid_mask]
        
        if not v_orig.empty:
            if "Int16" in out_dtype:
                clamped = (v_scaled >= 32000) | (v_scaled <= -32000)
                clamped_pts = (clamped.sum() / len(v_orig)) * 100
                p25, p75 = np.percentile(v_orig, [25, 75])
                iqr = p75 - p25
                if iqr > 0:
                    prec_iqr = "{:.4f}%".format(((1.0/scale) / iqr) * 100)
                else: prec_iqr = "0.0000%"
            else: prec_iqr = "Perfect"

    data.append({
        "Group": row["category"],
        "Variable Name": row["title"],
        "Param": row["neighborhood"],
        "Abbr": raw_id,
        "Suffix": suffix,
        "Res": row["res"],
        "Match": row["match_type"],
        "Raw GB": raw_gb,
        "Scaled GB": scaled_gb,
        "Scale": scale,
        "Out Type": out_dtype.replace("Float32","F32").replace("Int16","I16"),
        "% Clamped": clamped_pts,
        "IQR Max Error": "Perfect" if out_dtype == "Byte" else prec_iqr
    })

df = pd.DataFrame(data)
df["sort_key"] = df.apply(sort_key, axis=1)
df = df.sort_values("sort_key")

with open("03_data_topography/cog_pipeline/reports/summary_tables.md", "w") as f:
    f.write("### Continuous Covariates Summary\n\n")
    cont_df = df[df["Out Type"] != "Byte"]
    for g in sorted(cont_df["Group"].unique()):
        f.write(format_section(g, cont_df[cont_df["Group"] == g]))
        f.write("\n\n")
    
    f.write("### Categorical Covariates Summary\n\n")
    cat_df = df[df["Out Type"] == "Byte"]
    for g in sorted(cat_df["Group"].unique()):
        f.write(format_section(g, cat_df[cat_df["Group"] == g]))
        f.write("\n\n")

total_raw_tb = df["Raw GB"].sum() / 1024
total_scaled_tb = df["Scaled GB"].sum() / 1024
reduction = (1 - (total_scaled_tb / total_raw_tb)) * 100

with open("03_data_topography/cog_pipeline/reports/size_summary.md", "w") as f:
    f.write("| Metric | Value |\n")
    f.write("| :--- | :---: |\n")
    f.write(f"| Total Raw Size | {total_raw_tb:.2f} TB |\n")
    f.write(f"| Total Scaled Size | {total_scaled_tb:.2f} TB |\n")
    f.write(f"| Storage Reduction | {reduction:.1f}% |\n")
