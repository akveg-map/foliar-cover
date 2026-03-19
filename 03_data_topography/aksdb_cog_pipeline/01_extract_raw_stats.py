import os
import json
import datetime
import subprocess

# PROJECT CONFIG
PROJECT_ID = "akveg-map"
REGION = "us-central1"
BASE_IMAGE = "python:3.10-slim"

# FULL LIST OF 111 FILES
FILES_TO_SCAN = [
  'aspct_16', 'aspct_32', 'aspct_4', 'ca_10', 'ca_10000', 'ci_16', 'ci_32', 'ci_4',
  'crosc_16', 'crosc_32', 'crosc_4', 'dah', 'devmeanelev_16', 'devmeanelev_32',
  'devmeanelev_4', 'dfa', 'diffmeanelev_16', 'diffmeanelev_32', 'diffmeanelev_4',
  'diffopen_2', 'diffopen_256', 'diffopen_32', 'dis', 'fel', 'gmrph_ms_30',
  'gmrph_ms_300', 'gmrph_r_30', 'gmrph_r_300', 'gmrph_r_3000', 'hs_st', 'longc_16',
  'longc_32', 'longc_4', 'maxc_16', 'maxc_32', 'maxc_4', 'mbi_0.001', 'mbi_0.01',
  'mbi_0.1', 'mca_10', 'mca_10000', 'minc_16', 'minc_32', 'minc_4', 'minelev_16',
  'minelev_32', 'minelev_4', 'morpfeat_16', 'morpfeat_32', 'morpfeat_4', 'msp',
  'nh', 'no_2', 'no_256', 'no_32', 'perctelev_16', 'perctelev_32', 'perctelev_4',
  'pisrdif_2023-01-22', 'pisrdif_2023-02-22', 'pisrdif_2023-03-22',
  'pisrdif_2023-04-22', 'pisrdif_2023-05-22', 'pisrdif_2023-06-22',
  'pisrdif_2023-12-22', 'pisrdir_2023-01-22', 'pisrdir_2023-02-22',
  'pisrdir_2023-03-22', 'pisrdir_2023-04-22', 'pisrdir_2023-05-22',
  'pisrdir_2023-06-22', 'pisrdir_2023-12-22', 'planc_16', 'planc_32', 'planc_4',
  'po_2', 'po_256', 'po_32', 'profc_16', 'profc_32', 'profc_4', 'relelev_16',
  'relelev_32', 'relelev_4', 'relmeanelev_16', 'relmeanelev_32', 'relmeanelev_4',
  'sl_16', 'sl_32', 'sl_4', 'slh', 'spi', 'stddevelev_16', 'stddevelev_32',
  'stddevelev_4', 'stdh', 'swi_10', 'swi_10000', 'tpi_32', 'tpi_4', 'tri_16',
  'tri_32', 'tri_4', 'tsc_16', 'tsc_32', 'tsc_4', 'twi', 'vlyd', 'vrm_16',
  'vrm_32', 'vrm_4'
]

OUTPUT_BUCKET = "akveg-data"
OUTPUT_BLOB = "aksdb_dem_covars_v20250422/cog_pipeline/cog_stats_summary_full.csv"

def create_batch_job_config(job_id):
    container_python_script = f"""
import rasterio
import numpy as np
import os
import pandas as pd
from google.cloud import storage

FILES = {json.dumps(FILES_TO_SCAN)}
GCS_ROOT = "/vsigs/akveg-data/aksdb_dem_covars_v20250422/"
PERCENTILES = [0.1, 0.5, 1, 5, 10, 25, 50, 75, 90, 95, 99, 99.5, 99.9]

results = []

print(f"Starting extraction for {{len(FILES)}} files...")
for name in FILES:
    uri = GCS_ROOT + name + ".tif"
    print(f"  Processing {{name}}...")
    try:
        with rasterio.open(uri) as src:
            ovs = src.overviews(1)
            row = {{
                "Filename": name,
                "Type": str(src.dtypes[0]),
                "NoData": float(src.nodata) if src.nodata is not None else "N/A",
                "Width": int(src.width),
                "Height": int(src.height),
                "EPSG": src.crs.to_epsg() if src.crs else "N/A",
                "Overviews": len(ovs)
            }}
            
            if ovs:
                # Read deepest overview
                decimation = ovs[-1]
                data = src.read(1, out_shape=(src.height // decimation, src.width // decimation)).astype(np.float32)
                mask = (data != src.nodata) if src.nodata is not None else (~np.isnan(data) & (data > -1e30))
                valid = data[mask]
                
                if valid.size > 0:
                    row["Min"] = float(np.min(valid))
                    p_vals = np.percentile(valid, PERCENTILES)
                    for p, val in zip(PERCENTILES, p_vals):
                        row[f"p_{{str(p).replace('.', '_')}}"] = float(val)
                    row["Max"] = float(np.max(valid))
            results.append(row)
    except Exception as e:
        print(f"    Error on {{name}}: {{e}}")

df = pd.DataFrame(results)
df.to_csv("stats_full.csv", index=False)

print("Uploading to GCS...")
try:
    client = storage.Client()
    bucket = client.bucket("{OUTPUT_BUCKET}")
    blob = bucket.blob("{OUTPUT_BLOB}")
    blob.upload_from_filename("stats_full.csv")
    print("Upload complete.")
except Exception as e:
    print(f"Upload failed: {{e}}")
"""

    escaped_script = container_python_script.replace('"', '\\"').replace('$', '\\$')
    
    container_command = (
        "apt-get update && apt-get install -y libgdal-dev g++ && "
        "pip3 install rasterio pandas google-cloud-storage --break-system-packages && "
        f"export GS_PROJECT_ID={PROJECT_ID} && "
        f"python3 -c \"{escaped_script}\""
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
                "computeResource": {
                    "cpuMilli": "4000",
                    "memoryMib": "16384"
                }
            }
        }],
        "allocationPolicy": {
            "instances": [{
                "policy": {
                    "machineType": "n2-standard-4",
                    "provisioningModel": "SPOT"
                }
            }]
        },
        "logsPolicy": {
            "destination": "CLOUD_LOGGING"
        }
    }
    return job_config

def main():
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    job_id = f"stats-full-111-{timestamp}"
    
    config = create_batch_job_config(job_id)
    with open("batch_config_full.json", "w") as f:
        json.dump(config, f, indent=2)
        
    submit_cmd = (
        f"gcloud batch jobs submit {job_id} "
        f"--location {REGION} "
        f"--config batch_config_full.json "
        f"--project {PROJECT_ID}"
    )
    
    print(f"Submitting full 111-file stats extraction job: {job_id}...")
    subprocess.run(submit_cmd, shell=True, check=True)

if __name__ == "__main__":
    main()
