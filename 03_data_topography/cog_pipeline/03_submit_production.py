import os
import json
import datetime
import subprocess

import pandas as pd

PROJECT_ID = "akveg-map"
REGION = "us-central1"
BASE_IMAGE = "gcr.io/akveg-map/vhr-cpu:latest"

# New output path for Unified Int32 high-integrity run
OUTPUT_ROOT = "aksdb_dem_covars_v20250422_scaled_i32"
OUTPUT_BUCKET = "akveg-data"

WORKER_SCRIPT_LOCAL = "03_data_topography/cog_pipeline/02_production_worker.py"
WORKER_SCRIPT_GCS = f"gs://{OUTPUT_BUCKET}/{OUTPUT_ROOT}/config/production_worker.py"
CONFIG_LOCAL = "03_data_topography/cog_pipeline/scaling_config.json"
CONFIG_GCS = f"gs://{OUTPUT_BUCKET}/{OUTPUT_ROOT}/config/scaling_config.json"

# FETCH FULL FILE LIST (111 files) from crosswalk
cw = pd.read_csv("03_data_topography/cog_pipeline/metadata_crosswalk.csv")
FILES_TO_PROCESS = cw["raw_id"].tolist()

def submit_batch_job(basename):
    safe_name = basename.replace('_', '-').replace('.', '-')
    job_id = f"cog-prod-{safe_name}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Each task downloads the worker script and runs it with its specific env vars
    container_command = (
        f"gsutil cp {WORKER_SCRIPT_GCS} /tmp/worker.py && "
        f"export BASENAME={basename} && "
        f"export INPUT_FILE=/vsigs/akveg-data/aksdb_dem_covars_v20250422/{basename}.tif && "
        f"export CONFIG_URI={CONFIG_GCS} && "
        f"export OUTPUT_BUCKET={OUTPUT_BUCKET} && "
        f"export OUTPUT_ROOT={OUTPUT_ROOT} && "
        f"export GS_PROJECT_ID={PROJECT_ID} && "
        "python3 /tmp/worker.py"
    )

    job_config = {
        "taskGroups": [{
            "taskSpec": {
                "runnables": [{
                    "container": {
                        "imageUri": BASE_IMAGE,
                        "commands": ["/bin/sh", "-c", container_command],
                        "options": "--privileged"
                    }
                }],
                "computeResource": { "cpuMilli": "16000", "memoryMib": "65536" },
                "maxRunDuration": "14400s",
                "maxRetryCount": 3,
                "lifecyclePolicies": [
                    {
                        "action": "RETRY_TASK",
                        "actionCondition": {
                            "exitCodes": [50001]
                        }
                    }
                ]
            }
        }],
        "allocationPolicy": {
            "instances": [{
                "policy": {
                    "machineType": "n2-standard-16",
                    "provisioningModel": "SPOT",
                    "bootDisk": { "sizeGb": "500" }
                }
            }]
        },
        "logsPolicy": { "destination": "CLOUD_LOGGING" }
    }
    
    config_filename = f"config_{basename}.json"
    with open(config_filename, "w") as f:
        json.dump(job_config, f)
        
    cmd = [
        "gcloud", "batch", "jobs", "submit", job_id,
        "--location", REGION,
        "--config", config_filename,
        "--project", PROJECT_ID
    ]
    subprocess.run(cmd, check=True)
    os.remove(config_filename)

def main():
    # TEST MODE: Set to False for full production run
    # Now launching remaining 94 variables
    TEST_MODE = False
    
    # 1. Upload worker script and config
    print(f"Uploading production worker to {WORKER_SCRIPT_GCS}...")
    subprocess.run(["gsutil", "cp", WORKER_SCRIPT_LOCAL, WORKER_SCRIPT_GCS], check=True)
    print(f"Uploading scaling config to {CONFIG_GCS}...")
    subprocess.run(["gsutil", "cp", CONFIG_LOCAL, CONFIG_GCS], check=True)

    # 2. Filter list to run only remaining files (already identified 94)
    # Get files in GCS to skip already successful ones
    gcs_raw = subprocess.check_output(["gsutil", "ls", f"gs://{OUTPUT_BUCKET}/{OUTPUT_ROOT}/cogs/"]).decode().splitlines()
    gcs_basenames = [os.path.basename(f) for f in gcs_raw]
    
    vars_to_run = [r for r in FILES_TO_PROCESS if not any(f.startswith(r + "_") for f in gcs_basenames)]
    print(f"IDENTIFIED: {len(vars_to_run)} variables remaining to process.")

    # 3. Iterate and submit
    print(f"Launching final production batch for {len(vars_to_run)} files...")
    for i, name in enumerate(vars_to_run):
        print(f"[{i+1}/{len(vars_to_run)}] Submitting {name}...")
        try:
            submit_batch_job(name)
        except Exception as e:
            print(f"Failed to submit {name}: {e}")

if __name__ == "__main__":
    main()
