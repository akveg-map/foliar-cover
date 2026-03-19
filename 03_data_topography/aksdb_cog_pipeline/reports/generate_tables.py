import pandas as pd
import numpy as np
import json
import re
import os

def sort_key(row):
    group = row["Group"]
    name = row["Variable Name"]
    abbr = row["Abbr"]
    param_str = str(row["Param"])
    prio = 0 if row["Out Type"] != "Byte" else 1
    if "pisr" in abbr:
        p_type = "0_direct" if "dir" in abbr else "1_diffuse"
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", param_str)
        date_val = date_match.group(1) if date_match else "0000-00-00"
        return (prio, group, "pisr", p_type, date_val)
    try:
        match = re.search(r"([0-9.]+)", param_str)
        param_num = float(match.group(1)) if match else 0
    except:
        param_num = 0
    base_name = name.split(" (")[0]
    return (prio, group, base_name, param_num)

def format_num(val):
    if pd.isna(val): return "N/A"
    if isinstance(val, str): return val
    if abs(val) < 0.0001 and val != 0: return f"{val:.6f}"
    if abs(val) > 1000: return f"{val:,.1f}"
    return f"{val:.4f}"

def format_section(group_name, df):
    cols = ["Variable Name", "Abbr", "Suffix", "Res", "Variable Abbr<br>to Name Match", "Raw GB", "Scaled GB", "Scale", "Type", "% Clamp", "Step/IQR"]
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
    md.append("\n: {tbl-colwidths=\"[24,10,8,5,10,7,7,10,7,7,7]\"}")
    return "\n".join(md)

def main():
    with open("03_data_topography/aksdb_cog_pipeline/scaling_config.json", "r") as f:
        config = json.load(f)
    with open("03_data_topography/aksdb_cog_pipeline/reports/file_sizes.json", "r") as f:
        sizes = json.load(f)
    cw = pd.read_csv("03_data_topography/aksdb_cog_pipeline/metadata_crosswalk.csv")
    
    orig_path = "03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_orig_35000.csv"
    scaled_path = "03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_scaled_35000.csv"
    
    if not os.path.exists(orig_path) or not os.path.exists(scaled_path):
        print("WARNING: 35k datasets missing, falling back to 10k")
        orig_path = "03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_orig_10000.csv"
        scaled_path = "03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_scaled_10000.csv"

    orig_35k = pd.read_csv(orig_path)
    scaled_35k = pd.read_csv(scaled_path)

    orig_35k = orig_35k.sort_values("system:index").reset_index(drop=True)
    scaled_35k = scaled_35k.sort_values("system:index").reset_index(drop=True)

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
        
        b_raw_base = raw_id.replace(".", "p")
        b_raw = next((c for c in orig_35k.columns if c == b_raw_base or c == f"{b_raw_base}_B0"), None)
        
        b_scaled_base = scaled_id.replace(".", "p")
        b_scaled = next((c for c in scaled_35k.columns if c == b_scaled_base or c == f"{b_scaled_base}_B0"), None)

        if b_raw and b_scaled:
            raw_series = orig_35k[b_raw]
            scaled_series = scaled_35k[b_scaled]
            
            valid_mask = (raw_series.notna()) & (raw_series > -90000)
            if raw_id in ["dfa", "spi", "fel"]:
                valid_mask = valid_mask & (raw_series > 0)
                
            v_orig = raw_series[valid_mask]
            v_scaled = scaled_series[valid_mask]
            
            if not v_orig.empty:
                if "Int" in out_dtype:
                    max_int = 2147483647 if "Int32" in out_dtype else 32767
                    is_clamped = (v_scaled.abs() >= (max_int - 100))
                    clamped_pts = (is_clamped.sum() / len(v_orig)) * 100
                    
                    p25, p75 = np.percentile(v_orig, [25, 75])
                    iqr = p75 - p25
                    if iqr > 0:
                        prec_iqr = "{:.4f}%".format(((1.0/scale) / iqr) * 100)
                    else:
                        prec_iqr = "0.0000%"
                else:
                    prec_iqr = "Perfect"

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
            "Out Type": out_dtype.replace("Float32","F32").replace("Int16","I16").replace("Int32","I32"),
            "% Clamped": clamped_pts,
            "IQR Max Error": prec_iqr
        })

    df = pd.DataFrame(data)
    df["sort_key"] = df.apply(sort_key, axis=1)
    df = df.sort_values("sort_key")

    # Group by category and write individual tables
    for cat in df["Group"].unique():
        # Normalize category name for filename
        cat_norm = str(cat).lower().replace(" ", "_").replace("/", "_")
        out_file = f"03_data_topography/aksdb_cog_pipeline/reports/table_{cat_norm}.md"
        
        cat_df = df[df["Group"] == cat]
        
        # Split into Continuous and Categorical within the category if needed?
        # The prompt says "write individual markdown files for each category".
        # I'll keep the Continuous/Categorical separation if they exist in the category.
        
        with open(out_file, "w") as f:
            cont_df = cat_df[cat_df["Out Type"] != "Byte"]
            if not cont_df.empty:
                f.write(f"### {cat} - Continuous\n\n")
                f.write(format_section(cat, cont_df))
                f.write("\n\n")
            
            cat_byte_df = cat_df[cat_df["Out Type"] == "Byte"]
            if not cat_byte_df.empty:
                f.write(f"### {cat} - Categorical\n\n")
                f.write(format_section(cat, cat_byte_df))
                f.write("\n\n")

    total_raw_tb = df["Raw GB"].sum() / 1024
    total_scaled_tb = df["Scaled GB"].sum() / 1024
    reduction = (1 - (total_scaled_tb / total_raw_tb)) * 100

    with open("03_data_topography/aksdb_cog_pipeline/reports/size_summary.md", "w") as f:
        f.write("| Metric | Value |\n")
        f.write("| :--- | :---: |\n")
        f.write(f"| Total Raw Size | {total_raw_tb:.2f} TB |\n")
        f.write(f"| Total Scaled Size | {total_scaled_tb:.2f} TB |\n")
        f.write(f"| Storage Reduction | {reduction:.1f}% |\n")

if __name__ == "__main__":
    main()
