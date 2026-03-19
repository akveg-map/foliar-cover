#!/bin/bash

# Configuration
# Default to 'processed', but allow override via argument
TARGET_DIR="${1:-processed}"
LOG_DIR="gs://akveg-data/vhr/nome_beaver/${TARGET_DIR}/processing_logs"

echo "=========================================================="
echo "      VHR Pipeline Status Summary (Nome Beaver)           "
echo "=========================================================="
echo ""

# Helper to format seconds to HH:MM:SS
format_duration() {
    local T=$1
    local H=$((T/3600))
    local M=$(( (T%3600)/60 ))
    local S=$((T%60))
    printf "%02d:%02d:%02d" $H $M $S
}

# 1. Gather all log files
echo "Fetching log list from GCS..."
# We dump the list to a temporary file to avoid repeated API calls
gcloud storage ls -l "$LOG_DIR" | grep ".txt\|.log" | grep -v "startup_all" > /tmp/vhr_logs_raw.txt

if [ ! -s /tmp/vhr_logs_raw.txt ]; then
    echo "No processing logs found in $LOG_DIR."
    exit 0
fi

# Clean up the output to just file size, date, and path
awk '{print $1, $2, $3}' /tmp/vhr_logs_raw.txt > /tmp/vhr_logs.txt

# 2. Separate into Completed vs Running
COMPLETED_LOGS=$(grep ".txt" /tmp/vhr_logs.txt)
RUNNING_LOGS=$(grep "_Running.log" /tmp/vhr_logs.txt | grep -v "\.gstmp")

echo "-------------------------------------------------------------------------------------------------------------------"
echo "                                     CURRENTLY RUNNING JOBS                                         "
echo "-------------------------------------------------------------------------------------------------------------------"
printf "%-25s | %-20s | %-10s | %-20s | %-22s | %-22s | %-10s | %s\n" "IMAGE ID" "START TIME" "DURATION" "CPU (CUR/AVG/LD/N)" "MEM (CUR%/MAX%/AV/TOT)" "DISK (CUR%/MAX%/AV/TOT)" "INPUT" "CURRENT STEP"
echo "-------------------------------------------------------------------------------------------------------------------"
if [ -z "$RUNNING_LOGS" ]; then
    echo "No actively running jobs detected (no *_Running.log files found)."
else
    # Loop through running logs and fetch their last step
    echo "$RUNNING_LOGS" | while read -r SIZE DATE PATH_URI; do
        FILENAME=$(basename "$PATH_URI")
        IMAGE_ID=${FILENAME%_JobAll_Running.log}
        
        # Check if a completed log exists for this exact Image ID
        # If it does, check timestamps to see if this is a retry (Running > Completed)
        MATCHING_COMPLETED=$(echo "$COMPLETED_LOGS" | grep "${IMAGE_ID}_JobAll_")
        
        if [ -n "$MATCHING_COMPLETED" ]; then
            # Get the latest completed date (Column 2 is date in ISO format)
            LATEST_COMPLETED_DATE=$(echo "$MATCHING_COMPLETED" | sort -k2 -r | head -n 1 | awk '{print $2}')
            
            # If Running Log Date is older or equal to Completed Log Date, it's stale.
            if [[ "$DATE" < "$LATEST_COMPLETED_DATE" ]] || [[ "$DATE" == "$LATEST_COMPLETED_DATE" ]]; then
                continue
            fi
        fi

        # Fetch content once
        LOG_CONTENT=$(gcloud storage cat "$PATH_URI" 2>/dev/null)
        
        # Extract Start Time (First line with [Date])
        START_LINE=$(echo "$LOG_CONTENT" | grep -m 1 "^\[")
        START_TIME_STR="Unknown"
        DURATION_STR="--"
        
        if [ -n "$START_LINE" ]; then
            # Extract content between [ ]
            TS_STR=$(echo "$START_LINE" | sed -n 's/^\[\(.*\)\] .*/\1/p')
            START_SEC=$(date -d "$TS_STR" +%s 2>/dev/null)
            if [ -n "$START_SEC" ]; then
                START_TIME_STR=$(date -d "@$START_SEC" "+%Y-%m-%d %H:%M:%S")
                NOW_SEC=$(date +%s)
                DURATION_SEC=$((NOW_SEC - START_SEC))
                DURATION_STR=$(format_duration $DURATION_SEC)
            fi
        fi

        # Extract Stats (Last line with [STATS])
        STATS_LINE=$(echo "$LOG_CONTENT" | grep "\[STATS\]" | tail -n 1)
        CPU_STATS="--"
        MEM_STATS="--"
        DISK_STATS="--"
        
        # Extract Input Size if available
        INPUT_MB=$(echo "$LOG_CONTENT" | grep "Input_Size_MB:" | tail -n 1 | sed 's/.*Input_Size_MB: //' | awk '{print $1}')
        INPUT_STR="--"
        if [ -n "$INPUT_MB" ] && [ "$INPUT_MB" -gt 0 ]; then
            INPUT_GB=$(awk "BEGIN {printf \"%.1f\", $INPUT_MB / 1024}")
            INPUT_STR="${INPUT_GB}G"
        fi
        
        if [ -n "$STATS_LINE" ]; then
            # Format New: [STATS] CPU_Load: 1.05/0.80/8 | Mem_Stats: ...
            # Format Old: [STATS] CPU_Load: 1.05/0.80 | Mem_MB: 4500/5000/32000 | Disk_Cur/Max: 45G/200G
            CPU_VALS=$(echo "$STATS_LINE" | grep -o "CPU_Load: [0-9./]*" | cut -d' ' -f2)
            MEM_VALS=$(echo "$STATS_LINE" | grep -o -E "Mem_(MB|Stats): [0-9A-Za-z%./]*" | cut -d' ' -f2)
            DISK_VALS=$(echo "$STATS_LINE" | grep -o -E "Disk_(Used/Avail|Cur/Max|Stats): [0-9A-Za-z%./]*" | cut -d' ' -f2)
            
            if [ -n "$CPU_VALS" ]; then
                CUR=$(echo "$CPU_VALS" | cut -d'/' -f1)
                AVG=$(echo "$CPU_VALS" | cut -d'/' -f2)
                N_CPUS=$(echo "$CPU_VALS" | cut -d'/' -f3)
                [ -z "$N_CPUS" ] && N_CPUS=4
                # Calculate Load Factor (AVG / 4 cores)
                LOAD_FACTOR=$(awk "BEGIN {printf \"%.1f\", $AVG / $N_CPUS}")
                CPU_STATS="${CUR}/${AVG}/${LOAD_FACTOR}/${N_CPUS}C"
            fi
            
            if [ -n "$MEM_VALS" ]; then
                if [[ "$STATS_LINE" == *"Mem_Stats"* ]]; then
                     MEM_STATS="$MEM_VALS"
                else
                     # Fallback formatting for old MB
                     MEM_STATS=$(echo "$MEM_VALS" | awk -F'/' '{print $1"/"$2"M"}')
                fi
            fi
            
            if [ -n "$DISK_VALS" ]; then
                 # Truncate to first 4 fields for display (hide MB raw in running table)
                 DISK_STATS=$(echo "$DISK_VALS" | cut -d'/' -f1-4)
            fi
        fi

        # Fetch the last step indicator from the log
        LAST_STEP=$(echo "$LOG_CONTENT" | grep -E "\[Step [0-9]+\]" | tail -n 1)
        
        if [ -z "$LAST_STEP" ]; then
            LAST_STEP="Initializing / Downloading inputs..."
        else
            # Clean up the date prefix for a cleaner display
            LAST_STEP=$(echo "$LAST_STEP" | sed 's/\[.*\] //')
        fi
        
        printf "%-25s | %-20s | %-10s | %-20s | %-22s | %-22s | %-10s | %s\n" "$IMAGE_ID" "$START_TIME_STR" "$DURATION_STR" "$CPU_STATS" "$MEM_STATS" "$DISK_STATS" "$INPUT_STR" "$LAST_STEP"
    done
fi

echo ""
echo "-------------------------------------------------------------------------------------------------------------------"
echo "                                        COMPLETED JOBS                                              "
echo "-------------------------------------------------------------------------------------------------------------------"
printf "%-25s | %-20s | %-10s | %-18s | %-18s | %-22s | %s\n" "IMAGE ID" "START TIME" "DURATION" "CPU (AVG/LD/N)" "MEM (MAX%/TOT)" "DISK (USED/TOT/IN)" "STATUS"
echo "-------------------------------------------------------------------------------------------------------------------"
if [ -z "$COMPLETED_LOGS" ]; then
    echo "No completed jobs detected."
else
    echo "$COMPLETED_LOGS" | while read -r SIZE DATE PATH_URI; do
        FILENAME=$(basename "$PATH_URI")
        
        # Extract Image ID (everything before _JobAll_)
        IMAGE_ID=$(echo "$FILENAME" | sed -E 's/_JobAll_[0-9]{8}_[0-9]{6}\.txt//')
        
        # Read content
        LOG_CONTENT=$(gcloud storage cat "$PATH_URI" 2>/dev/null)
        
        # Start Time
        START_LINE=$(echo "$LOG_CONTENT" | grep -m 1 "^\[")
        START_TIME_STR="Unknown"
        DURATION_STR="--"
        
        if [ -n "$START_LINE" ]; then
            TS_STR=$(echo "$START_LINE" | sed -n 's/^\[\(.*\)\] .*/\1/p')
            START_SEC=$(date -d "$TS_STR" +%s 2>/dev/null)
            if [ -n "$START_SEC" ]; then
                START_TIME_STR=$(date -d "@$START_SEC" "+%Y-%m-%d %H:%M:%S")
                # End Time from filename
                END_TS_STR=$(echo "$FILENAME" | grep -oE '[0-9]{8}_[0-9]{6}' | tail -n 1)
                if [ -n "$END_TS_STR" ]; then
                    FMT_END_STR="${END_TS_STR:0:4}-${END_TS_STR:4:2}-${END_TS_STR:6:2} ${END_TS_STR:9:2}:${END_TS_STR:11:2}:${END_TS_STR:13:2} UTC"
                    END_SEC=$(date -d "$FMT_END_STR" +%s 2>/dev/null)
                    if [ -n "$END_SEC" ]; then
                        DURATION_SEC=$((END_SEC - START_SEC))
                        DURATION_STR=$(format_duration $DURATION_SEC)
                    fi
                fi
            fi
        fi

        # Extract Final Stats
        STATS_LINE=$(echo "$LOG_CONTENT" | grep "\[STATS\]" | tail -n 1)
        CPU_STATS="--"
        MEM_STATS="--"
        DISK_STATS="--"
        
        # Extract Input Size if available
        INPUT_MB=$(echo "$LOG_CONTENT" | grep "Input_Size_MB:" | tail -n 1 | sed 's/.*Input_Size_MB: //' | awk '{print $1}')

        if [ -n "$STATS_LINE" ]; then
            # For completed jobs, show Avg CPU and Max Mem/Disk
            # CPU_Load: Cur/Avg
            CPU_AVG=$(echo "$STATS_LINE" | grep -o "CPU_Load: [0-9./]*" | cut -d' ' -f2 | cut -d'/' -f2)
            N_CPUS=$(echo "$STATS_LINE" | grep -o "CPU_Load: [0-9./]*" | cut -d' ' -f2 | cut -d'/' -f3)
            [ -z "$N_CPUS" ] && N_CPUS=4
            if [ -n "$CPU_AVG" ]; then
                LOAD_FACTOR=$(awk "BEGIN {printf \"%.1f\", $CPU_AVG / $N_CPUS}")
                CPU_STATS="${CPU_AVG}/${LOAD_FACTOR}/${N_CPUS}C"
            fi

            # Mem_Stats: CUR%/MAX%/AV_GB/TOT_GB
            MEM_VALS=$(echo "$STATS_LINE" | grep -o "Mem_Stats: [0-9A-Za-z%./]*" | cut -d' ' -f2)
            if [ -n "$MEM_VALS" ]; then
                MEM_MAX_PCT=$(echo "$MEM_VALS" | cut -d'/' -f2)
                MEM_TOT=$(echo "$MEM_VALS" | cut -d'/' -f4)
                MEM_STATS="${MEM_MAX_PCT}/${MEM_TOT}"
            fi

            # Disk_Stats: CUR%/MAX%/AV_GB/TOT_GB[/MAX_USED_MB]
            DISK_VALS=$(echo "$STATS_LINE" | grep -o "Disk_Stats: [0-9A-Za-z%./]*" | cut -d' ' -f2)
            if [ -n "$DISK_VALS" ]; then
                DISK_MAX_PCT=$(echo "$DISK_VALS" | cut -d'/' -f2)
                DISK_TOT=$(echo "$DISK_VALS" | cut -d'/' -f4)
                DISK_MAX_MB=$(echo "$DISK_VALS" | cut -d'/' -f5)
                
                # Calculate absolute used GB for easier comparison
                if [[ "$DISK_MAX_MB" =~ ^[0-9]+M$ ]]; then
                     # Use precise MB if available
                     MB_NUM=${DISK_MAX_MB%M}
                     USED_GB=$(awk "BEGIN {printf \"%.0f\", $MB_NUM / 1024}")
                     
                     if [ -n "$INPUT_MB" ] && [ "$INPUT_MB" -gt 0 ]; then
                         INPUT_GB=$(awk "BEGIN {printf \"%.1f\", $INPUT_MB / 1024}")
                         DISK_STATS="${USED_GB}G/${DISK_TOT} (In:${INPUT_GB}G)"
                     else
                         DISK_STATS="${USED_GB}G/${DISK_TOT} (${DISK_MAX_PCT})"
                     fi
                else
                     # Fallback to percentage based calc
                     PCT_NUM=${DISK_MAX_PCT%\%}
                     TOT_NUM=${DISK_TOT%G}
                     if [[ "$PCT_NUM" =~ ^[0-9]+$ ]] && [[ "$TOT_NUM" =~ ^[0-9]+$ ]]; then
                         USED_GB=$(awk "BEGIN {printf \"%.0f\", $TOT_NUM * $PCT_NUM / 100}")
                         
                         if [ -n "$INPUT_MB" ] && [ "$INPUT_MB" -gt 0 ]; then
                             INPUT_GB=$(awk "BEGIN {printf \"%.1f\", $INPUT_MB / 1024}")
                             DISK_STATS="${USED_GB}G/${DISK_TOT} (In:${INPUT_GB}G)"
                         else
                             DISK_STATS="${USED_GB}G/${DISK_TOT} (${DISK_MAX_PCT})"
                         fi
                     else
                         DISK_STATS="${DISK_MAX_PCT}/${DISK_TOT}"
                     fi
                fi
            fi
        fi

        # Status
        TAIL=$(echo "$LOG_CONTENT" | tail -n 40)
        
        if echo "$TAIL" | grep -q "Pipeline Complete."; then
            STATUS="SUCCEEDED"
            COLOR="\033[0;32m" # Green
        else
            # Check exit code if available
            EXIT_CODE=$(echo "$TAIL" | grep -o "exit code [0-9]*" | head -n 1)
            if [ -n "$EXIT_CODE" ]; then
                STATUS="FAILED ($EXIT_CODE)"
            else
                STATUS="FAILED (Timeout / Killed)"
            fi
            COLOR="\033[0;31m" # Red
        fi
        RESET="\033[0m"
        
        # Print with colors
        printf "%-25s | %-20s | %-10s | %-18s | %-18s | %-22s | ${COLOR}%s${RESET}\n" "$IMAGE_ID" "$START_TIME_STR" "$DURATION_STR" "$CPU_STATS" "$MEM_STATS" "$DISK_STATS" "$STATUS"
    done
fi

echo ""
echo "=========================================================="
echo "To view active Batch VMs: gcloud compute instances list"
echo "To view Workflow status : gcloud workflows executions list vhr-pipeline-orchestrator --location us-central1"
echo "=========================================================="

# Cleanup
rm /tmp/vhr_logs_raw.txt /tmp/vhr_logs.txt