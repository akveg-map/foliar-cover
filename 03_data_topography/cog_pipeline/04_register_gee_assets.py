import ee
import pandas as pd
import sys
import time

PROJECT_ID = "akveg-map"
ee.Initialize(project=PROJECT_ID)

def sync_collection(collection_id, filename_col, gcs_root, crosswalk_df, description):
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
    # Asset IDs in GEE replace dots with 'p'
    intended_assets = {}
    for _, row in crosswalk_df.iterrows():
        img_id = row[filename_col]
        asset_id = f"{collection_id}/{img_id.replace('.', 'p')}"
        intended_assets[asset_id] = {
            'gcs_path': f"{gcs_root}{img_id}.tif",
            'properties': {
                'title': row['title'],
                'category': row['category'],
                'variable_prefix': row['prefix'],
                'neighborhood': str(row['neighborhood']),
                'scale_factor': float(row['scale']),
                'data_type': row['data_type'],
                'match_verification': row['match_type'],
                'project': 'AKVEG',
                'source_version': 'v20250422'
            }
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
            # print(f"[{idx+1}/111] Updated properties: {a_id}")
        except ee.EEException:
            # Create new
            try:
                request = {
                    'type': 'IMAGE',
                    'gcs_location': {'uris': [info['gcs_path']]},
                    'properties': info['properties']
                }
                ee.data.createAsset(request, a_id)
                print(f"[{idx+1}/111] Registered: {a_id}", flush=True)
            except Exception as ex:
                print(f"FAILED {a_id}: {ex}")
        
        if (idx + 1) % 20 == 0:
            print(f"Progress: {idx+1}/111 complete...")
            time.sleep(1)

def main():
    cw_path = '03_data_topography/cog_pipeline/metadata_crosswalk.csv'
    df = pd.read_csv(cw_path)
    
    raw_root = 'gs://akveg-data/aksdb_dem_covars_v20250422/'
    scaled_root = 'gs://akveg-data/aksdb_dem_covars_v20250422_scaled_cog/cogs/'
    
    raw_coll = f"projects/{PROJECT_ID}/assets/covariates/aksdb/aksdb_topo_v20250422_raw"
    scaled_coll = f"projects/{PROJECT_ID}/assets/covariates/aksdb/aksdb_topo_v20250422_scaled"

    # Raw collection doesn't change often, but scaled does
    sync_collection(raw_coll, 'raw_id', raw_root, df, "Raw Collection")
    sync_collection(scaled_coll, 'scaled_id', scaled_root, df, "Scaled Collection")

if __name__ == "__main__":
    main()
