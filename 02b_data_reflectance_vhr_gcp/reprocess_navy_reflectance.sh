#!/bin/bash
# Description: Triggers reflectance reprocessing for Navy North Slope strips to harmonize with Nome Beaver structure.
# This only triggers the CPU phase. GPU CHM phase must be triggered separately.

ORDERS=(
    "gs://akveg-data/vhr/navy_north_slope/orders/050300601010_01"
    "gs://akveg-data/vhr/navy_north_slope/orders/050300602010_01"
    "gs://akveg-data/vhr/navy_north_slope/orders/050300603010_01"
)

OUTPUT_BASE="gs://akveg-data/vhr/navy_north_slope/processed"
# Standard Copernicus DEM for North Slope
DEM_PATH="gs://akveg-data/vhr/ancillary/dem/Copernicus_DSM_COG_10_N70_00_W157_00_DEM.tif"

# Deploy the updated orchestrator first to ensure ee_project parameter is supported
echo "Deploying updated vhr-pipeline-orchestrator workflow..."
gcloud workflows deploy vhr-pipeline-orchestrator \
    --source=vhr_orchestrator.yaml \
    --location=us-central1

echo "Reprocessing 3 Navy North Slope orders into standard structure (using teck project for GEE)..."

for ORDER in "${ORDERS[@]}"; do
    echo "Submitting CPU pipeline job for: $ORDER"
    
    gcloud workflows execute vhr-pipeline-orchestrator \
        --location=us-central1 \
        --data="{
            \"input_dir\": \"$ORDER\",
            \"output_base\": \"$OUTPUT_BASE\",
            \"dem_path\": \"$DEM_PATH\",
            \"ccdc_ee_project\": \"abr-gee-teck\",
            \"skip_seg\": false,
            \"use_spot\": false
        }"
    
    echo "Job submitted for $(basename $ORDER). Waiting 10 seconds before next submission..."
    sleep 10
done

echo "All CPU reprocessing jobs submitted. Monitor them in the GCP console."
