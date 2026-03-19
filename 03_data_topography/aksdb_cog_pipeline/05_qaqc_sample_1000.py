import ee
import pandas as pd
import json
import os

PROJECT_ID = "akveg-map"
COLLECTION_ID = f"projects/{PROJECT_ID}/assets/topography/aksdb_dem_covars_v20250422_scaled_i32"
BASELINE_CSV = "03_data_topography/aksdb_cog_pipeline/qaqc_data/assessment_orig_35000.csv"
SCALING_CONFIG = "03_data_topography/aksdb_cog_pipeline/scaling_config.json"

def main():
    ee.Initialize(project=PROJECT_ID)
    
    with open(SCALING_CONFIG, 'r') as f:
        full_config = json.load(f)
    
    # Validation Sample: 11 Step 2 + 9 Step 3 (total 20 diverse variables)
    val_vars = [
        'ca_10', 'aspct_4', 'ci_16', 'crosc_32', 'dah', 
        'devmeanelev_4', 'gmrph_ms_30', 'hs_st', 
        'pisrdir_2023-06-22', 'sl_16', 'swi_10000',
        'twi', 'vlyd', 'vrm_32', 'mbi_0.001', 'minelev_4',
        'diffmeanelev_32', 'pisrdif_2023-03-22', 'planc_16', 'relelev_4'
    ]
    
    var_map = {}
    for var in val_vars:
        group = next((k for k in sorted(full_config.keys(), key=len, reverse=True) if var.startswith(k)), None)
        if group:
            suffix = full_config[group]["suffix"]
            scale = full_config[group]["scale"]
            clean_var = var.replace(".", "p")
            var_map[var] = {"scaled_name": f"{clean_var}{suffix}", "scale": scale}
    
    df = pd.read_csv(BASELINE_CSV)
    df_terrestrial = df[df['ca_10_B0'].notnull()]
    df_valid = df_terrestrial.sample(n=100, random_state=42).copy()
        
    print(f"Sampling 100 random points across {len(val_vars)} diverse variables...")

    features = []
    for idx, row in df_valid.iterrows():
        geom = ee.Geometry.Point([row['longitude'], row['latitude']])
        feat = ee.Feature(geom, {'orig_index': str(row['system:index'])})
        for var in val_vars:
            col = f"{var}_B0"
            val = row.get(col)
            if pd.notna(val):
                feat = feat.set(f"orig_{var.replace('.', 'p')}", float(val))
        features.append(feat)
    
    fc = ee.FeatureCollection(features)
    
    # Initialize combined image
    first_var = val_vars[0]
    combined_image = ee.Image(f"{COLLECTION_ID}/{var_map[first_var]['scaled_name']}").rename(first_var.replace(".", "p"))
    for var in val_vars[1:]:
        img = ee.Image(f"{COLLECTION_ID}/{var_map[var]['scaled_name']}").rename(var.replace(".", "p"))
        combined_image = combined_image.addBands(img)
    
    # Sample in ONE call
    props_to_keep = ['orig_index'] + [f"orig_{v.replace('.', 'p')}" for v in val_vars]
    sampled_fc = combined_image.sampleRegions(
        collection=fc,
        properties=props_to_keep,
        scale=10,
        geometries=False
    )
    
    results = sampled_fc.getInfo()['features']
    print(f"Sampling returned {len(results)} points.")

    errors = 0
    matches = 0
    
    for f in results:
        res = f['properties']
        for var in val_vars:
            clean_var = var.replace(".", "p")
            orig_val = res.get(f"orig_{clean_var}")
            new_val = res.get(clean_var)
            scale = var_map[var]['scale']
            
            if orig_val is not None and new_val is not None:
                expected = float(orig_val) * scale
                if abs(new_val - expected) < 1.0:
                    matches += 1
                else:
                    errors += 1
                    if errors < 10:
                        print(f"Mismatch in {var}: Orig={orig_val}, New={new_val}, Expected={expected}")

    print(f"\nResults Summary:")
    print(f"Successful Matches: {matches}")
    print(f"Mismatches (Error): {errors}")
    
    if errors == 0 and matches > 0:
        print("\nSUCCESS: All sampled values match original values.")
    else:
        print(f"\nFAILURE: Found {errors} mismatches.")

if __name__ == "__main__":
    main()
