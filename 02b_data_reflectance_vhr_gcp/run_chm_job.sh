#!/bin/bash
set -e
set -x

# V4.6 Production Runner - Pure FUSE / Conda-Python
# Assumes gs://akveg-data is mounted at /mnt/disks/akveg

# 1. EXPLICIT ENVIRONMENT
PYTHON_BIN="/opt/conda/bin/python"

echo "[$(date)] --- INITIALIZING SUICIDE CHECK ---"

# Check 1: Tool Paths
$PYTHON_BIN --version || { echo "ERROR: Conda Python not found at $PYTHON_BIN"; exit 1; }

# Check 2: GCS Mount Writeability
TEST_FILE="/mnt/disks/akveg/vhr/navy_north_slope/test_write_${BATCH_JOB_ID}.tmp"
touch "$TEST_FILE" && rm "$TEST_FILE" || { echo "ERROR: GCS Mount is not writeable at /mnt/disks/akveg"; exit 1; }

# Check 3: Python Environment
$PYTHON_BIN -c "import torch; import rasterio; from transformers import AutoModelForDepthEstimation" || { echo "ERROR: Python environment incomplete at $PYTHON_BIN"; exit 1; }

echo "[$(date)] --- ENVIRONMENT VERIFIED ---"

# 2. Path Discovery
if [ -n "$HF_TOKEN" ]; then
    export HF_TOKEN=$(echo "$HF_TOKEN" | tr -d '[:space:]')
fi

FILENAME=$(basename "$GCS_INPUT_IMAGE")
STRIP_ID=$(echo "$FILENAME" | grep -oE '[0-9]{8}_[0-9]{6}_[A-Z0-9]+_[A-Z0-9]+')
STRIP_ROOT_GCS=$(dirname $(dirname "$GCS_INPUT_IMAGE"))

# Local Workspaces
PROCESSED_DIR="/tmp/processed"
mkdir -p "$PROCESSED_DIR"

OUTPUT_BASENAME="CHM_cm_DINOv3_${STRIP_ID}.tif"
RAW_LOCAL="${PROCESSED_DIR}/CHM_raw.tif"
COG_LOCAL="${PROCESSED_DIR}/${OUTPUT_BASENAME}"
METRICS_LOCAL="${PROCESSED_DIR}/CHM_raw_metrics.json"

# GCS Target Paths (Mapped to Mount)
GCS_COG_MOUNT="/mnt/disks/akveg/${STRIP_ROOT_GCS#gs://akveg-data/}/250_cog/${OUTPUT_BASENAME}"
GCS_METRICS_MOUNT="/mnt/disks/akveg/${STRIP_ROOT_GCS#gs://akveg-data/}/230_chm/CHM_cm_DINOv3_${STRIP_ID}_metrics.json"
GCS_LOG_DIR_MOUNT="/mnt/disks/akveg/${STRIP_ROOT_GCS#gs://akveg-data/}/processing_logs"

# 3. Execute CHM Inference
echo "[$(date)] Starting CHM Inference (V4.6)..."

# Conditional tile limiting
if [ -n "$LIMIT_TILES" ] && [ "$LIMIT_TILES" -gt 0 ]; then
    LIMIT_ARGS="--limit-tiles $LIMIT_TILES"
fi
if [ -n "$START_TILE" ] && [ "$START_TILE" -gt 0 ]; then
    export START_TILE=$START_TILE
fi

# Heartbeat log via CP
STATUS_FILE="/tmp/chm_status.json"
mkdir -p "$GCS_LOG_DIR_MOUNT"
HEARTBEAT_REMOTE="${GCS_LOG_DIR_MOUNT}/heartbeat_${BATCH_JOB_ID}.json"

while true; do
    if [ -f "$STATUS_FILE" ]; then
        cp "$STATUS_FILE" "$HEARTBEAT_REMOTE" || true
    fi
    sleep 60
done &
HEARTBEAT_PID=$!

$PYTHON_BIN -u /mnt/disks/akveg/scripts/vhr_pipeline/230_predict_chm_dinov3.py \
    --input "/mnt/disks/akveg/${GCS_INPUT_IMAGE#gs://akveg-data/}" \
    --output "$RAW_LOCAL" \
    --status-file "$STATUS_FILE" \
    $LIMIT_ARGS

kill $HEARTBEAT_PID || true

# 4. Local COG Generation
echo "[$(date)] Generating optimized COG locally..."
gdal_translate "$RAW_LOCAL" "$COG_LOCAL" \
    -of COG -co COMPRESS=DEFLATE -co PREDICTOR=2 -co BIGTIFF=YES -co NUM_THREADS=ALL -q

# 5. Final Upload via CP + Sync
echo "[$(date)] Uploading results to GCS mount..."
mkdir -p "$(dirname "$GCS_COG_MOUNT")"
cp "$COG_LOCAL" "$GCS_COG_MOUNT"
sync "$GCS_COG_MOUNT"

if [ -f "$METRICS_LOCAL" ]; then
    mkdir -p "$(dirname "$GCS_METRICS_MOUNT")"
    cp "$METRICS_LOCAL" "$GCS_METRICS_MOUNT"
    sync "$GCS_METRICS_MOUNT"
fi

echo "[$(date)] Job Complete. Output verified at $GCS_COG_MOUNT"
