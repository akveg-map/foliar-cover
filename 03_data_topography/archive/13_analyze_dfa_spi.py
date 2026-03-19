import pandas as pd
import numpy as np

def analyze():
    df = pd.read_csv('03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_scaled_10000.csv')
    
    # Map raw band names to GEE extract column names
    targets = {
        'dfa': 'dfa_0p1_B0',
        'spi': 'spi_0p1_B0'
    }
    
    print("--- DFA and SPI Distribution Analysis (10,000 points) ---")
    for raw_name, col in targets.items():
        if col not in df.columns:
            print(f"Column {col} not found in CSV.")
            continue
            
        data = df[col]
        # Drop empty/NaN and exclude NoData (-99999 from GEE unmask, -32768 internal)
        valid = data.dropna()
        valid = valid[(valid != -99999) & (valid != -32768)]
        
        if valid.empty:
            print(f"{raw_name}: No valid pixels in sample.")
            continue
            
        # Stats in Scaled Units (Int16)
        s_min, s_max = valid.min(), valid.max()
        # Explicitly use numeric values for numpy
        vals = valid.values.astype(float)
        s_p05, s_p50, s_p95 = np.percentile(vals, [5, 50, 95])
        clamped = ((valid >= 32000) | (valid <= -32000)).sum()
        
        # Stats in Physical Units (Original)
        scale = 0.1
        p_min, p_max = s_min / scale, s_max / scale
        p_p50 = s_p50 / scale
        
        print(f"\n[{raw_name.upper()}]")
        print(f"  Scaled (Int16): Min={s_min}, Max={s_max}, Median={s_p50}, P05={s_p05}, P95={s_p95}")
        print(f"  Physical:       Min={p_min:.2f}, Max={p_max:.2f}, Median={p_p50:.2f}")
        print(f"  Clamping:       {clamped} points ({clamped/len(valid)*100:.2f}%)")
        
        # Check if 0.1 scale is too high or too low
        # If max is very low (e.g. 500), we could increase scale.
        # If clamping is high, we must decrease scale.

if __name__ == "__main__":
    analyze()
