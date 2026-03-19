import pandas as pd
import numpy as np

# Load the sampled data
df = pd.read_csv('03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_1000pts.csv')

# Identify all band columns (excluding system indices and geometry)
bands = [c for c in df.columns if c not in ["system:index", ".geo"]]

print(f"Analyzing {len(df)} points across {len(bands)} bands...")

# 1. Check for Mask Inconsistency
# Count how many points have NoData (-99999) in at least one band
is_nodata = (df[bands] == -99999)
any_nodata = is_nodata.any(axis=1)
all_nodata = is_nodata.all(axis=1)

# Flag inconsistent points: Some bands are NoData, but not all.
inconsistent = df[any_nodata & ~all_nodata]

print(f"\n--- MASK INCONSISTENCY ---")
print(f"Total points with some NoData: {any_nodata.sum()}")
print(f"Total points with all NoData (Ocean/Outside): {all_nodata.sum()}")
print(f"Points with inconsistent masking: {len(inconsistent)}")

if len(inconsistent) > 0:
    print("\nSample of inconsistent points (Bands with valid data where others are NoData):")
    # For each inconsistent row, show which bands have data
    for idx, row in inconsistent.head(10).iterrows():
        valid_in_row = [b for b in bands if row[b] != -99999]
        nodata_in_row = [b for b in bands if row[b] == -99999]
        print(f"  Point {idx}: {len(valid_in_row)} valid, {len(nodata_in_row)} NoData. First 3 valid: {valid_in_row[:3]}")

# 2. Check for Clamping Artifacts (-32000) or suspicious Zeros
print(f"\n--- VALUE ANOMALIES ---")
for b in bands:
    clamped_count = (df[b] == -32000).sum()
    zero_count = (df[b] == 0).sum()
    if clamped_count > 0 or zero_count > 0:
        print(f" {b:<25} | Clamped (-32000): {clamped_count:<4} | Zeros (0): {zero_count:<4}")

