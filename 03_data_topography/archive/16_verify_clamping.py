import pandas as pd
import numpy as np

def verify():
    df = pd.read_csv('03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_orig_10000.csv')
    
    print("--- DFA/SPI Clamping Verification ---")
    for b in ['dfa', 'spi']:
        data = df[b]
        # Only check terrestrial land (positives)
        land = data[data > 0]
        # Int16 limit at scale 10.0 is 32767 / 10 = 3276.7
        clamped = (land > 3276.7).sum()
        print(f"{b.upper()}: {clamped} of {len(land)} land points (>3276.7) clamped ({clamped/len(land)*100:.2f}%)")
        print(f"  Max physical value in sample: {land.max():.2f}")

    print("\n--- PISR Variable Inspection ---")
    pisr_cols = [c for c in df.columns if 'pisr' in c]
    for c in sorted(pisr_cols):
        print(c)

if __name__ == "__main__":
    verify()
