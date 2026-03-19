import pandas as pd
import numpy as np

def inspect_raw_negatives():
    df = pd.read_csv('03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_orig_10000.csv')
    bands = ['dfa', 'spi', 'fel']
    
    for b in bands:
        if b not in df.columns:
            print(f"Band {b} not in raw dataset.")
            continue
            
        data = df[b]
        # Filter for values < 0 that are NOT -99999
        # Need to be careful with floating point comparison for -99999.0
        neg_artifacts = data[(data < 0) & (np.abs(data - (-99999.0)) > 0.1)]
        
        print(f"\n--- {b.upper()} RAW DATA INSPECTION ---")
        if neg_artifacts.empty:
            print("No negative artifacts found (only -99999 or positive data).")
        else:
            print(f"Found {len(neg_artifacts)} artifact points (Negative but not -99999).")
            print("Top 10 unique values:")
            print(neg_artifacts.value_counts().sort_index().head(10))
            print("\nStatistics of these artifacts:")
            print(neg_artifacts.describe())

if __name__ == "__main__":
    inspect_raw_negatives()
