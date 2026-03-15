import rasterio
from rasterio.windows import Window
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import os
import sys
import json
import time
import subprocess
from google.cloud import storage

def log(msg):
    print(msg)
    with open("process.log", "a") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

def process_window(args):
    """Worker function for parallel block processing."""
    # input_path is a local path for efficiency
    input_path, window, scale, min_val, max_val, nodata_out, target_dtype = args
    try:
        with rasterio.open(input_path) as src:
            arr = src.read(1, window=window).astype(np.float32)
            
            # Create mask: True for VALID data, False for NoData
            mask = (arr > -99990) & (~np.isnan(arr))
            if src.nodata is not None:
                mask = mask & (arr != src.nodata)
            
            # Initialize with target NoData value
            out_arr = np.full(arr.shape, nodata_out, dtype=target_dtype)
            
            if np.any(mask):
                if scale != 1.0:
                    valid_scaled = arr[mask] * scale
                    clamped = np.clip(valid_scaled, min_val, max_val)
                    out_arr[mask] = clamped.astype(target_dtype)
                else:
                    clamped = np.clip(arr[mask], min_val, max_val)
                    out_arr[mask] = clamped.astype(target_dtype)
            return window, out_arr
    except Exception as e:
        return window, str(e)

def main():
    # 1. Environment and Config
    input_file_uri = os.environ.get("INPUT_FILE") # gs://... or /vsigs/...
    basename = os.environ.get("BASENAME")
    config_uri = os.environ.get("CONFIG_URI")
    output_bucket = os.environ.get("OUTPUT_BUCKET")
    output_root = os.environ.get("OUTPUT_ROOT")
    
    # Ensure input_file_uri is a standard gs:// path for the storage client
    gcs_input_path = input_file_uri.replace("/vsigs/", "gs://")
    
    log(f"Starting Production Job for: {basename}")
    
    # 2. Parse Scaling Config
    try:
        client = storage.Client()
        config_bucket_name = config_uri.replace("gs://", "").split("/")[0]
        config_blob_name = "/".join(config_uri.replace("gs://", "").split("/")[1:])
        config_data = client.bucket(config_bucket_name).blob(config_blob_name).download_as_string()
        full_config = json.loads(config_data)
        
        group = None
        sorted_keys = sorted(full_config.keys(), key=len, reverse=True)
        for key in sorted_keys:
            if basename.startswith(key):
                group = key
                break
        
        if not group:
            log(f"CRITICAL: Could not find scaling group for {basename}")
            sys.exit(1)
            
        cfg = full_config[group]
        scale = cfg["scale"]
        suffix = cfg["suffix"]
        config_type = cfg["type"]
        
        # Comprehensive DType Mapping
        if config_type == "Byte":
            target_dtype = "uint8"
            nodata_out = 0
            clamp_min, clamp_max = 0, 255
        elif config_type == "Float32":
            target_dtype = "float32"
            nodata_out = -99999.0
            clamp_min, clamp_max = -1e30, 1e30
        elif config_type == "Int32":
            target_dtype = "int32"
            nodata_out = -2147483648
            clamp_min, clamp_max = -2147483647, 2147483647
        else: # Int16
            target_dtype = "int16"
            nodata_out = -32768
            clamp_min, clamp_max = -32000, 32000
            
        resampling = "MODE" if config_type == "Byte" else "AVERAGE"
        log(f"Config Matched: Group={group}, Scale={scale}, DType={target_dtype}, Resampling={resampling}")
    except Exception as e:
        log(f"CRITICAL ERROR loading config: {e}")
        sys.exit(1)

    # 3. Setup Paths
    output_filename = f"{basename}{suffix}.tif"
    local_raw = f"/tmp/raw_{basename}.tif"
    temp_scaled = f"/tmp/scaled_{basename}.tif"
    temp_cog = f"/tmp/final_{basename}.tif"
    
    try:
        # STEP 0: Local Download (Crucial for performance)
        log(f"Step 0: Downloading raw source to {local_raw}...")
        input_bucket_name = gcs_input_path.replace("gs://", "").split("/")[0]
        input_blob_name = "/".join(gcs_input_path.replace("gs://", "").split("/")[1:])
        client.bucket(input_bucket_name).blob(input_blob_name).download_to_filename(local_raw)

        # STEP 1: Scaling (Parallel)
        num_workers = 12 # Optimized for n2-standard-16
        log(f"Step 1: Scaling/Clamping with {num_workers} workers...")
        with rasterio.open(local_raw) as src:
            profile = src.profile.copy()
            profile.update(
                dtype=target_dtype, 
                nodata=nodata_out, 
                count=1, 
                compress='DEFLATE', 
                tiled=True, 
                blockxsize=512, 
                blockysize=512, 
                bigtiff='YES'
            )
            windows = [window for ij, window in src.block_windows()]
            args = [(local_raw, w, scale, clamp_min, clamp_max, nodata_out, target_dtype) for w in windows]
            
            with rasterio.open(temp_scaled, 'w', **profile) as dst:
                with ProcessPoolExecutor(max_workers=num_workers) as executor:
                    for i, (window, result) in enumerate(executor.map(process_window, args)):
                        if isinstance(result, str):
                            log(f"Error in block: {result}")
                            continue
                        dst.write(result, 1, window=window)
                        if (i+1) % 2000 == 0 or (i+1) == len(windows):
                            log(f"  Progress: {i+1}/{len(windows)} blocks...")

        # STEP 2: COG Conversion
        log("Step 2: Local COG conversion...")
        translate_cmd = [
            "gdal_translate", temp_scaled, temp_cog,
            "-of", "COG", "-co", "COMPRESS=DEFLATE",
            "-co", "BIGTIFF=YES", "-co", "NUM_THREADS=ALL_CPUS",
            "-co", f"RESAMPLING={resampling}", "-co", "OVERVIEWS=IGNORE_EXISTING", "-co", "LEVELS=9",
            "--config", "GDAL_CACHEMAX", "32768"
        ]
        # Only add Predictor 2 for Integer types
        if target_dtype in ["int16", "int32", "uint8"]:
            translate_cmd.insert(5, "-co")
            translate_cmd.insert(6, "PREDICTOR=2")
            
        subprocess.run(translate_cmd, check=True)
        
        # STEP 3: Cleanup Intermediate
        for p in [local_raw, temp_scaled]:
            if os.path.exists(p): os.remove(p)

        # STEP 4: GCS Upload
        log("Step 4: Uploading COG to GCS...")
        final_blob_path = f"{output_root}/cogs/{output_filename}"
        blob = client.bucket(output_bucket).blob(final_blob_path)
        blob.chunk_size = 128 * 1024 * 1024
        blob.upload_from_filename(temp_cog)
        
        log(f"SUCCESS: {output_filename} uploaded to {output_bucket}/{output_root}/cogs/")

    except Exception as e:
        log(f"CRITICAL ERROR: {e}")
        sys.exit(1)
    finally:
        # Final log upload and cleanup
        try:
            log_blob_path = f"{output_root}/logs/{output_filename}.log"
            client.bucket(output_bucket).blob(log_blob_path).upload_from_filename("process.log")
            for p in [local_raw, temp_scaled, temp_cog]:
                if os.path.exists(p): os.remove(p)
        except:
            pass

if __name__ == "__main__":
    main()
