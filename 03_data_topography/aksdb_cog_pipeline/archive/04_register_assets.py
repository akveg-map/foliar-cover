import ee
import os
import pandas as pd
import subprocess

PROJECT_ID = "akveg-map"
OUTPUT_BUCKET = "akveg-data"
OUTPUT_ROOT = "aksdb_dem_covars_v20250422_scaled_i32"
COLLECTION_ID = f"projects/{PROJECT_ID}/assets/topography/aksdb_dem_covars_v20250422_scaled_i32"

def register_cogs():
    ee.Initialize(project=PROJECT_ID)
    
    # Ensure collection exists
    try:
        ee.data.createAsset({'type': 'IMAGE_COLLECTION'}, COLLECTION_ID)
        print(f"Created collection: {COLLECTION_ID}")
    except ee.ee_exception.EEException as e:
        if "already exists" in str(e) or "Cannot overwrite asset" in str(e):
            print(f"Collection already exists: {COLLECTION_ID}")
        else:
            raise e

    # List COGs in bucket
    gcs_path = f"gs://{OUTPUT_BUCKET}/{OUTPUT_ROOT}/cogs/"
    objs = subprocess.check_output(["gsutil", "ls", gcs_path]).decode().splitlines()
    cogs = [obj for obj in objs if obj.endswith(".tif")]
    
    # List existing assets in collection
    existing_assets = [asset['id'] for asset in ee.data.listAssets({'parent': COLLECTION_ID})['assets']]
    
    for cog_url in cogs:
        basename = os.path.basename(cog_url).replace(".tif", "")
        asset_id = f"{COLLECTION_ID}/{basename}"
        
        if asset_id in existing_assets:
            print(f"Asset already exists: {basename}")
            continue
            
        print(f"Registering: {basename}...")
        try:
            # Register as COG-backed asset
            ee.data.createAsset({
                'type': 'IMAGE',
                'gcs_location': {'uris': [cog_url]}
            }, asset_id)
        except Exception as e:
            print(f"Failed to register {basename}: {e}")

if __name__ == "__main__":
    register_cogs()
