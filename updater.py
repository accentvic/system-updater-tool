#!/bin/bash
LOG_FILE="$HOME/app-update-log.txt"

echo "=== APPLICATION UPDATE: $(date) ===" | tee -a $LOG_FILE

# Update Snap applications
if command -v snap &> /dev/null; then
    echo "--- Checking Snap Applications ---" | tee -a $LOG_FILE
    UPDATABLE=$(snap refresh --list 2>/dev/null | wc -l)
    
    if [ $UPDATABLE -gt 1 ]; then
        echo "Found $((UPDATABLE-1)) apps to update:" | tee -a $LOG_FILE
        snap refresh --list | tee -a $LOG_FILE
        echo "Updating Snap applications..." | tee -a $LOG_FILE
        sudo snap refresh | tee -a $LOG_FILE
        echo "✅ Snap apps updated successfully" | tee -a $LOG_FILE
    else
        echo "✅ All Snap apps are up to date" | tee -a $LOG_FILE
    fi
fi

# System update check (integrated)
echo "=== Running System Update Check ===" | tee -a $LOG_FILE
python3 /home/capalot/system-updater-final/src/updater.py --auto >> $LOG_FILE 2>&1

echo "=== UPDATE COMPLETED: $(date) ===" | tee -a $LOG_FILE

# Desktop notification
if command -v notify-send &> /dev/null; then
    notify-send "Update Cycle Complete" "App updates and system check finished"
fi
