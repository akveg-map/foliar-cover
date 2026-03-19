import ee
import pandas as pd
import sys
import time
import json

PROJECT_ID = "akveg-map"
ee.Initialize(project=PROJECT_ID)

def sync_collection(collection_id, filename_col, gcs_root, crosswalk_df, description, config=None):
    """Synchronizes a GEE collection to match the crosswalk exactly."""
    print(f"\n--- Syncing {description} ---")
    
    # 1. Ensure collection exists
    try:
        ee.data.createAsset({'type': 'ImageCollection'}, collection_id)
        print(f"Created collection: {collection_id}")
    except ee.EEException as e:
        if "already exists" in str(e).lower() or "cannot overwrite" in str(e).lower():
            print(f"Collection exists: {collection_id}")
        else:
            raise e

    # 2. Map intended assets
    intended_assets = {}
    config_keys_sorted = sorted(config.keys(), key=len, reverse=True) if config else []
    
    for _, row in crosswalk_df.iterrows():
        raw_id = row['raw_id']
        
        if config:
            # Dynamically determine the scaled filename and properties
            img_id = row['scaled_id']
            # Extract properties from config for consistency
            group = next((k for k in config_keys_sorted if raw_id.startswith(k)), None)
            if not group:
                print(f"WARNING: No config group found for {raw_id}")
                continue
            cfg = config[group]
            scale_factor = float(cfg['scale'])
            data_type = cfg['type']
            
            # Determine nodata
            if data_type == 'Int32': nodata = -2147483648
            elif data_type == 'Int16': nodata = -32768
            else: nodata = 0 # Byte
        else:
            # Raw properties
            img_id = row[filename_col]
            scale_factor = 1.0
            data_type = 'Float32' # Most raw are float
            nodata = -99999.0
            
        asset_id = f"{collection_id}/{img_id.replace('.', 'p')}"
        
        properties = {
            'title': row['title'],
            'category': row['category'],
            'variable_prefix': row['prefix'],
            'neighborhood': str(row['neighborhood']),
            'scale_factor': scale_factor,
            'data_type': data_type,
            'match_verification': row['match_type'],
            'project': 'AKVEG',
            'source_version': 'v20250422',
            'nodata_value': nodata
        }
        
        intended_assets[asset_id] = {
            'gcs_path': f"{gcs_root}{img_id}.tif",
            'properties': properties
        }

    # 3. List current assets
    try:
        existing_assets = [a['id'] for a in ee.data.listAssets({'parent': collection_id})['assets']]
    except Exception:
        existing_assets = []
    
    print(f"Current assets in GEE: {len(existing_assets)}")
    print(f"Intended assets: {len(intended_assets)}")

    # 4. Remove obsolete assets
    obsolete = [a for a in existing_assets if a not in intended_assets]
    if obsolete:
        print(f"Removing {len(obsolete)} obsolete assets...")
        for a_id in obsolete:
            try:
                ee.data.deleteAsset(a_id)
                print(f"  Deleted: {a_id}")
            except Exception as e:
                print(f"  Failed to delete {a_id}: {e}")

    # 5. Register/Update assets
    for idx, (a_id, info) in enumerate(intended_assets.items()):
        try:
            # Check if exists
            ee.data.getAsset(a_id)
            # Update properties
            ee.data.setAssetProperties(a_id, info['properties'])
        except ee.EEException:
            # Create new
            try:
                request = {
                    'type': 'IMAGE',
                    'gcs_location': {'uris': [info['gcs_path']]},
                    'properties': info['properties']
                }
                ee.data.createAsset(request, a_id)
                print(f"[{idx+1}/{len(intended_assets)}] Registered: {a_id}", flush=True)
            except Exception as ex:
                print(f"FAILED {a_id}: {ex}")
        
        if (idx + 1) % 20 == 0:
            print(f"Progress: {idx+1}/{len(intended_assets)} complete...")
            time.sleep(1)

def main():
    cw_path = '03_data_topography/cog_pipeline/metadata_crosswalk.csv'
    df = pd.read_csv(cw_path)
    
    with open('03_data_topography/cog_pipeline/scaling_config.json', 'r') as f:
        config = json.load(f)
    
    raw_root = 'gs://akveg-data/aksdb_dem_covars_v20250422/'
    scaled_root = 'gs://akveg-data/aksdb_dem_covars_v20250422_scaled_i32/cogs/'
    
    raw_coll = f"projects/{PROJECT_ID}/assets/covariates/aksdb/aksdb_topo_v20250422_raw"
    scaled_coll = f"projects/{PROJECT_ID}/assets/covariates/aksdb/aksdb_topo_v20250422_scaled_i32"

    sync_collection(raw_coll, 'raw_id', raw_root, df, "Raw Collection")
    sync_collection(scaled_coll, 'scaled_id', scaled_root, df, "Scaled Collection", config=config)

if __name__ == "__main__":
    main()
