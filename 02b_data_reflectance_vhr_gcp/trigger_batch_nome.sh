#!/bin/bash

# Reads from nome_orders.list
# Only processes lines starting with "TODO"

LIST_FILE="nome_orders.list"
OUTPUT_BASE="gs://akveg-data/vhr/nome_beaver/processed"

if [ ! -f "$LIST_FILE" ]; then
    echo "Error: $LIST_FILE not found."
    exit 1
fi

echo "Looking for 'TODO' orders in $LIST_FILE..."

while read -r STATUS INPUT_DIR; do
    if [[ "$STATUS" == "TODO" ]]; then
        CLEAN_INPUT=${INPUT_DIR%/}
        
        echo "Calculating size for $CLEAN_INPUT ..."
        SIZE_BYTES=$(gsutil du -s "$CLEAN_INPUT" | awk '{print $1}')
        SIZE_GB=$((SIZE_BYTES / 1024 / 1024 / 1024))
        
        # Dynamic Disk Allocation: (Input Size * 12) + 100GB Buffer
        # This accounts for the ~10x expansion during full resolution processing
        DISK_GB=$(( SIZE_GB * 12 + 100 ))
        
        # Performance Floor: Ensure at least 400GB to get ~190 MB/s (pd-ssd).
        # Small disks (200GB) throttle I/O to ~56 MB/s, causing CPU wait.
        [ "$DISK_GB" -lt 400 ] && DISK_GB=400
        
        echo "Triggering workflow for $CLEAN_INPUT (Input: ${SIZE_GB}GB -> Allocating: ${DISK_GB}GB)..."
        gcloud workflows execute vhr-pipeline-orchestrator \
            --location=us-central1 \
            --data="{
                \"dem_path\": \"gs://akveg-data/dem/alaska_ifsar_dsm_20200925_plus_us_noaa_g2009_cog1024_noLerc_deflate3.tif\",
                \"input_dir\": \"$CLEAN_INPUT\",
                \"output_base\": \"$OUTPUT_BASE\",
                \"res_pan\": 0.5,
                \"res_ms\": 2.0,
                \"skip_seg\": true,
                \"disk_size_gb\": $DISK_GB,
                \"boot_disk_type\": \"pd-ssd\",
                \"use_spot\": true
            }"
            
        # Safely update status in the file from TODO to SUBMITTED
        sed -i "s|^TODO[[:space:]]*$INPUT_DIR|SUBMITTED $INPUT_DIR|" "$LIST_FILE"
        sleep 2 # Slight delay between API calls
    fi
done < <(grep -v '^#' "$LIST_FILE")

echo "Done."
