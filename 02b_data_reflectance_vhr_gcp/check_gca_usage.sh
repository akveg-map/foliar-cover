#!/bin/bash
# copied to /usr/local/bin

# Default values
PROJECT_ID="gemini-trial-479902"
SINCE="24 hours ago"
USER_ONLY=false
TARGET_USER=""

# Display Help
function show_help() {
    echo "Usage: ./check_gca_usage.sh [OPTIONS]"
    echo "Check how many API requests have been sent to the Gemini Code Assist backend."
    echo ""
    echo "Options:"
    echo "  -p, --project ID      Specify the Google Cloud Project ID (default: $PROJECT_ID)"
    echo "  -s, --since TIME      Specify the start time (default: '24 hours ago')"
    echo "                        Accepts standard Linux date strings like '6 hours ago', 'today at 08:00', etc."
    echo "  -o, --user-only       Only show per-user usage from Audit Logs (skip project-wide metrics)"
    echo "  -u, --user EMAIL      Filter audit logs for a specific user (implicitly enables user-only mode)"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./check_gca_usage.sh                            # Check project-wide and all users"
    echo "  ./check_gca_usage.sh -o                         # Skip project-wide, show all users"
    echo "  ./check_gca_usage.sh -u mmacander@abrinc.com    # Show usage only for this specific user"
}

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -p|--project) PROJECT_ID="$2"; shift ;;
        -s|--since) SINCE="$2"; shift ;;
        -o|--user-only) USER_ONLY=true ;;
        -u|--user) TARGET_USER="$2"; USER_ONLY=true; shift ;;
        -h|--help) show_help; exit 0 ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo "Fetching GCA request logs for project: $PROJECT_ID"
echo "Timeframe: Since $SINCE"
if [ -n "$TARGET_USER" ]; then
    echo "Filtering for user: $TARGET_USER"
fi

# Ensure gcloud is authenticated and token is available
TOKEN=$(gcloud auth print-access-token 2>/dev/null)
if [ -z "$TOKEN" ]; then
    echo "Error: Could not retrieve gcloud access token. Please run 'gcloud auth login' first."
    exit 1
fi

# Calculate RFC3339 timestamps in UTC (Required by Google Cloud Monitoring API)
# Uses GNU date which is standard on your Linux environment.
START_TIME=$(date -u -d "$SINCE" +%FT%TZ 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "Error: Invalid time format provided to --since."
    exit 1
fi
END_TIME=$(date -u +%FT%TZ)

# ==========================================
# PROJECT-WIDE METRICS (Skipped if USER_ONLY=true)
# ==========================================
if [ "$USER_ONLY" = false ]; then
    # Run the curl command to fetch TimeSeries data for API request counts
    # -s hides the curl progress bar
    # -G forces a GET request to allow URL encoding of the complex filter strings
    RESPONSE=$(curl -s -G "https://monitoring.googleapis.com/v3/projects/$PROJECT_ID/timeSeries" \
      -H "Authorization: Bearer $TOKEN" \
      --data-urlencode "filter=metric.type=\"serviceruntime.googleapis.com/api/request_count\" AND resource.labels.service=\"cloudaicompanion.googleapis.com\"" \
      --data-urlencode "interval.startTime=$START_TIME" \
      --data-urlencode "interval.endTime=$END_TIME")

    # Parse and format API Request Counts
    echo "$RESPONSE" | jq -r '.timeSeries[]? | "\(.resource.labels.method) \(.points | map(.value.int64Value | tonumber) | add)"' | awk '
    {
        method=$1
        sub(/^.*\./, "", method)
        arr[method]+=$2
        total+=$2
    }
    END {
        print "\n============================================="
        print "GCA API Requests (Project-Wide)"
        print "============================================="
        for (m in arr) {
            printf "%-30s %10d\n", m, arr[m]
        }
        print "---------------------------------------------"
        printf "%-30s %10d\n", "Total Requests:", total+0
        print "============================================="
    }'

    # Fetch Quota specific metrics to see breakdown
    QUOTA_RESPONSE=$(curl -s -G "https://monitoring.googleapis.com/v3/projects/$PROJECT_ID/timeSeries" \
      -H "Authorization: Bearer $TOKEN" \
      --data-urlencode "filter=metric.type=\"serviceruntime.googleapis.com/quota/rate/net_usage\" AND resource.labels.service=\"cloudaicompanion.googleapis.com\"" \
      --data-urlencode "interval.startTime=$START_TIME" \
      --data-urlencode "interval.endTime=$END_TIME")

    # Parse and format Quota Usage
    echo "$QUOTA_RESPONSE" | jq -r '.timeSeries[]? | "\(.metric.labels.quota_metric) \(.points | map(.value.int64Value | tonumber) | add)"' | awk '
    {
        arr[$1]+=$2
    }
    END {
        if (length(arr) > 0) {
            print "\n============================================="
            print "Quota Usage (Proxy for per-user limits)"
            print "============================================="
            for (q in arr) {
                printf "%-30s %10d\n", q, arr[q]
            }
            print "============================================="
        }
    }'
fi

# ==========================================
# PER-USER AUDIT LOGS
# ==========================================
echo ""
echo "Fetching per-user audit logs (this may take a few seconds)..."

# Build the filter
LOG_FILTER="protoPayload.serviceName=\"cloudaicompanion.googleapis.com\" AND timestamp>=\"$START_TIME\" AND timestamp<=\"$END_TIME\""
if [ -n "$TARGET_USER" ]; then
    LOG_FILTER="$LOG_FILTER AND protoPayload.authenticationInfo.principalEmail=\"$TARGET_USER\""
fi

# Note: Removed 2>/dev/null so any gcloud permission/syntax errors will print to your terminal!
if ! gcloud logging read "$LOG_FILTER" --project="$PROJECT_ID" --format=json > /tmp/gca_audit_logs_$$.json 2>/tmp/gca_err_$$.txt; then
    echo "Error: Failed to fetch audit logs."
    cat /tmp/gca_err_$$.txt
    echo "Tip: Ensure you have the 'Private Logs Viewer' (roles/logging.privateLogViewer) role."
    rm -f /tmp/gca_audit_logs_$$.json /tmp/gca_err_$$.txt
    exit 1
fi

if [ -s /tmp/gca_audit_logs_$$.json ] && [ "$(cat /tmp/gca_audit_logs_$$.json)" != "[]" ]; then
    cat /tmp/gca_audit_logs_$$.json | jq -r '.[] | "\(.protoPayload.authenticationInfo.principalEmail) \(.protoPayload.methodName)"' | awk '
    {
        user=$1
        method=$2
        sub(/^.*\./, "", method)
        if (user == "null" || user == "") user = "unknown"
        if (method == "null" || method == "") method = "unknown"
        
        arr[user SUBSEP method]++
        user_total[user]++
        total++

        # Estimate quota hits (exclude administrative/background methods)
        if (method != "QueryEffectiveSetting") {
            user_quota_total[user]++
            quota_total++
        }
    }
    END {
        print "\n============================================="
        print "Per-User Usage (From Audit Logs)"
        print "============================================="
        for (u in user_total) {
            q_total = user_quota_total[u] ? user_quota_total[u] : 0
            printf "User: %s\n", u
            printf "  %-28s %10d\n", "Est. Quota Hits:", q_total
            printf "  %-28s %10d\n", "Total Raw Logs:", user_total[u]
            print  "  Method Breakdown:"
            for (comb in arr) {
                split(comb, idx, SUBSEP)
                if (idx[1] == u) {
                    printf "    %-26s %10d\n", idx[2], arr[comb]
                }
            }
            print "---------------------------------------------"
        }
        printf "%-30s %10d\n", "GRAND TOTAL (Quota Hits):", quota_total+0
        printf "%-30s %10d\n", "GRAND TOTAL (Raw Logs):", total
        print "============================================="
    }'
else
    echo ""
    echo "============================================="
    echo "Per-User Usage (From Audit Logs)"
    echo "============================================="
    echo "No data access audit logs found for this timeframe."
    echo "Note: Audit logging was just enabled and only tracks new requests."
    echo "============================================="
fi

rm -f /tmp/gca_audit_logs_$$.json /tmp/gca_err_$$.txt