#!/bin/bash
#
# outbound_scan_watch.sh (v2)
#
# Live watcher for outbound traffic to suspicious ports. Built for a host that
# should NEVER initiate outbound connections (only serves 80/8080/443 inbound).
#
# v2 adds: --direction {out,in,both} to filter by traffic direction at the
# packet level (not just port), so inbound internet-scan noise (the bulk of
# real-world traffic hitting any public server) doesn't drown out genuine
# outbound activity from a compromised process. Default is "out" since that's
# what you need to catch ASAP - a local process attacking other hosts.
#
# Also adds: immediate PID correlation by matching the outbound packet's local
# (source) port against `ss` - much faster than grepping by destination IP,
# since the local port is unique to the process/socket on THIS host.
#
# Detects both:
#   1. Normal connect()-based traffic (visible in ss/lsof)
#   2. Raw-socket scanners (masscan/zmap-style) that reuse one source port
#      across many destinations and DON'T show up in ss/lsof at all
#
# Usage:
#   sudo ./outbound_scan_watch.sh                        # outbound only (default), default port list
#   sudo ./outbound_scan_watch.sh --direction out         # explicit, same as default
#   sudo ./outbound_scan_watch.sh --direction in          # inbound only (the old noisy behavior)
#   sudo ./outbound_scan_watch.sh --direction both        # both directions
#   sudo ./outbound_scan_watch.sh --all                   # ANY outbound SYN except allowed ports
#   sudo ./outbound_scan_watch.sh --ports 6379,2375,9200
#   sudo ./outbound_scan_watch.sh --iface eth0 --logdir /var/log/scanwatch
#
# Stop with Ctrl+C. Writes:
#   <logdir>/scan_events_<timestamp>.log   - human readable event log
#   <logdir>/capture_<timestamp>.pcap      - full packet capture for later analysis

set -uo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Must run as root (sudo) - needed for tcpdump/ss/lsof visibility." >&2
    exit 1
fi

# --- defaults ----------------------------------------------------------------
IFACE="any"
LOGDIR="./scanwatch_$(date +%Y%m%d_%H%M%S)"
ALLOWED_PORTS="80,443,8080"     # ports this box is expected to use outbound (rare) - never flagged
WATCH_MODE="list"               # "list" = only watch SUSPICIOUS_PORTS, "all" = watch everything except ALLOWED_PORTS
DIRECTION="out"                 # out | in | both  -- THIS IS THE KEY NEW SETTING
SUSPICIOUS_PORTS="2375,2376,6379,6380,8545,8546,8547,9200,9300,27017,5984,2379,8091,3306,5432,23,2323,445,3389,5900,6667,6697,4444,4445,8081,8888"

# --- parse args ----------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --iface) IFACE="$2"; shift 2 ;;
        --logdir) LOGDIR="$2"; shift 2 ;;
        --ports) SUSPICIOUS_PORTS="$2"; WATCH_MODE="list"; shift 2 ;;
        --allowed) ALLOWED_PORTS="$2"; shift 2 ;;
        --all) WATCH_MODE="all"; shift ;;
        --direction) DIRECTION="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: sudo $0 [--direction out|in|both] [--iface IFACE] [--logdir DIR] [--ports p1,p2,...] [--allowed p1,p2,...] [--all]"
            exit 0
            ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

if [[ "$DIRECTION" != "out" && "$DIRECTION" != "in" && "$DIRECTION" != "both" ]]; then
    echo "Invalid --direction: $DIRECTION (must be out, in, or both)" >&2
    exit 1
fi

if ! command -v tcpdump >/dev/null 2>&1; then
    echo "tcpdump not found. Install with: sudo apt install tcpdump" >&2
    exit 1
fi

mkdir -p "$LOGDIR"
TS=$(date +%Y%m%d_%H%M%S)
EVENTLOG="$LOGDIR/scan_events_${TS}.log"
PCAPFILE="$LOGDIR/capture_${TS}.pcap"

# --- detect local IPs so we can filter by direction reliably ------------------------
# This works regardless of tcpdump version/interface (-Q direction flag isn't
# available everywhere), by filtering on which side of the packet is "us".
mapfile -t LOCAL_IPS < <(ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1)
if [[ ${#LOCAL_IPS[@]} -eq 0 ]]; then
    echo "WARNING: could not auto-detect local IPs; direction filtering will be less precise." >&2
fi

HOST_CLAUSE=""
for ip in "${LOCAL_IPS[@]}"; do
    if [[ -z "$HOST_CLAUSE" ]]; then
        HOST_CLAUSE="host $ip"
    else
        HOST_CLAUSE+=" or host $ip"
    fi
done

echo "Scan watcher started $(date)" | tee "$EVENTLOG"
echo "Interface: $IFACE" | tee -a "$EVENTLOG"
echo "Direction: $DIRECTION" | tee -a "$EVENTLOG"
echo "Local IPs detected: ${LOCAL_IPS[*]:-none}" | tee -a "$EVENTLOG"
echo "Mode: $WATCH_MODE" | tee -a "$EVENTLOG"
if [[ "$WATCH_MODE" == "list" ]]; then
    echo "Watching ports: $SUSPICIOUS_PORTS" | tee -a "$EVENTLOG"
else
    echo "Watching ALL SYNs except allowed ports: $ALLOWED_PORTS" | tee -a "$EVENTLOG"
fi
echo "Full packet capture: $PCAPFILE" | tee -a "$EVENTLOG"
echo "Event log: $EVENTLOG" | tee -a "$EVENTLOG"
echo "---" | tee -a "$EVENTLOG"

# --- build the BPF filter -------------------------------------------------------
IFS=',' read -ra ALLOWED_ARR <<< "$ALLOWED_PORTS"
NOT_ALLOWED_CLAUSE=""
for p in "${ALLOWED_ARR[@]}"; do
    NOT_ALLOWED_CLAUSE+=" and dst port not $p"
done

if [[ "$WATCH_MODE" == "list" ]]; then
    IFS=',' read -ra WATCH_ARR <<< "$SUSPICIOUS_PORTS"
    PORT_CLAUSE=""
    for p in "${WATCH_ARR[@]}"; do
        if [[ -z "$PORT_CLAUSE" ]]; then
            PORT_CLAUSE="port $p"
        else
            PORT_CLAUSE+=" or port $p"
        fi
    done
    PORT_FILTER="($PORT_CLAUSE)"
else
    # NOT_ALLOWED_CLAUSE looks like " and dst port not 80 and dst port not 443 ..."
    # strip the leading " and " so it stands alone as a valid filter on its own.
    PORT_FILTER="(${NOT_ALLOWED_CLAUSE# and })"
fi

# Direction clause: pin src/dst to local IP(s) depending on direction wanted.
# out  -> we are the source (attacker-from-here)
# in   -> we are the destination (someone probing us)
# both -> no host restriction beyond the SYN/port filter
# NOTE: BPF does not allow "src (host A or host B)" - the src/dst qualifier
# must be distributed over each term inside the parens individually.
SRC_CLAUSE=""
DST_CLAUSE=""
for ip in "${LOCAL_IPS[@]}"; do
    if [[ -z "$SRC_CLAUSE" ]]; then
        SRC_CLAUSE="src host $ip"
        DST_CLAUSE="dst host $ip"
    else
        SRC_CLAUSE+=" or src host $ip"
        DST_CLAUSE+=" or dst host $ip"
    fi
done

DIR_CLAUSE=""
if [[ -n "$SRC_CLAUSE" ]]; then
    case "$DIRECTION" in
        out)  DIR_CLAUSE=" and ($SRC_CLAUSE) and not ($DST_CLAUSE)" ;;
        in)   DIR_CLAUSE=" and ($DST_CLAUSE) and not ($SRC_CLAUSE)" ;;
        both) DIR_CLAUSE="" ;;
    esac
fi

BPF="tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0 and ${PORT_FILTER}${DIR_CLAUSE}"

# --- raw socket check function ---------------------------------------------------
check_raw_sockets() {
    {
        echo "  [raw sockets currently open on this host]"
        if [[ -r /proc/net/raw ]]; then
            n=$(wc -l < /proc/net/raw)
            if [[ "$n" -gt 1 ]]; then
                cat /proc/net/raw
                echo "  [processes holding raw sockets:]"
                for pid in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
                    if ls -l "/proc/$pid/fd" 2>/dev/null | grep -q "socket"; then
                        for fd in /proc/$pid/fd/*; do
                            target=$(readlink "$fd" 2>/dev/null)
                            if [[ "$target" == socket:* ]]; then
                                inode=$(echo "$target" | grep -oE '[0-9]+')
                                if grep -q "$inode" /proc/net/raw 2>/dev/null; then
                                    echo "    PID $pid ($(cat /proc/$pid/comm 2>/dev/null)) -> $(readlink /proc/$pid/exe 2>/dev/null)"
                                fi
                            fi
                        done
                    fi
                done
            else
                echo "  (none open right now - remember masscan-style scanners open/close raw sockets fast)"
            fi
        fi
    }
}

# --- snapshot function: run on every detected event -------------------------------
snapshot_state() {
    local srcip="$1" srcport="$2" dstip="$3" dstport="$4" dir_label="$5"
    {
        echo ""
        echo "=== EVENT: $(date -u +%Y-%m-%dT%H:%M:%S.%3NZ) [$dir_label] ${srcip}:${srcport} -> ${dstip}:${dstport} ==="

        if [[ "$dir_label" == "OUTBOUND" ]]; then
            echo "-- fast PID lookup by local port $srcport (this is US, so should resolve if it's a real connect()) --"
            ss -tnp 2>/dev/null | awk -v p=":$srcport " '$0 ~ p {print}'
            match_pid=$(ss -tnp 2>/dev/null | awk -v p=":$srcport " '$0 ~ p {print}' | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2)
            if [[ -n "${match_pid:-}" ]]; then
                echo "  >>> MATCHED PID $match_pid <<<"
                echo "  exe: $(readlink /proc/$match_pid/exe 2>/dev/null)"
                echo "  cmdline: $(tr '\0' ' ' < /proc/$match_pid/cmdline 2>/dev/null)"
                echo "  ppid/parent chain:"
                ps -o pid,ppid,user,cmd --no-headers -p "$match_pid" 2>/dev/null
                ppid=$(ps -o ppid= -p "$match_pid" 2>/dev/null | tr -d ' ')
                [[ -n "$ppid" ]] && ps -o pid,ppid,user,cmd --no-headers -p "$ppid" 2>/dev/null
            else
                echo "  (no ss match yet - if this is a raw-socket scanner, check the raw socket section below)"
            fi
        fi

        echo "-- ss (all established/syn-sent sockets) --"
        ss -tnp state established 2>/dev/null
        ss -tnp state syn-sent 2>/dev/null
        echo "-- lsof matching remote ip $dstip / $srcip --"
        lsof -i "@${dstip}" -P -n 2>/dev/null
        lsof -i "@${srcip}" -P -n 2>/dev/null
        echo "-- top CPU processes right now --"
        ps -eo pid,ppid,user,%cpu,%mem,etime,cmd --sort=-%cpu --no-headers | head -8
        check_raw_sockets
        echo "=== END EVENT ==="
    } >> "$EVENTLOG"
}

# --- start background full packet capture ------------------------------------------
tcpdump -i "$IFACE" -nn -w "$PCAPFILE" "$BPF" &
TCPDUMP_PCAP_PID=$!

cleanup() {
    echo "" | tee -a "$EVENTLOG"
    echo "Stopping watcher $(date)" | tee -a "$EVENTLOG"
    kill "$TCPDUMP_PCAP_PID" 2>/dev/null
    wait "$TCPDUMP_PCAP_PID" 2>/dev/null
    echo "Saved: $EVENTLOG"
    echo "Saved: $PCAPFILE (open with: tcpdump -r $PCAPFILE -nn, or Wireshark)"
    exit 0
}
trap cleanup INT TERM

echo "Watcher running (PID $$). Press Ctrl+C to stop." | tee -a "$EVENTLOG"

# --- live parsing loop: read matching packets as text, trigger snapshot on each ------
tcpdump -i "$IFACE" -nn -l -q "$BPF" 2>/dev/null | while read -r line; do
    # Typical line (no -e): 18:45:11.123456 IP 135.181.0.35.45983 > 78.46.11.64.6379: tcp 0
    # With -i any, may be prefixed: 18:45:11.123456 enp195s0 In  IP 201.50.85.154.53442 > 135.181.0.35.23: tcp 0
    src=$(echo "$line" | grep -oE 'IP6? [0-9a-fA-F:.]+\.[0-9]+ >' | head -1 | awk '{print $2}')
    dst=$(echo "$line" | grep -oE '> [0-9a-fA-F:.]+\.[0-9]+:' | head -1 | sed 's/[>:]//g' | tr -d ' ')
    if [[ -n "$src" && -n "$dst" ]]; then
        srcip="${src%.*}"; srcport="${src##*.}"
        dstip="${dst%.*}"; dstport="${dst##*.}"

        # Determine direction label for the log line (best-effort, based on local IP match)
        dir_label="UNKNOWN"
        for lip in "${LOCAL_IPS[@]}"; do
            if [[ "$srcip" == "$lip" ]]; then dir_label="OUTBOUND"; fi
            if [[ "$dstip" == "$lip" ]]; then dir_label="INBOUND"; fi
        done

        echo "$(date '+%H:%M:%S') [$dir_label] ${srcip}:${srcport} -> ${dstip}:${dstport}   raw: $line" | tee -a "$EVENTLOG"
        snapshot_state "$srcip" "$srcport" "$dstip" "$dstport" "$dir_label" &
    fi
done

wait