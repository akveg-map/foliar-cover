import rasterio
from rasterio.windows import Window
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
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
    input_file_uri = os.environ.get("INPUT_FILE")
    basename = os.environ.get("BASENAME")
    config_uri = os.environ.get("CONFIG_URI")
    output_bucket = os.environ.get("OUTPUT_BUCKET")
    output_root = os.environ.get("OUTPUT_ROOT")
    
    gcs_input_path = input_file_uri.replace("/vsigs/", "gs://")
    log(f"Starting Production Job for: {basename}")
    
    # 2. Parse Scaling Config
    try:
        client = storage.Client()
        config_bucket_name = config_uri.replace("gs://", "").split("/")[0]
        config_blob_name = "/".join(config_uri.replace("gs://", "").split("/")[1:])
        config_data = client.bucket(config_bucket_name).blob(config_blob_name).download_as_string()
        full_config = json.loads(config_data)
        
        group = next((k for k in sorted(full_config.keys(), key=len, reverse=True) if basename.startswith(k)), None)
        if not group: sys.exit(1)
            
        cfg = full_config[group]
        scale, suffix, config_type = cfg["scale"], cfg["suffix"], cfg["type"]
        
        if config_type == "Byte":
            target_dtype, nodata_out, clamp_min, clamp_max = "uint8", 0, 0, 255
        elif config_type == "Float32":
            target_dtype, nodata_out, clamp_min, clamp_max = "float32", -99999.0, -1e30, 1e30
        elif config_type == "Int32":
            target_dtype, nodata_out, clamp_min, clamp_max = "int32", -2147483648, -2147483647, 2147483647
        else: # Int16
            target_dtype, nodata_out, clamp_min, clamp_max = "int16", -32768, -32000, 32000
            
        resampling = "MODE" if config_type == "Byte" else "AVERAGE"
        log(f"Config Matched: Group={group}, Scale={scale}, DType={target_dtype}")
    except Exception as e:
        log(f"CRITICAL ERROR loading config: {e}"); sys.exit(1)

    # 3. Setup Paths
    output_filename = f"{basename}{suffix}.tif"
    local_raw = f"/tmp/raw_{basename}.tif"
    temp_scaled = f"/tmp/scaled_{basename}.tif"
    temp_cog = f"/tmp/final_{basename}.tif"
    
    try:
        # STEP 0: Local Download
        log(f"Step 0: Downloading raw source via gsutil to {local_raw}...")
        subprocess.run(["gsutil", "-m", "cp", gcs_input_path, local_raw], check=True)

        # STEP 1: Scaling (Parallel with Throttled Write)
        num_workers = 12 # Increase workers since we removed compression bottleneck
        log(f"Step 1: Scaling/Clamping with {num_workers} workers (Throttled)...")
        with rasterio.open(local_raw) as src:
            profile = src.profile.copy()
            # Remove compression from intermediate file to avoid double-compression and I/O bottlenecks
            profile.update(dtype=target_dtype, nodata=nodata_out, count=1, tiled=True, blockxsize=512, blockysize=512, bigtiff='YES')
            if 'compress' in profile: del profile['compress']
            
            windows = [window for ij, window in src.block_windows()]
            
            with rasterio.open(temp_scaled, 'w', **profile) as dst:
                with ProcessPoolExecutor(max_workers=num_workers) as executor:
                    # Submit only first batch of windows
                    future_to_window = {}
                    batch_size = num_workers * 4 
                    
                    window_iter = iter(windows)
                    for _ in range(batch_size):
                        try:
                            w = next(window_iter)
                            args = (local_raw, w, scale, clamp_min, clamp_max, nodata_out, target_dtype)
                            future_to_window[executor.submit(process_window, args)] = w
                        except StopIteration:
                            break
                    
                    count = 0
                    while future_to_window:
                        future = next(as_completed(future_to_window))
                        window = future_to_window.pop(future)
                        _, result = future.result()
                        
                        if isinstance(result, str):
                            log(f"Error in block: {result}")
                        else:
                            dst.write(result, 1, window=window)
                        
                        count += 1
                        if count % 2000 == 0:
                            log(f"  Progress: {count}/{len(windows)} blocks...")
                        
                        # Submit next window to keep the pipeline full but throttled
                        try:
                            w_next = next(window_iter)
                            args_next = (local_raw, w_next, scale, clamp_min, clamp_max, nodata_out, target_dtype)
                            future_to_window[executor.submit(process_window, args_next)] = w_next
                        except StopIteration:
                            continue

        # STEP 1.5: Free space
        if os.path.exists(local_raw): os.remove(local_raw)

        # STEP 2: COG Conversion
        log("Step 2: Local COG conversion...")
        translate_cmd = [
            "gdal_translate", temp_scaled, temp_cog,
            "-of", "COG", "-co", "COMPRESS=DEFLATE",
            "-co", "BIGTIFF=YES", "-co", "NUM_THREADS=ALL_CPUS",
            "-co", f"RESAMPLING={resampling}", "-co", "OVERVIEWS=IGNORE_EXISTING",
            "--config", "GDAL_CACHEMAX", "16384" # Conservative cache
        ]
        if target_dtype in ["int16", "int32", "uint8"]:
            translate_cmd.insert(5, "-co"); translate_cmd.insert(6, "PREDICTOR=2")
        subprocess.run(translate_cmd, check=True)

        # STEP 2.5: Free space
        if os.path.exists(temp_scaled): os.remove(temp_scaled)
        
        # STEP 4: GCS Upload
        log("Step 4: Uploading COG to GCS...")
        client.bucket(output_bucket).blob(f"{output_root}/cogs/{output_filename}").upload_from_filename(temp_cog)
        log(f"SUCCESS: {output_filename} uploaded.")

    except Exception as e:
        log(f"CRITICAL ERROR: {e}"); sys.exit(1)
    finally:
        for p in [local_raw, temp_scaled, temp_cog]:
            if os.path.exists(p): os.remove(p)
        try:
            client.bucket(output_bucket).blob(f"{output_root}/logs/{output_filename}.log").upload_from_filename("process.log")
        except: pass

if __name__ == "__main__":
    main()
