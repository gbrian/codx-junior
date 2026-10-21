#!/bin/bash

# Exit on error
set -e

# Define base paths
BASE_DIR="$HOME/.codx-junior"
HISTORY_DIR="$BASE_DIR/history"
SETTINGS_DIR="$BASE_DIR/settings"

# Print usage helper
usage() {
    echo "Usage:"
    echo "  $0 list <settings_file.json>          - List last 5 backups with file sizes"
    echo "  $0 modified <days>                    - Scan files modified in the last X days (with seconds)"
    echo "  $0 rollback <YYYY-MM-DDTHH:mm:ss>     - Rollback all files to an exact ISO timestamp"
    echo "  $0 rollback-before <YYYY-MM-DD>       - Recover all files changed on a bad day to their previous backup"
    echo ""
    echo "Examples:"
    echo "  $0 list ai_models.json"
    echo "  $0 modified 3"
    echo "  $0 rollback-before 2026-10-13"
    exit 1
}

# Helper function to get cross-platform modification time with seconds
get_mod_time() {
    local target_file="$1"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$target_file"
    else
        stat -c "%y" "$target_file" | cut -d'.' -f1
    fi
}

# Ensure minimum required arguments
if [ -z "$1" ] || [ -z "$2" ]; then
    usage
fi

COMMAND="$1"

# ==========================================
# COMMAND: DETECT MODIFIED FILES (With Seconds)
# ==========================================
if [ "$COMMAND" = "modified" ]; then
    DAYS="$2"
    if ! [[ "$DAYS" =~ ^[0-9]+$ ]]; then
        echo "❌ Error: Days parameter must be a valid number."
        exit 1
    fi

    echo "Scanning active configuration files modified in the last $DAYS days..."
    echo "----------------------------------------------------------------------"
    printf "%-25s %-12s %-20s\n" "Active Settings File" "File Size" "Last Modified Time"
    echo "----------------------------------------------------------------------"

    found_any=false
    if [ -d "$SETTINGS_DIR" ]; then
        while read -r setting_file; do
            [ -f "$setting_file" ] || continue
            found_any=true
            
            file_name=$(basename "$setting_file")
            file_size=$(du -b "$setting_file" 2>/dev/null | cut -f1 || du -ch "$setting_file" | tail -n1 | cut -f1) # Handles exact byte fallback
            mod_time=$(get_mod_time "$setting_file")
            
            printf "%-25s %-12s %-20s\n" "$file_name" "$file_size bytes" "$mod_time"
        done < <(find "$SETTINGS_DIR" -type f -name "*.json" -mtime -"$DAYS" 2>/dev/null)
    fi

    [ "$found_any" = false ] && echo "No settings files modified within the last $DAYS days."

# ==========================================
# COMMAND: ROLLBACK BEFORE A CORRUPT DATE
# ==========================================
elif [ "$COMMAND" = "rollback-before" ]; then
    CORRUPT_ISO="$2"
    # Extract clean target stamp prefix (e.g., 2026-10-13 -> 20261013)
    BAD_DATE_PREFIX=$(echo "$CORRUPT_ISO" | tr -d ':-' | tr 'T' '_')
    
    echo "Searching for active files modified on/during: $CORRUPT_ISO"
    echo "Targeting individual restoration to their last version before this event..."
    echo "----------------------------------------------------------------------"

    for setting_file in "$SETTINGS_DIR"/*.json; do
        [ -f "$setting_file" ] || continue
        
        file_name=$(basename "$setting_file")
        folder_name="${file_name%.json}"
        target_history_dir="$HISTORY_DIR/$folder_name"
        
        # Check if the active file's current modification date matches the bad day
        mod_time=$(get_mod_time "$setting_file")
        
        if [[ "$mod_time" == *"$CORRUPT_ISO"* ]]; then
            echo "⚠️ Match found: $file_name was modified during the target corrupt frame ($mod_time)"
            
            # Find all backups for this file, filtering out files from the bad day/time frame, and grab the newest remaining one
            # It sorts files chronologically by filename structure (reverse)
            last_good_backup=$(ls -1 "$target_history_dir"/*.json 2>/dev/null | grep -v "${BAD_DATE_PREFIX}" | sort -r | head -n 1 || true)
            
            if [ -n "$last_good_backup" ] && [ -f "$last_good_backup" ]; then
                good_size=$(du -sh "$last_good_backup" | cut -f1)
                echo "    -> Found last known clean backup: $(basename "$last_good_backup") ($good_size)"
                echo "    -> Overwriting corrupted active file..."
                cp "$last_good_backup" "$setting_file"
                echo "    ✅ Fixed $file_name"
            else
                echo "    ❌ Error: Could not locate a valid historic backup prior to $CORRUPT_ISO for $file_name"
            fi
        fi
    done
    echo "----------------------------------------------------------------------"
    echo "🎯 Disaster recovery execution finished."

# ==========================================
# COMMAND: LIST BACKUPS
# ==========================================
elif [ "$COMMAND" = "list" ]; then
    FILE_NAME="$2"
    FOLDER_NAME="${FILE_NAME%.json}"
    TARGET_FOLDER="$HISTORY_DIR/$FOLDER_NAME"

    if [ ! -d "$TARGET_FOLDER" ]; then
        echo "❌ Error: No history directory found for '$FILE_NAME' at $TARGET_FOLDER"
        exit 1
    fi

    echo "Listing the last 5 backups for '$FILE_NAME' (with precise seconds):"
    echo "----------------------------------------------------------------------"
    printf "%-25s %-12s %-15s\n" "Backup Timestamp" "File Size" "Status/Note"
    echo "----------------------------------------------------------------------"

    ls -1 "$TARGET_FOLDER"/*.json 2>/dev/null | sort -r | head -n 5 | while read -r backup_file; do
        if [ -f "$backup_file" ]; then
            raw_name=$(basename "$backup_file")
            clean_ts="${raw_name%.json}"
            
            if [[ "$clean_ts" =~ ^([0-9]{4})([0-9]{2})([0-9]{2})_([0-9]{2})([0-9]{2})([0-9]{2}) ]]; then
                display_time="${BASH_REMATCH[1]}-${BASH_REMATCH[2]}-${BASH_REMATCH[3]} ${BASH_REMATCH[4]}:${BASH_REMATCH[5]}:${BASH_REMATCH[6]}"
            else
                display_time="$clean_ts"
            fi
            
            file_size=$(du -sh "$backup_file" | cut -f1)
            note="OK"
            if [ ! -s "$backup_file" ]; then note="⚠️ CORRUPTED (0B)"; fi
            
            printf "%-25s %-12s %-15s\n" "$display_time" "$file_size" "$note"
        fi
    done

# ==========================================
# COMMAND: EXACT ROLLBACK
# ==========================================
elif [ "$COMMAND" = "rollback" ]; then
    INPUT_ISO="$2"
    CLEANED_TS=$(echo "$INPUT_ISO" | tr -d ':-' | tr 'T' '_')
    TARGET_DATE="${CLEANED_TS:0:8}"
    TARGET_TIME="${CLEANED_TS:9:6}"

    for history_folder in "$HISTORY_DIR"/*/; do
        [ -d "$history_folder" ] || continue
        folder_name=$(basename "$history_folder")
        match_pattern="${TARGET_DATE}_${TARGET_TIME}*.json"
        
        backup_file=$(ls -1 "$history_folder"$match_pattern 2>/dev/null | tail -n 1)

        if [ -n "$backup_file" ] && [ -f "$backup_file" ]; then
            target_file="$SETTINGS_DIR/${folder_name}.json"
            echo "Restoring: $(basename "$backup_file") -> $target_file"
            mkdir -p "$SETTINGS_DIR"
            cp "$backup_file" "$target_file"
        fi
    done
    echo "✅ Exact rollback complete!"
else
    usage
fi