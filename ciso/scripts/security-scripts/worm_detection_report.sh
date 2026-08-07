#!/bin/bash
#
# worm_detection_report.sh
#
# Generates a point-in-time forensic snapshot of a Linux host to help
# identify compromised processes / worm-like scanning behavior.
#
# Usage:
#   sudo ./worm_detection_report.sh [output_file]
#
# If no output file is given, writes to worm_report_<hostname>_<timestamp>.txt
#
# NOTE: This script only *collects and displays* information. It does not
# kill processes, modify firewall rules, or delete anything. Review the
# report yourself (or with someone experienced) before taking action.

set -uo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "This script should be run as root (sudo) for accurate results." >&2
    echo "Continuing anyway, but some sections will be incomplete." >&2
fi

HOSTNAME_SAFE=$(hostname 2>/dev/null || echo "unknown-host")
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTFILE="${1:-worm_report_${HOSTNAME_SAFE}_${TIMESTAMP}.txt}"

# --- helpers ---------------------------------------------------------------

section() {
    {
        echo ""
        echo "=============================================================="
        echo "  $1"
        echo "=============================================================="
    } >> "$OUTFILE"
}

run() {
    # run <description> <command...>
    local desc="$1"; shift
    {
        echo ""
        echo "--- $desc ---"
        if command -v "$1" >/dev/null 2>&1 || [[ "$1" == "cat" || "$1" == "find" || "$1" == "ls" ]]; then
            "$@" 2>&1
        else
            echo "[tool not installed: $1]"
        fi
    } >> "$OUTFILE"
}

have() { command -v "$1" >/dev/null 2>&1; }

# --- start report ------------------------------------------------------------

{
echo "############################################################"
echo "# Worm / Compromise Detection Report"
echo "# Host: $HOSTNAME_SAFE"
echo "# Generated: $(date)"
echo "############################################################"
} > "$OUTFILE"

# 1. System overview ----------------------------------------------------------
section "SYSTEM OVERVIEW"
run "Uname" uname -a
run "Uptime" uptime
run "OS release" cat /etc/os-release

# 2. Active network connections ------------------------------------------------
section "ACTIVE NETWORK CONNECTIONS (ss)"
run "Established TCP connections w/ PID" ss -tnp state established
run "All listening sockets w/ PID" ss -tlnp
run "All UDP sockets w/ PID" ss -unp

# 3. Suspicious ports / patterns -----------------------------------------------
section "SUSPICIOUS PORT PATTERNS"
{
    echo ""
    echo "--- Connections to common malicious/scan ports (25,445,135,139,6667,6697,23,2323,4444) ---"
    ss -tnp 2>/dev/null | grep -E ':(25|445|135|139|6667|6697|23|2323|4444|9200|6379)\b' || echo "(none found)"

    echo ""
    echo "--- Connections with unusually high remote port ranges (possible scan/backconnect) ---"
    ss -tnp state established 2>/dev/null | awk '{print $4, $5}' | grep -E ':[4-6][0-9]{4}\b' || echo "(none found)"
} >> "$OUTFILE"

# 4. Process <-> socket cross reference -----------------------------------------
section "LSOF NETWORK CONNECTIONS (non-listening)"
if have lsof; then
    run "lsof -i (established/outbound)" bash -c "lsof -i -P -n 2>/dev/null | grep -v LISTEN"
else
    echo "lsof not installed (sudo apt install lsof)" >> "$OUTFILE"
fi

# 5. conntrack table -------------------------------------------------------------
section "CONNTRACK TABLE"
if have conntrack; then
    run "conntrack -L (non-established / short-lived)" bash -c "conntrack -L 2>/dev/null | grep -v ESTABLISHED | head -100"
else
    echo "conntrack not installed (sudo apt install conntrack)" >> "$OUTFILE"
fi

# 6. Process list with suspicious traits ------------------------------------------
section "PROCESS AUDIT"
run "Full process list" ps auxww

{
    echo ""
    echo "--- Processes with deleted/missing binaries (common rootkit/worm trait) ---"
    for pid in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
        if [[ -L "/proc/$pid/exe" ]]; then
            link=$(readlink "/proc/$pid/exe" 2>/dev/null)
            if [[ "$link" == *"(deleted)"* ]]; then
                echo "PID $pid -> $link"
                echo "   cmdline: $(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null)"
            fi
        fi
    done

    echo ""
    echo "--- Processes running from suspicious/writable dirs (/tmp, /dev/shm, /var/tmp, uploads) ---"
    for pid in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
        if [[ -L "/proc/$pid/exe" ]]; then
            link=$(readlink "/proc/$pid/exe" 2>/dev/null)
            if [[ "$link" =~ ^/(tmp|dev/shm|var/tmp) || "$link" =~ upload ]]; then
                echo "PID $pid -> $link"
                echo "   cmdline: $(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null)"
            fi
        fi
    done

    echo ""
    echo "--- Processes with no matching command on disk (name mismatch / masquerading) ---"
    ps -eo pid,comm,args --no-headers | while read -r pid comm args; do
        exe="/proc/$pid/exe"
        if [[ -L "$exe" ]]; then
            target=$(readlink "$exe" 2>/dev/null)
            base=$(basename "$target" 2>/dev/null)
            if [[ -n "$base" && "$base" != "$comm" && "$target" != *"(deleted)"* ]]; then
                : # comm mismatches are common and often benign (e.g. bash vs -bash); skip noisy output
            fi
        fi
    done
} >> "$OUTFILE"

# 7. Top CPU/network-heavy processes ----------------------------------------------
section "RESOURCE HOGS (possible flood/scan source)"
run "Top CPU consumers" bash -c "ps -eo pid,ppid,user,%cpu,%mem,etime,cmd --sort=-%cpu | head -20"

# 8. Persistence mechanisms -------------------------------------------------------
section "PERSISTENCE CHECKS"
run "Root crontab" crontab -l -u root
run "System crontab" cat /etc/crontab
run "Cron.d entries" bash -c "ls -la /etc/cron.d/ 2>/dev/null; for f in /etc/cron.d/*; do echo \"--\$f--\"; cat \"\$f\" 2>/dev/null; done"
run "Cron.daily/hourly/weekly listing" bash -c "ls -la /etc/cron.daily /etc/cron.hourly /etc/cron.weekly 2>/dev/null"
run "Systemd timers" systemctl list-timers --all
run "Non-standard running services" bash -c "systemctl list-units --type=service --state=running --no-legend | grep -vE 'ssh|cron|systemd|dbus|network|rsyslog|polkit|udev|getty|user@'"
run "Root authorized_keys" cat /root/.ssh/authorized_keys
run "All authorized_keys on system" bash -c "find /home /root -name authorized_keys -exec echo '-- {} --' \; -exec cat {} \; 2>/dev/null"
run "LD_PRELOAD env check" bash -c "echo \"System-wide: \$(cat /etc/ld.so.preload 2>/dev/null || echo none)\"; env | grep -i preload"
run "rc.local / init scripts" cat /etc/rc.local

# 9. Recently modified/created files ----------------------------------------------
section "RECENTLY MODIFIED FILES (last 3 days, executable)"
run "Recently modified executables" bash -c "find / -xdev -mtime -3 -type f -perm -u+x 2>/dev/null | grep -Ev '^/(proc|sys|run)' | head -100"

section "RECENTLY MODIFIED FILES IN COMMON DROP LOCATIONS (last 7 days)"
run "tmp / dev/shm / var/tmp" bash -c "find /tmp /dev/shm /var/tmp -mtime -7 -type f 2>/dev/null | head -100"

# 10. Listening sockets not matching known services --------------------------------
section "LISTENING SOCKETS SUMMARY"
run "All listening TCP/UDP with process" ss -tulnp

# 11. Firewall state ------------------------------------------------------------------
section "FIREWALL STATE"
run "iptables rules" iptables -L -n -v
run "nftables rules" nft list ruleset

# 12. Last logins / auth log tail --------------------------------------------------
section "AUTHENTICATION ACTIVITY"
run "Last logins" last -a
run "Currently logged in" w
run "Failed login attempts (last 50)" bash -c "grep -i 'failed password' /var/log/auth.log 2>/dev/null | tail -50 || journalctl -u sshd --no-pager 2>/dev/null | grep -i fail | tail -50"

# --- summary -----------------------------------------------------------------------
section "REPORT COMPLETE"
{
    echo "Report saved to: $OUTFILE"
    echo ""
    echo "WHAT TO LOOK FOR:"
    echo "  1. Under PROCESS AUDIT: any 'deleted' binaries or processes running from /tmp, /dev/shm"
    echo "  2. Under SUSPICIOUS PORT PATTERNS: connections to 445, 6667, 4444, or many high-numbered ports"
    echo "  3. Under PERSISTENCE CHECKS: unfamiliar cron jobs, unknown SSH keys, unexpected systemd services"
    echo "  4. Cross-reference IPs from ACTIVE NETWORK CONNECTIONS against your known infrastructure"
    echo "  5. RECENTLY MODIFIED FILES: anything you didn't put there yourself"
    echo ""
    echo "This report only collects evidence. It does not confirm compromise or take any action."
} >> "$OUTFILE"

echo "Report generated: $OUTFILE"
echo "Review it with: less \"$OUTFILE\""