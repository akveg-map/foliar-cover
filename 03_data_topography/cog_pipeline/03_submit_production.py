import os
import json
import datetime
import subprocess

PROJECT_ID = "akveg-map"
REGION = "us-central1"
BASE_IMAGE = "gcr.io/akveg-map/vhr-cpu:latest"

WORKER_SCRIPT_LOCAL = "03_data_topography/cog_pipeline/02_production_worker.py"
WORKER_SCRIPT_GCS = "gs://akveg-data/aksdb_dem_covars_v20250422_scaled_cog/config/15_production_worker.py"
CONFIG_GCS = "gs://akveg-data/aksdb_dem_covars_v20250422_scaled_cog/config/scaling_config.json"

OUTPUT_BUCKET = "akveg-data"
OUTPUT_ROOT = "aksdb_dem_covars_v20250422_scaled_cog"

# FETCH FULL FILE LIST (111 files)
FILES_TO_PROCESS = [
  'dfa', 'spi',
  'diffopen_2', 'diffopen_32', 'diffopen_256',
  'planc_4', 'planc_16', 'planc_32',
  'devmeanelev_4', 'devmeanelev_16', 'devmeanelev_32'
]

def submit_batch_job(basename):
    safe_name = basename.replace('_', '-').replace('.', '-')
    job_id = f"cog-prod-{safe_name}-{datetime.datetime.now().strftime('%m%d-%H%M')}"
    
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
                "maxRetryCount": 3
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
    # 1. Upload worker script
    print(f"Uploading production worker to {WORKER_SCRIPT_GCS}...")
    subprocess.run(["gsutil", "cp", WORKER_SCRIPT_LOCAL, WORKER_SCRIPT_GCS], check=True)

    # 2. Iterate and submit
    print(f"Launching production batch for {len(FILES_TO_PROCESS)} files...")
    for i, name in enumerate(FILES_TO_PROCESS):
        print(f"[{i+1}/{len(FILES_TO_PROCESS)}] Submitting {name}...")
        try:
            submit_batch_job(name)
        except Exception as e:
            print(f"Failed to submit {name}: {e}")

if __name__ == "__main__":
    main()
