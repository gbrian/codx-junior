#!/bin/bash

LOG_FILE="/var/log/docker_culprit_matches.log"

echo "[+] Starting background monitor for port 2375 outbound connections..."
echo "[+] Output will be written to console and $LOG_FILE"
echo "--------------------------------------------------------"

# Keep track of records we have already processed
declare -A PROCESSED_IDS

while true; do
    # Search audit logs for our key, filtered by SYSCALL
    # We use 'tail' to read the results line-by-line safely
    ausearch -k docker_culprit -m SYSCALL -i 2>/dev/null | grep -E "syscall=connect" | while read -r line; do
        
        # Extract the unique audit event ID (e.g., audit(172380123.123:99))
        EVENT_ID=$(echo "$line" | grep -o 'audit([^)]*)')
        
        # Skip if we already logged this specific event ID
        if [[ -n "$EVENT_ID" && -n "${PROCESSED_IDS[$EVENT_ID]}" ]]; then
            continue
        fi
        
        # Mark as processed
        if [[ -n "$EVENT_ID" ]]; then
            PROCESSED_IDS[$EVENT_ID]=1
        fi

        # Parse critical details for high-density logging
        EXE_PATH=$(echo "$line" | grep -oE "exe=[^ ]+" | cut -d'=' -f2)
        PID=$(echo "$line" | grep -oE "pid=[^ ]+" | cut -d'=' -f2)
        PPID=$(echo "$line" | grep -oE "ppid=[^ ]+" | cut -d'=' -f2)
        COMM=$(echo "$line" | grep -oE "comm=[^ ]+" | cut -d'=' -f2)
        TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

        # Format the output block
        OUTPUT="=== MATCH DETECTED AT $TIMESTAMP ===\n"
        OUTPUT+="COMMAND   : $COMM\n"
        OUTPUT+="PID       : $PID (Parent PID: $PPID)\n"
        OUTPUT+="BINARY    : $EXE_PATH\n"
        OUTPUT+="RAW EVENT : $line\n"
        OUTPUT+="--------------------------------------------------------"

        # Print to console and append to log file
        echo -e "$OUTPUT"
        echo -e "$OUTPUT" >> "$LOG_FILE"
    done
    
    # Sleep 2 seconds before checking logs again to save CPU cycles
    sleep 2
done
