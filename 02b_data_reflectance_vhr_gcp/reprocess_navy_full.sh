#!/bin/bash
# Description: Methodical master script for Navy North Slope harmonization and CHM testing.
# Reverted to IFSAR DSM standard path.

PROJECT_ID="akveg-map"
BASE_GCS_SCRIPTS="gs://akveg-data/scripts/vhr_pipeline"
NAVY_ORDERS=(
    "gs://akveg-data/vhr/navy_north_slope/orders/050300601010_01"
    "gs://akveg-data/vhr/navy_north_slope/orders/050300602010_01"
    "gs://akveg-data/vhr/navy_north_slope/orders/050300603010_01"
)
TEST_IMAGE="gs://akveg-data/vhr/vhr_cogs_snap/PS_SRLite_00p50m_20240710_222652_WV03_10400100996FB100_cog.tif"
# Standard IFSAR DSM Path
DEM_PATH="gs://akveg-data/dem/alaska_ifsar_dsm_20200925_plus_us_noaa_g2009_cog1024_noLerc_deflate3.tif"

echo "[$(date)] --- STEP 1: Stabilize GCS Scripts ---"
gcloud storage cp run_job_all.sh "${BASE_GCS_SCRIPTS}/run_job_all.sh"
gcloud storage cp run_chm_job.sh "${BASE_GCS_SCRIPTS}/run_chm_job.sh"
gcloud storage cp 230_predict_chm_dinov3.py "${BASE_GCS_SCRIPTS}/230_predict_chm_dinov3.py"

echo "[$(date)] --- STEP 2: Deploy Workflows ---"
gcloud workflows deploy vhr-pipeline-orchestrator --source=vhr_orchestrator.yaml --location=us-central1
gcloud workflows deploy chm-pipeline-orchestrator --source=chm_orchestrator.yaml --location=us-central1

echo "[$(date)] --- STEP 3: Trigger Navy CPU Reprocessing (Standard Instances) ---"
for ORDER in "${NAVY_ORDERS[@]}"; do
    STRIP_ID=$(basename $ORDER)
    echo "Triggering CPU for $STRIP_ID..."
    gcloud workflows execute vhr-pipeline-orchestrator --location=us-central1 --data="{
        \"input_dir\": \"$ORDER\",
        \"output_base\": \"gs://akveg-data/vhr/navy_north_slope/processed\",
        \"dem_path\": \"$DEM_PATH\",
        \"ccdc_ee_project\": \"abr-gee-teck\",
        \"use_spot\": false
    }"
done

echo "[$(date)] --- STEP 4: Trigger Single GPU CHM Test (Standard Instance) ---"
gcloud workflows execute chm-pipeline-orchestrator --location=us-central1 --data="{
    \"input_image\": \"$TEST_IMAGE\",
    \"disk_size_gb\": 100,
    \"hf_token\": \"${HF_TOKEN:-NOT_REQUIRED}\",
    \"use_spot\": false
}"
echo "[$(date)] All tasks triggered. Monitor in GCP Console."
