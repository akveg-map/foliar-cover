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
    import rasterio
    import numpy as np
    input_path, window, scale, min_val, max_val, nodata_out, target_dtype = args
    try:
        with rasterio.open(input_path) as src:
            arr = src.read(1, window=window).astype(np.float32)
            
            # Create mask: True for VALID data, False for NoData
            # We catch: 
            # 1. The explicit metadata NoData value
            # 2. Hardcoded -99999 (commonly used as background in this dataset)
            # 3. NaNs and very large negative numbers
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
                    # For categorical/Byte, just clamp to be safe and cast
                    clamped = np.clip(arr[mask], min_val, max_val)
                    out_arr[mask] = clamped.astype(target_dtype)
            return window, out_arr
    except Exception as e:
        return window, str(e)

def main():
    # 1. Environment and Config
    input_file_uri = os.environ.get("INPUT_FILE") # /vsigs/...
    basename = os.environ.get("BASENAME")         # e.g. relelev_32
    config_uri = os.environ.get("CONFIG_URI")     # gs://.../scaling_config.json
    output_bucket = os.environ.get("OUTPUT_BUCKET")
    output_root = os.environ.get("OUTPUT_ROOT")   # e.g. aksdb_dem_covars_v20250422_scaled_cog
    
    log(f"Starting Production Job for: {basename}")
    
    # 2. Parse Scaling Config
    try:
        # Download config locally to read
        client = storage.Client()
        config_bucket_name = config_uri.replace("gs://", "").split("/")[0]
        config_blob_name = "/".join(config_uri.replace("gs://", "").split("/")[1:])
        config_data = client.bucket(config_bucket_name).blob(config_blob_name).download_as_string()
        full_config = json.loads(config_data)
        
        # Match basename to group (e.g. relelev_32 -> relelev)
        group = None
        # Sort keys by length descending to match longest prefix first
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
        
        # Map config types to numpy/rasterio valid types
        if config_type == "Byte":
            target_dtype = "uint8"
        elif config_type == "Float32":
            target_dtype = "float32"
        else:
            target_dtype = "int16"
            
        resampling = "MODE" if config_type == "Byte" else "AVERAGE"
        
        log(f"Config Matched: Group={group}, Scale={scale}, DType={target_dtype}, Resampling={resampling}")
    except Exception as e:
        log(f"CRITICAL ERROR loading config: {e}")
        sys.exit(1)

    # 3. Setup Paths
    output_filename = f"{basename}{suffix}.tif"
    temp_scaled = f"/tmp/scaled_{basename}.tif"
    temp_cog = f"/tmp/final_{basename}.tif"
    
    # Range limits
    if target_dtype == "uint8":
        nodata_out = 0
        clamp_min = 0
        clamp_max = 255
    elif target_dtype == "float32":
        nodata_out = -99999.0
        clamp_min = -1e30 # Basically no clamping for floats
        clamp_max = 1e30
    else: # int16
        nodata_out = -32768
        clamp_min = -32000
        clamp_max = 32000
    
    num_workers = 8

    try:
        # TODO (Optimization): If scale == 1.0 and source_dtype matches target_dtype,
        # we can skip the block-by-block Python processing (STEP 1). 
        # Instead, we should download the source file locally using the GCS client,
        # and pass that local file directly into gdal_translate (STEP 2).
        # This avoids multi-pass /vsigs/ network overhead and saves massive amounts 
        # of RAM and processing time for scale-1 bands.
        
        # STEP 1: Scaling (Parallel)
        log(f"Step 1: Scaling/Clamping with {num_workers} workers...")
        with rasterio.open(input_file_uri) as src:
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
            args = [(input_file_uri, w, scale, clamp_min, clamp_max, nodata_out, target_dtype) for w in windows]
            
            with rasterio.open(temp_scaled, 'w', **profile) as dst:
                with ProcessPoolExecutor(max_workers=num_workers) as executor:
                    for i, (window, result) in enumerate(executor.map(process_window, args)):
                        if isinstance(result, str):
                            log(f"Error in block: {result}")
                            continue
                        dst.write(result, 1, window=window)
                        if (i+1) % 2000 == 0 or (i+1) == len(windows):
                            log(f"  Progress: {i+1}/{len(windows)} blocks...")

        # STEP 2: COG Conversion (Local)
        log("Step 2: Local COG conversion...")
        translate_cmd = [
            "gdal_translate", temp_scaled, temp_cog,
            "-of", "COG", "-co", "COMPRESS=DEFLATE", "-co", "PREDICTOR=2",
            "-co", "BIGTIFF=YES", "-co", "NUM_THREADS=ALL_CPUS",
            "-co", f"RESAMPLING={resampling}", "-co", "OVERVIEWS=IGNORE_EXISTING", "-co", "LEVELS=9",
            "--config", "GDAL_CACHEMAX", "32768"
        ]
        subprocess.run(translate_cmd, check=True)
        
        # STEP 3: Cleanup Intermediate
        if os.path.exists(temp_scaled):
            os.remove(temp_scaled)

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
        # Final log upload
        try:
            log_blob_path = f"{output_root}/logs/{output_filename}.log"
            client.bucket(output_bucket).blob(log_blob_path).upload_from_filename("process.log")
        except:
            pass

if __name__ == "__main__":
    main()
