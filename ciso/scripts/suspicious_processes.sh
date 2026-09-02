#!/bin/bash

# Ensure the script is run as root to access /proc and lsof details
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo)."
  exit 1
fi

REPORT_FILE="incident_report_$(date +%F_%H%M%S).txt"

{
  echo "=================================================================="
  echo "                  INCIDENT FORENSIC REPORT                        "
  echo "                  Generated: $(date)"
  echo "=================================================================="
  echo ""

  echo "--- [1] TARGET PROCESSES DETECTED ---"
  # Capture suspicious PIDs while explicitly ignoring legitimate sysbox processes
  SUSPICIOUS_PIDS=$(ps aux | grep -E 'sleep|masscan|apk' | grep -v 'grep' | grep -v 'sysbox' | awk '{print $2}')

  if [ -z "$SUSPICIOUS_PIDS" ]; then
    echo "No suspicious PIDs found matching criteria (excluding sysbox)."
    echo "=================================================================="
  fi

  ps aux | grep -E 'sleep|masscan|apk' | grep -v 'grep' | grep -v 'sysbox'
  echo ""

  # Loop through each detected PID for deeper analysis
  for pid in $SUSPICIOUS_PIDS; do
    echo "=================================================================="
    echo " ANALYZING PID: $pid"
    echo "=================================================================="
    
    # 1. Verify if PID still exists
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "Process $pid has terminated since the initial check."
      continue
    fi

    # 2. Command Line & Executable Path
    echo "-> Exact Command Line:"
    cat /proc/"$pid"/cmdline 2>/dev/null | tr '\0' ' '
    echo -e "\n"

    echo "-> Executable Link Path:"
    ls -l /proc/"$pid"/exe 2>/dev/null
    echo ""

    # 3. Parent Process Tracking
    ppid=$(ps -o ppid= -p "$pid" | tr -d ' ')
    echo "-> Parent PID (PPID): $ppid"
    if [ -n "$ppid" ] && [ "$ppid" -gt 0 ]; then
      echo "-> Parent Process Details:"
      ps -fp "$ppid" 2>/dev/null
    else
      echo "-> Parent process could not be determined or is init/systemd."
    fi
    echo ""

    # 4. Working Directory
    echo "-> Working Directory (CWD):"
    ls -l /proc/"$pid"/cwd 2>/dev/null
    echo ""

    # 5. Environment Variables (Cleansed for readability)
    echo "-> Process Environment Variables:"
    cat /proc/"$pid"/environ 2>/dev/null | tr '\0' '\n' | grep -E 'PATH|HOME|USER|CONTAINER|DOCKER|KUBERNETES|PWD|SHELL|HTTP|IP|URL' || echo "No standard environmental markers found."
    echo ""

    # 6. Network Connections
    echo "-> Active Network Connections & Open Sockets:"
    if command -v lsof &> /dev/null; then
      lsof -i -P -n -p "$pid" 2>/dev/null || echo "No active network sockets found for this PID."
    else
      netstat -nap 2>/dev/null | grep "$pid" || ss -nap 2>/dev/null | grep "$pid" || echo "lsof missing; alternative network checks found nothing."
    fi
    echo ""
  done

  echo "=================================================================="
  echo "                  END OF FORENSIC REPORT                          "
  echo "=================================================================="

} | tee "$REPORT_FILE"

echo -e "\n[+] Analysis complete. Full report saved to: \033[1;32m$REPORT_FILE\033[0m"