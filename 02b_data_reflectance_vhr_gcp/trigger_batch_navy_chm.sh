#!/bin/bash
# Description: Triggers the CHM GPU batch job for Navy North Slope sites.
# Supports both the temporary flat structure and the standard harmonized structure.
# Usage: ./trigger_batch_navy_chm.sh [test|all|harmonized]

MODE=${1:-test}
BASE_DIR="gs://akveg-data/vhr/vhr_cogs_snap"
HARMONIZED_DIR="gs://akveg-data/vhr/navy_north_slope/processed"
PROJECT_ID=$(gcloud config get-value project)

# Deploy the workflow first
echo "Deploying chm-pipeline-orchestrator workflow..."
gcloud workflows deploy chm-pipeline-orchestrator \
    --source=chm_orchestrator.yaml \
    --location=us-central1

if [ "$MODE" == "test" ]; then
    echo "Running in TEST mode (Single Smallest Image from flat bucket)"
    SMALLEST_IMAGE_URL=$(gsutil ls -l "${BASE_DIR}/PS_SRLite*cog.tif" | grep -v TOTAL | sort -n -k1 | head -n 1 | awk '{print $3}')
    
    if [ -z "$SMALLEST_IMAGE_URL" ]; then
        echo "Error: Could not find any PS SRLite images for testing in $BASE_DIR"
        exit 1
    fi
    
    echo "Smallest image found: $SMALLEST_IMAGE_URL"
    
    gcloud workflows execute chm-pipeline-orchestrator \
        --location=us-central1 \
        --data="{
            \"input_image\": \"$SMALLEST_IMAGE_URL\",
            \"disk_size_gb\": 100,
            \"use_spot\": false
        }"
        
    echo "Test job submitted."

elif [ "$MODE" == "harmonized" ]; then
    echo "Running in HARMONIZED mode (Strips in standard subfolders)"
    # This mode expects strips in gs://.../processed/{STRIP_ID}/225_srlite/
    
    STRIP_DIRS=$(gsutil ls -d "${HARMONIZED_DIR}/*/")
    
    for STRIP_DIR in $STRIP_DIRS; do
        STRIP_DIR=${STRIP_DIR%/}
        STRIP_ID=$(basename "$STRIP_DIR")
        
        # Find the PS SRLite in the standard location
        IMAGE_URL=$(gsutil ls "${STRIP_DIR}/225_srlite/*PS*SRLite*.tif" | head -n 1 || true)
        
        if [ -n "$IMAGE_URL" ]; then
            # Check if CHM already exists in the standard location
            CHM_CHECK=$(gsutil ls "${STRIP_DIR}/230_chm/*_CHM.tif" 2>/dev/null || true)
            
            if [ -z "$CHM_CHECK" ]; then
                echo "Submitting harmonized CHM job for: $STRIP_ID"
                gcloud workflows execute chm-pipeline-orchestrator \
                    --location=us-central1 \
                    --data="{
                        \"input_image\": \"$IMAGE_URL\",
                        \"disk_size_gb\": 200,
                        \"use_spot\": true
                    }"
                sleep 2
            else
                echo "Skipping $STRIP_ID: CHM already exists."
            fi
        else
            echo "Skipping $STRIP_ID: No PS SRLite found in 225_srlite/"
        fi
    done

elif [ "$MODE" == "all" ]; then
    echo "Running in ALL mode (Legacy Flat bucket)"
    IMAGES=$(gsutil ls "${BASE_DIR}/PS_SRLite*cog.tif")
    for IMAGE_URL in $IMAGES; do
        BASENAME=$(basename "$IMAGE_URL")
        CHM_NAME="${BASENAME%.*}_CHM.tif"
        CHM_CHECK=$(gsutil ls "${BASE_DIR}/${CHM_NAME}" 2>/dev/null || true)
        if [ -z "$CHM_CHECK" ]; then
            echo "Submitting CHM job for: $BASENAME"
            gcloud workflows execute chm-pipeline-orchestrator \
                --location=us-central1 \
                --data="{
                    \"input_image\": \"$IMAGE_URL\",
                    \"disk_size_gb\": 200,
                    \"use_spot\": true
                }"
            sleep 2
        else
            echo "Skipping $BASENAME: CHM already exists."
        fi
    done
else
    echo "Usage: $0 [test|all|harmonized]"
    exit 1
fi
