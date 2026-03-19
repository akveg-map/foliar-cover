#!/bin/bash
set -e
set -x

# --- LOGGING SETUP ---
LOG_FILE="/tmp/job_all.log"
exec > >(tee -a "$LOG_FILE") 2>&1

# Define paths early for logging trap
RAW_DIR="/mnt/local_ssd/raw"
PROCESSED_DIR="/mnt/local_ssd/processed"
DIR_ORTHO="${PROCESSED_DIR}/200_ortho"
DIR_TOA="${PROCESSED_DIR}/205_ortho_toa"
DIR_CLOUD="${PROCESSED_DIR}/210_cloud"
DIR_PAN="${PROCESSED_DIR}/212_pansharpen"
DIR_SRLITE="${PROCESSED_DIR}/225_srlite"
DIR_SRLITE_INPUT="${PROCESSED_DIR}/220_srlite_input"
DIR_COGS="${PROCESSED_DIR}/250_cogs"
DIR_CCDC="${PROCESSED_DIR}/202_ccdc_sr"

ORDER_ID=$(basename "${GCS_INPUT_PATH}")
CENTRAL_LOG_DIR="${GCS_OUTPUT_PATH}/processing_logs"
# GCS_SYNC_PATH will be determined dynamically

upload_log() {
    EXIT_CODE=$?
    [ -n "$HEARTBEAT_PID" ] && kill $HEARTBEAT_PID 2>/dev/null

    echo "Pipeline finishing with exit code $EXIT_CODE"
    
    IMG_ID="Unknown_Image"
    FOUND=$(find "$PROCESSED_DIR" -type f 2>/dev/null | grep -oE '[0-9]{8}_[0-9]{6}_[A-Z0-9]+' | head -n 1)
    [ -n "$FOUND" ] && IMG_ID="$FOUND"
    
    if [ "$IMG_ID" == "Unknown_Image" ] && [ -d "$RAW_DIR" ]; then
        FOUND=$(ls "$RAW_DIR" 2>/dev/null | grep -oE '^[0-9]{2}[A-Z]{3}[0-9]{8}' | head -n 1)
        [ -n "$FOUND" ] && IMG_ID="$FOUND"
    fi

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    LOG_NAME="${IMG_ID}_JobAll_${TIMESTAMP}.txt"
    
    echo "Uploading log to ${CENTRAL_LOG_DIR}/${LOG_NAME}"
    gcloud storage cp "$LOG_FILE" "${CENTRAL_LOG_DIR}/${LOG_NAME}" || echo "Log upload failed"

    # Hybrid Approach: Also upload to the specific image folder if we got far enough to know it
    if [ -n "$GCS_SYNC_PATH" ]; then
        echo "Archiving log to ${GCS_SYNC_PATH}/${LOG_NAME}"
        gcloud storage cp "$LOG_FILE" "${GCS_SYNC_PATH}/${LOG_NAME}" || true
    fi

    # Remove the running log to prevent stale status in monitoring
    gcloud storage rm "${CENTRAL_LOG_DIR}/${IMG_ID}_JobAll_Running.log" 2>/dev/null || true
}
trap upload_log EXIT
# ---------------------

# --- STARTUP BEACON ---
echo "All-in-One Container Started on $(hostname)" > /tmp/startup_all.txt
gcloud storage cp /tmp/startup_all.txt "${CENTRAL_LOG_DIR}/startup_all_$(date +%s).txt" || echo "Startup beacon upload failed"

echo "[$(date)] === Environment Check ==="
python3 --version
python3 -c "import numpy; print(f'Numpy: {numpy.__version__}')"
python3 -c "from osgeo import gdal; print(f'GDAL: {gdal.__version__}')"
export PYTHONUNBUFFERED=1

echo "[$(date)] === Dynamically pulling latest Python scripts ==="
mkdir -p /app/vhr-pipeline
gcloud storage cp "gs://akveg-data/scripts/vhr_pipeline/*.py" /app/vhr-pipeline/

echo "[$(date)] === Setup & Downloads ==="
mkdir -p "$RAW_DIR" "$PROCESSED_DIR" "$DIR_ORTHO" "$DIR_TOA" "$DIR_CLOUD" "$DIR_PAN" "$DIR_SRLITE" "$DIR_SRLITE_INPUT" "$DIR_COGS" "$DIR_CCDC"

echo "[$(date)] Syncing raw inputs from ${GCS_INPUT_PATH} to ${RAW_DIR}/"
# Use rsync so it skips files that are already downloaded if the job was preempted and restarted.
gcloud storage rsync -r "${GCS_INPUT_PATH}/" "${RAW_DIR}/"

# Calculate and log input size for monitoring
INPUT_SIZE_MB=$(du -sm "${RAW_DIR}" | awk '{print $1}')
echo "[STATS] Input_Size_MB: ${INPUT_SIZE_MB}"

echo "[$(date)] Extracting Strip ID and creating metadata.json..."
cat << 'EOF' > /tmp/extract_meta.py
import glob, re, os, json, sys
from datetime import datetime

raw_dir = sys.argv[1]
order_id = sys.argv[2]
processed_dir = sys.argv[3]

xml_files = glob.glob(os.path.join(raw_dir, '**', '*.XML'), recursive=True) + glob.glob(os.path.join(raw_dir, '**', '*.xml'), recursive=True)

strip_id = order_id
if xml_files:
    xml_file = sorted(xml_files)[0]
    catid = sensor = timestamp = None
    with open(xml_file, 'r', errors='ignore') as f:
        c = f.read()
        m = re.search(r'<CATID>([A-F0-9]+)</CATID>', c, re.IGNORECASE)
        if m: catid = m.group(1)
        m = re.search(r'<SATID>(\S+)</SATID>', c, re.IGNORECASE)
        if m: sensor = m.group(1)
        m = re.search(r'<(?:EARLIESTACQTIME|FIRSTLINETIME)>(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', c, re.IGNORECASE)
        if m:
            dt = datetime.strptime(m.group(1), '%Y-%m-%dT%H:%M:%S')
            timestamp = dt.strftime('%Y%m%d_%H%M%S')
            
    if catid and sensor and timestamp:
        strip_id = f"{timestamp}_{sensor}_{catid}"

files = [os.path.basename(f) for f in glob.glob(os.path.join(raw_dir, '**', '*'), recursive=True) if os.path.isfile(f)]
meta_path = os.path.join(processed_dir, 'order_metadata.json')
os.makedirs(processed_dir, exist_ok=True)
data = {
    'order_id': order_id,
    'strip_id': strip_id,
    'input_images': sorted(files)
}
with open(meta_path, 'w') as f:
    json.dump(data, f, indent=4)

print(strip_id)
EOF

STRIP_ID=$(python3 /tmp/extract_meta.py "${RAW_DIR}" "${ORDER_ID}" "${PROCESSED_DIR}")
echo "[$(date)] Determined STRIP_ID: $STRIP_ID"
GCS_SYNC_PATH="${GCS_OUTPUT_PATH}/${STRIP_ID}"

echo "[$(date)] Syncing intermediate products from ${GCS_SYNC_PATH} to ${PROCESSED_DIR}/"
# Use rsync so pre-existing intermediate files populate PROCESSED_DIR and python scripts can skip them.
gcloud storage rsync -r "${GCS_SYNC_PATH}/" "${PROCESSED_DIR}/" || true

VSIGS_DEM_PATH=$(echo "${DEM_PATH}" | sed 's|gs://|/vsigs/|')

# Parse GCS_SYNC_PATH for CCDC export
NO_SCHEME=${GCS_SYNC_PATH#gs://}
BUCKET=${NO_SCHEME%%/*}
if [[ "$NO_SCHEME" == *"/"* ]]; then
    BASE_PREFIX=${NO_SCHEME#*/}
else
    BASE_PREFIX=""
fi
CCDC_PREFIX="${BASE_PREFIX}/202_ccdc_sr"
CCDC_PREFIX=${CCDC_PREFIX#/}

# Capture available CPUs globally for use in scripts
N_CPUS=$(nproc || echo 4)

# --- HEARTBEAT LOGGING ---
(
    set +x # Disable debug echo for the heartbeat loop to keep log clean
    SUM_LOAD=0
    COUNT=0
    MAX_MEM=0
    
    while true; do
        sleep 60

        # --- STATS COLLECTION ---
        # Load Average (1 min)
        CURRENT_LOAD=$(awk '{print $1}' /proc/loadavg)
        
        # Memory (MB) - Parse free -m output (Total, Used, Free+Buffers/Cache)
        read MEM_TOTAL MEM_USED MEM_AVAIL <<< $(free -m | awk '/Mem:/ {print $2, $3, $7}')
        
        # Calculate Memory Percentage
        MEM_PCT=$(awk "BEGIN {printf \"%d\", ($MEM_USED / $MEM_TOTAL) * 100}")
        MEM_TOTAL_GB=$(awk "BEGIN {printf \"%.1fG\", $MEM_TOTAL / 1024}")
        MEM_AVAIL_GB=$(awk "BEGIN {printf \"%.1fG\", $MEM_AVAIL / 1024}")
        
        # Update Max Mem & Avg Load
        [ "$MEM_USED" -gt "$MAX_MEM" ] && MAX_MEM=$MEM_USED
        MAX_MEM_PCT=$(awk "BEGIN {printf \"%d\", ($MAX_MEM / $MEM_TOTAL) * 100}")
        
        SUM_LOAD=$(awk "BEGIN {print $SUM_LOAD + $CURRENT_LOAD}")
        COUNT=$((COUNT + 1))
        AVG_LOAD=$(awk "BEGIN {printf \"%.2f\", $SUM_LOAD / $COUNT}")
        
        # Disk Space
        # Get Human Readable for display
        # Columns: Size(2), Used(3), Avail(4), Use%(5)
        read DISK_SIZE DISK_USED DISK_AVAIL DISK_PCT <<< $(df -h /mnt/local_ssd | tail -n 1 | awk '{print $2, $3, $4, $5}')
        # Get MB for precise tracking
        read DISK_USED_MB <<< $(df -m /mnt/local_ssd | tail -n 1 | awk '{print $3}')
        
        # Remove the '%' sign from DISK_PCT for clean numbers, and keep track of max disk pct
        DISK_PCT_NUM=${DISK_PCT%\%}
        [ -z "$MAX_DISK_PCT" ] && MAX_DISK_PCT=0
        [ "$DISK_PCT_NUM" -gt "$MAX_DISK_PCT" ] && MAX_DISK_PCT=$DISK_PCT_NUM
        
        # Track Max Used MB
        [ -z "$MAX_DISK_USED_MB" ] && MAX_DISK_USED_MB=0
        [ "$DISK_USED_MB" -gt "$MAX_DISK_USED_MB" ] && MAX_DISK_USED_MB=$DISK_USED_MB
        
        # Log Stats (Goes to stdout -> tee -> logfile)
        # Appending MaxUsedMB as 5th field in Disk_Stats
        echo "[$(date)] [STATS] CPU_Load: ${CURRENT_LOAD}/${AVG_LOAD}/${N_CPUS} | Mem_Stats: ${MEM_PCT}%/${MAX_MEM_PCT}%/${MEM_AVAIL_GB}/${MEM_TOTAL_GB} | Disk_Stats: ${DISK_PCT_NUM}%/${MAX_DISK_PCT}%/${DISK_AVAIL}/${DISK_SIZE}/${MAX_DISK_USED_MB}M"

        HB_ID="Unknown"
        FOUND=$(find "$PROCESSED_DIR" -type f 2>/dev/null | grep -oE '[0-9]{8}_[0-9]{6}_[A-Z0-9]+' | head -n 1)
        [ -n "$FOUND" ] && HB_ID="$FOUND"
        
        if [ "$HB_ID" == "Unknown" ] && [ -d "$RAW_DIR" ]; then
            FOUND=$(ls "$RAW_DIR" 2>/dev/null | grep -oE '^[0-9]{2}[A-Z]{3}[0-9]{8}' | head -n 1)
            [ -n "$FOUND" ] && HB_ID="$FOUND"
        fi
        gcloud storage cp "$LOG_FILE" "${CENTRAL_LOG_DIR}/${HB_ID}_JobAll_Running.log" >/dev/null 2>&1
    done
) &
HEARTBEAT_PID=$!

# --- IN-PLACE COG CONVERSION FUNCTION ---
# This saves massive amounts of disk space by compressing large uncompressed TIFFs 
# immediately after a step generates them, while keeping the original filename 
# so downstream python scripts don't break.
compress_in_place() {
    local TARGET_DIR=$1
    echo "[$(date)] [Cleanup] Compressing files in $TARGET_DIR to COG in-place..."
    
    # Temporarily disable set -e just for this loop to prevent a single file failure from killing the job
    set +e 
    for file in "$TARGET_DIR"/*.tif; do
        [ -e "$file" ] || continue
        
        # Don't double-compress files that might already be compressed
        # GDAL sometimes complains or bloats if you COG a COG
        if gdalinfo "$file" | grep -q "LAYOUT=COG"; then
            continue
        fi

        base_name="${file%.tif}"
        noncog_name="${base_name}_noncog.tif"
        
        echo "  - Compressing $(basename "$file")..."
        RESAMPLING="AVERAGE"
        if [[ "$file" == *"_cloud"* ]]; then
            RESAMPLING="MODE"
        fi

        mv "$file" "$noncog_name"
        
        # Note: We output back to the original filename so Python scripts can still find it later
        if gdal_translate "$noncog_name" "$file" -of COG -co COMPRESS=DEFLATE -co PREDICTOR=2 -co BIGTIFF=YES -co OVERVIEW_RESAMPLING="$RESAMPLING" -co NUM_THREADS=$N_CPUS -q; then
            rm "$noncog_name"
        else
            echo "    Warning: GDAL compression failed. Reverting to original."
            mv "$noncog_name" "$file"
        fi
    done
    set -e

    echo "[$(date)] [Sync] Uploading intermediate products from $TARGET_DIR to GCS..."
    # basename extracts the folder name (e.g., 205_ortho_toa) so it uploads to the correct subfolder
    gcloud storage cp -r "$TARGET_DIR"/* "${GCS_SYNC_PATH}/$(basename "$TARGET_DIR")/" || true
}

echo "[$(date)] === EXECUTING PIPELINE ==="

ORTHO_ARGS="--input ${RAW_DIR} --output ${DIR_ORTHO} --dem ${VSIGS_DEM_PATH} --epsg 3338"
[ -n "${RES_PAN}" ] && ORTHO_ARGS="${ORTHO_ARGS} --res-pan ${RES_PAN}"
[ -n "${RES_MS}" ] && ORTHO_ARGS="${ORTHO_ARGS} --res-ms ${RES_MS}"

echo "[$(date)] [Step 200] Orthorectification..."
python3 vhr-pipeline/200_ortho_pgc_warp.py ${ORTHO_ARGS}

# Cleanup Raw files to save space (Ortho contains everything we need now)
echo "[$(date)] [Cleanup] Removing raw input files..."
rm -rf "${RAW_DIR}"/*

echo "[$(date)] [Sync] Uploading Ortho products to GCS to act as a preemption checkpoint..."
gcloud storage cp -r "${DIR_ORTHO}"/* "${GCS_SYNC_PATH}/200_ortho/" || true

echo "[$(date)] [Step 202] CCDC Export..."
python3 vhr-pipeline/202_export_ccdc_sr.py --input ${DIR_ORTHO} --project "${GOOGLE_CLOUD_PROJECT}" --bucket "${BUCKET}" --prefix "${CCDC_PREFIX}"

echo "[$(date)] [Step 205] TOA Calculation..."
python3 vhr-pipeline/205_batch_calc_toa.py --input "${DIR_ORTHO}" --output "${DIR_TOA}"
compress_in_place "${DIR_TOA}"

echo "[$(date)] [Step 210] Cloud Masking..."
# Using batch size 4 and CPU-friendly types (float32) to avoid OOM on smaller VMs
python3 vhr-pipeline/210_generate_cloud_mask.py --input "${DIR_TOA}" --output "${DIR_CLOUD}" --batch-size 4 --device cpu --dtype float32
compress_in_place "${DIR_CLOUD}"

echo "[$(date)] [Step 212] Pansharpening..."
python3 vhr-pipeline/212_pansharpen_gram_schmidt.py --input "${DIR_TOA}" --output "${DIR_PAN}"
compress_in_place "${DIR_PAN}"

echo "[$(date)] [Step 220] Calculate SRLite Params..."
python3 vhr-pipeline/220_calculate_srlite_params.py --vhr-dir "$DIR_TOA" "$DIR_PAN" --cloud-dir "$DIR_CLOUD" --ccdc-dir "$DIR_CCDC" --output-dir "${DIR_SRLITE}" --intermediate-dir "${DIR_SRLITE_INPUT}" --bucket "${BUCKET}" --prefix "${CCDC_PREFIX}"
compress_in_place "${DIR_SRLITE_INPUT}"

echo "[$(date)] [Step 225] Apply SRLite..."
python3 vhr-pipeline/225_apply_srlite.py --input-dir "$DIR_TOA" "$DIR_PAN" --params-dir "${DIR_SRLITE}" --output-dir "${DIR_SRLITE}"
compress_in_place "${DIR_SRLITE}"

# Cleanup massive intermediate files to prevent disk full errors, 
# BUT keep the final products (TOA, PAN, SRLITE, CLOUD) for upload.
echo "[$(date)] [Cleanup] Removing bulky uncompressed Ortho files..."
rm -rf "${DIR_ORTHO}"/*

# Also remove the intermediate ortho backup from GCS now that the pipeline is complete
echo "[$(date)] [Cleanup] Removing intermediate Ortho checkpoint from GCS..."
gcloud storage rm -r "${GCS_SYNC_PATH}/200_ortho" 2>/dev/null || true

# Step 250 (COG Generation) has been removed because files are now compressed in-place 
# automatically after each step via the compress_in_place function.

# Remove empty directories to prevent gcloud storage cp from failing
rm -rf "${DIR_ORTHO}" "${DIR_COGS}"

echo "[$(date)] === UPLOADING FINAL RESULTS ==="
# Only upload the final usable assets to keep GCS clean (or upload all processed if desired)
# For now, uploading all subdirectories just like the previous pipeline did.
gcloud storage cp -r "${PROCESSED_DIR}/"* "${GCS_SYNC_PATH}"/ || true

echo "[$(date)] [Step 256] Generating GEE Script..."
# Run against the GCS path so it picks up all uploaded files recursively
python3 vhr-pipeline/256_create_gee_script.py --input-dir "${GCS_SYNC_PATH}" --output "${PROCESSED_DIR}/${STRIP_ID}_viz.js"
# Upload the generated script
gcloud storage cp "${PROCESSED_DIR}/${STRIP_ID}_viz.js" "${GCS_SYNC_PATH}/"

if [ "$SKIP_SEG" != "true" ]; then
    echo "[$(date)] === RUNNING SEGMENTATION ==="
    for cog in ${DIR_SRLITE}/*SRLite*.tif; do
        if [ -f "$cog" ]; then
            fname=$(basename "$cog")
            # Since the structure in GCS mirrors PROCESSED_DIR, it uploads to {BASE_PREFIX}/225_srlite/
            gcs_uri="gs://${BUCKET}/${BASE_PREFIX}/225_srlite/${fname}"
            asset_id="projects/${GOOGLE_CLOUD_PROJECT}/assets/segments/${fname%.*}"
            
            echo "Submitting segmentation for ${fname}..."
            python3 vhr-pipeline/261_segmentation.py --image "${gcs_uri}" --asset-id "${asset_id}" || echo "Segmentation submission failed"
        fi
    done
else
    echo "[$(date)] Skipping Segmentation (SKIP_SEG=true)"
fi

echo "[$(date)] Pipeline Complete."