#!/usr/bin/env bash
# =============================================================================
# security_audit.sh — codx-junior environment security audit
# Generates a structured report of active threats and anomalies
# Usage: sudo bash scripts/security_audit.sh [--output /path/to/report.md]
# Note: Reports are written to ./logs/security/ relative to script execution directory
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
PROJECT_PATH="/home/codx-junior-projects/codx-junior"
# CHANGED: Use relative path from current working directory
REPORT_DIR="./logs/security"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="${REPORT_DIR}/security_report_${TIMESTAMP}.md"
OUTPUT_OVERRIDE=""

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) OUTPUT_OVERRIDE="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

[[ -n "$OUTPUT_OVERRIDE" ]] && REPORT_FILE="$OUTPUT_OVERRIDE"
mkdir -p "$(dirname "$REPORT_FILE")"

# ---------------------------------------------------------------------------
# KNOWN-SAFE PROCESS PATTERNS (whitelist)
# Update this list as confirmed-safe processes are identified
# ---------------------------------------------------------------------------
SAFE_PATTERNS=(
  "outbound_traffic_scan"
  "watch_docker_scan"
  "scanwatch_"
  "tcpdump.*scanwatch"
  "bdsecd"                        # BitDefender security agent
  "sysbox-mgr"
  "sysbox-fs"
  "sysbox-runc"
  "milvus"
  "ollama"
  "traefik"
  "dockerd"
  "containerd"
  "code-server"
  "uvicorn codx.junior"
  "vite"
  "selkies"
  "s6-svscan"
  "s6-supervise"
  "MroManagementApplication"
  "mvn.*spring-boot"
  "ng serve"
  "postgres"
  "jedi-language-server"
  "vue.volar"
  "tsserver"
  "dockerfile-language-server"
  "compose-language-service"
  "docker-proxy"
  "docker-init"
  "docker events"
)

# ---------------------------------------------------------------------------
# COLORS (only when writing to terminal, not to file)
# ---------------------------------------------------------------------------
if [[ -t 1 ]]; then
  RED='\033[0;31m'; ORANGE='\033[0;33m'; YELLOW='\033[1;33m'
  GREEN='\033[0;32m'; BLUE='\033[0;34m'; RESET='\033[0m'; BOLD='\033[1m'
else
  RED=''; ORANGE=''; YELLOW=''; GREEN=''; BLUE=''; RESET=''; BOLD=''
fi

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
log()   { echo -e "${BLUE}[*]${RESET} $*"; }
ok()    { echo -e "${GREEN}[✓]${RESET} $*"; }
warn()  { echo -e "${YELLOW}[!]${RESET} $*"; }
alert() { echo -e "${RED}[✗]${RESET} $*"; }

proc_exists() { [[ -d "/proc/$1" ]]; }

get_proc_cmd() {
  local pid="$1"
  if [[ -r "/proc/${pid}/cmdline" ]]; then
    tr '\0' ' ' < "/proc/${pid}/cmdline" | sed 's/ $//'
  else
    echo "[unreadable]"
  fi
}

get_proc_stat() {
  local pid="$1" field="$2"
  if [[ -r "/proc/${pid}/status" ]]; then
    grep "^${field}:" "/proc/${pid}/status" | awk '{print $2}'
  else
    echo "?"
  fi
}

is_safe_process() {
  local cmd="$1"
  for pattern in "${SAFE_PATTERNS[@]}"; do
    if echo "$cmd" | grep -qE "$pattern"; then
      return 0
    fi
  done
  return 1
}

section() {
  echo ""
  echo "---"
  echo ""
  echo "## $*"
  echo ""
}

subsection() {
  echo ""
  echo "### $*"
  echo ""
}

# ---------------------------------------------------------------------------
# REPORT BUFFER — write to both terminal and file
# ---------------------------------------------------------------------------
REPORT_BUFFER=""
report() {
  echo -e "$*"
  REPORT_BUFFER+="$*"$'\n'
}
flush_report() { echo -e "$REPORT_BUFFER" > "$REPORT_FILE"; }

# Redirect report() output to file as well
exec > >(tee -a "$REPORT_FILE") 2>&1

# ---------------------------------------------------------------------------
# REPORT HEADER
# ---------------------------------------------------------------------------
echo "# codx-junior Security Audit Report"
echo ""
echo "| Field | Value |"
echo "|---|---|"
echo "| **Generated** | $(date '+%Y-%m-%d %H:%M:%S %Z') |"
echo "| **Host** | $(hostname) |"
echo "| **Kernel** | $(uname -r) |"
echo "| **Uptime** | $(uptime -p 2>/dev/null || uptime) |"
echo "| **Run as** | $(id) |"
echo "| **Report path** | \`${REPORT_FILE}\` |"
echo ""

# ---------------------------------------------------------------------------
# SECTION 1: ZOMBIE PROCESS INVESTIGATION
# ---------------------------------------------------------------------------
section "1. Zombie Process Investigation"

echo "Scanning for zombie (DEFUNCT) processes..."
echo ""

ZOMBIE_FOUND=0
ZOMBIE_TABLE="| PID | PPID | User | Command | Started | Notes |\n|---|---|---|---|---|---|\n"

while IFS= read -r line; do
  pid=$(echo "$line" | awk '{print $1}')
  ppid=$(echo "$line" | awk '{print $3}')
  user=$(echo "$line" | awk '{print $2}')
  cmd=$(echo "$line" | awk '{print $NF}')
  started=$(echo "$line" | awk '{print $9, $10}')
  
  ZOMBIE_FOUND=$((ZOMBIE_FOUND + 1))

  # Inspect parent
  parent_cmd="[unknown]"
  if proc_exists "$ppid"; then
    parent_cmd=$(get_proc_cmd "$ppid")
  fi

  # Check container association
  container_id="[host]"
  if [[ -r "/proc/${pid}/cgroup" ]]; then
    container_id=$(grep -oE '[a-f0-9]{12,}' "/proc/${pid}/cgroup" | head -1 || echo "[host]")
  fi

  note="Parent: \`$(echo "$parent_cmd" | cut -c1-60)\` | Container: \`${container_id}\`"
  ZOMBIE_TABLE+="| **${pid}** | ${ppid} | ${user} | \`${cmd}\` | ${started} | ${note} |\n"

  # Extra inspection
  echo "#### Zombie PID ${pid}: \`${cmd}\`"
  echo ""
  echo "| Attribute | Value |"
  echo "|---|---|"
  echo "| PPID | ${ppid} |"
  echo "| User | ${user} |"
  echo "| Parent CMD | \`$(echo "$parent_cmd" | cut -c1-80)\` |"
  echo "| Container | \`${container_id}\` |"

  # Try to read any remaining proc info before it's fully reaped
  if [[ -r "/proc/${pid}/status" ]]; then
    vm_peak=$(grep VmPeak "/proc/${pid}/status" 2>/dev/null | awk '{print $2, $3}' || echo "n/a")
    threads=$(grep Threads "/proc/${pid}/status" 2>/dev/null | awk '{print $2}' || echo "n/a")
    echo "| Peak Memory | ${vm_peak} |"
    echo "| Threads | ${threads} |"
  fi

  # Check if parent is a known-dangerous container
  if echo "$parent_cmd" | grep -qE "sleep infinity|c1a114"; then
    echo "| ⚠️ Risk | **Parent is \`sleep infinity\` — unexpected shell execution** |"
  fi
  echo ""

  # Check environ for clues
  if [[ -r "/proc/${pid}/environ" ]]; then
    echo "**Environment variables (selected):**"
    echo "\`\`\`"
    tr '\0' '\n' < "/proc/${pid}/environ" 2>/dev/null \
      | grep -E '^(PATH|HOME|USER|SHELL|PWD|_|TERM)=' \
      | head -10 || echo "[empty or unreadable]"
    echo "\`\`\`"
  fi
  echo ""

done < <(ps axo pid,user,ppid,stat,stime,time,cmd --no-headers 2>/dev/null | awk '$4 ~ /Z/')

if [[ $ZOMBIE_FOUND -eq 0 ]]; then
  ok "**No zombie processes found.**"
  echo ""
else
  echo "> ⚠️ **${ZOMBIE_FOUND} zombie process(es) detected**"
  echo ""
  echo -e "$ZOMBIE_TABLE"
fi

# ---------------------------------------------------------------------------
# SECTION 2: SUSPICIOUS CONTAINER INSPECTION (c1a114)
# ---------------------------------------------------------------------------
section "2. Suspicious Container Deep Inspection"

TARGET_CONTAINERS=("c1a114")

for CONTAINER in "${TARGET_CONTAINERS[@]}"; do
  # ADDED: Retrieve container name alongside ID
  container_name=$(docker inspect "$CONTAINER" --format='{{.Name}}' 2>/dev/null | sed 's|^/||' || echo "[unknown]")
  subsection "Container: \`${CONTAINER}\` (\`${container_name}\`)"

  if ! docker inspect "$CONTAINER" &>/dev/null; then
    warn "Container \`${CONTAINER}\` not found or not running"
    continue
  fi

  echo "**Container metadata:**"
  echo "\`\`\`json"
  docker inspect "$CONTAINER" \
    | jq -r '.[0] | {
        Id: .Id[:12],
        Name: .Name,
        Image: .Config.Image,
        Created: .Created,
        Status: .State.Status,
        StartedAt: .State.StartedAt,
        Mounts: [.Mounts[] | {src: .Source, dst: .Destination}],
        Entrypoint: .Config.Entrypoint,
        Cmd: .Config.Cmd,
        Labels: .Config.Labels
      }' 2>/dev/null || echo "[inspect failed]"
  echo "\`\`\`"
  echo ""

  echo "**Running processes inside container:**"
  echo "\`\`\`"
  docker exec "$CONTAINER" ps auxf 2>/dev/null || echo "[exec failed — container may be minimal]"
  echo "\`\`\`"
  echo ""

  echo "**Filesystem changes (docker diff):**"
  echo "\`\`\`"
  docker diff "$CONTAINER" 2>/dev/null | head -50 || echo "[diff unavailable]"
  echo "\`\`\`"
  echo ""

  echo "**Recently modified files (last 24h):**"
  echo "\`\`\`"
  docker exec "$CONTAINER" find / -newer /proc/1/exe -type f 2>/dev/null \
    | grep -vE '^/(proc|sys|dev)' \
    | head -30 || echo "[find failed or no results]"
  echo "\`\`\`"
  echo ""

  echo "**Container logs (last 50 lines):**"
  echo "\`\`\`"
  docker logs --tail 50 --timestamps "$CONTAINER" 2>/dev/null || echo "[no logs]"
  echo "\`\`\`"
  echo ""

  echo "**Network connections from container:**"
  echo "\`\`\`"
  docker exec "$CONTAINER" ss -tnp 2>/dev/null \
    | grep -v '127.0.0.1' \
    | grep ESTAB || echo "[none or ss unavailable]"
  echo "\`\`\`"
  echo ""

  echo "**Cron jobs inside container:**"
  echo "\`\`\`"
  docker exec "$CONTAINER" crontab -l 2>/dev/null || echo "[no crontab]"
  docker exec "$CONTAINER" ls -la /etc/cron* /var/spool/cron* 2>/dev/null || echo "[no cron dirs]"
  echo "\`\`\`"
  echo ""

  # Check for suspicious binaries
  echo "**SUID/SGID binaries (unexpected):**"
  echo "\`\`\`"
  docker exec "$CONTAINER" find / -perm /6000 -type f 2>/dev/null \
    | grep -vE '^/(bin|usr/bin|usr/sbin|sbin)' \
    | head -20 || echo "[none found outside standard paths]"
  echo "\`\`\`"
  echo ""
done

# ---------------------------------------------------------------------------
# SECTION 3: HIGH CPU PYTHON WORKERS
# ---------------------------------------------------------------------------
section "3. High-CPU Python Worker Analysis"

echo "Scanning for python multiprocessing workers with sustained high CPU..."
echo ""

HIGH_CPU_THRESHOLD=50
WORKER_COUNT=0
WORKER_TABLE="| PID | CPU% | RSS (MB) | Start | Parent PID | Parent CMD | Outbound Connections |\n|---|---|---|---|---|---|---|\n"

while IFS= read -r line; do
  pid=$(echo "$line" | awk '{print $1}')
  cpu=$(echo "$line" | awk '{print $3}')
  rss_kb=$(echo "$line" | awk '{print $6}')
  rss_mb=$(( rss_kb / 1024 ))
  started=$(echo "$line" | awk '{print $9}')
  cmd=$(echo "$line" | cut -d' ' -f11-)

  # Filter: python workers only
  echo "$cmd" | grep -qiE 'python|multiprocessing|worker' || continue

  # CPU check
  cpu_int=${cpu%.*}
  [[ "$cpu_int" -lt "$HIGH_CPU_THRESHOLD" ]] 2>/dev/null && continue

  WORKER_COUNT=$((WORKER_COUNT + 1))

  ppid=$(get_proc_stat "$pid" "PPid")
  parent_cmd="[unknown]"
  [[ -n "$ppid" ]] && parent_cmd=$(get_proc_cmd "$ppid" | cut -c1-60)

  # Network connections
  outbound="none"
  if [[ -r "/proc/${pid}/net/tcp" ]]; then
    outbound=$(awk 'NR>1 && $4!="0A" {print $3}' "/proc/${pid}/net/tcp" \
      | while read -r hex; do
          printf '%d.%d.%d.%d:%d\n' \
            "0x${hex:6:2}" "0x${hex:4:2}" "0x${hex:2:2}" "0x${hex:0:2}" \
            "$((16#${hex:9:4}))" 2>/dev/null
        done | grep -v '0.0.0.0' | tr '\n' ', ' || echo "none")
  fi

  WORKER_TABLE+="| **${pid}** | ${cpu}% | ${rss_mb} MB | ${started} | ${ppid} | \`${parent_cmd}\` | \`${outbound}\` |\n"

  echo "#### Worker PID ${pid}"
  echo ""
  echo "| Attribute | Value |"
  echo "|---|---|"
  echo "| CPU% | **${cpu}%** |"
  echo "| RSS | **${rss_mb} MB** |"
  echo "| Started | ${started} |"
  echo "| Parent PID | ${ppid} |"
  echo "| Parent CMD | \`${parent_cmd}\` |"
  echo "| Outbound | \`${outbound}\` |"
  echo ""

  # Check open files for clues
  echo "**Open files/sockets (top 20):**"
  echo "\`\`\`"
  lsof -p "$pid" 2>/dev/null \
    | grep -vE '(mem|/lib|/usr/lib|\.so)' \
    | head -20 || echo "[lsof unavailable or permission denied]"
  echo "\`\`\`"
  echo ""

  # Check syscall activity
  echo "**Recent syscall summary (3s sample):**"
  echo "\`\`\`"
  if command -v strace &>/dev/null; then
    timeout 3 strace -p "$pid" -c 2>&1 | tail -20 || echo "[strace timed out or permission denied]"
  else
    echo "[strace not available]"
  fi
  echo "\`\`\`"
  echo ""

done < <(ps aux --no-headers 2>/dev/null)

if [[ $WORKER_COUNT -eq 0 ]]; then
  ok "**No high-CPU python workers found at time of scan.**"
  echo ""
  echo "> ℹ️ The workers at PIDs 4159778/4159780 (127-128% CPU) may have completed their burst."
  echo ""
else
  echo -e "$WORKER_TABLE"
fi

# ---------------------------------------------------------------------------
# SECTION 4: UNKNOWN PROCESS AUDIT
# ---------------------------------------------------------------------------
section "4. Unclassified Process Audit"

echo "Scanning all processes against known-safe whitelist..."
echo ""

UNKNOWN_TABLE="| PID | User | CPU% | RSS(MB) | Started | Command | Risk Indicators |\n|---|---|---|---|---|---|---|\n"
UNKNOWN_COUNT=0

while IFS= read -r line; do
  pid=$(echo "$line" | awk '{print $1}')
  user=$(echo "$line" | awk '{print $2}')
  cpu=$(echo "$line" | awk '{print $3}')
  rss_kb=$(echo "$line" | awk '{print $6}')
  rss_mb=$(( rss_kb / 1024 ))
  started=$(echo "$line" | awk '{print $9}')
  cmd=$(echo "$line" | cut -d' ' -f11-)

  # Skip kernel threads
  [[ "$cmd" == "["* ]] && continue

  # Skip if safe
  is_safe_process "$cmd" && continue

  # Skip very short commands unlikely to be threats
  [[ ${#cmd} -lt 4 ]] && continue

  UNKNOWN_COUNT=$((UNKNOWN_COUNT + 1))

  # Gather risk indicators
  risks=""
  cpu_int=${cpu%.*}
  rss_int=$rss_mb

  [[ "$cpu_int" -ge 20 ]] 2>/dev/null && risks+="HIGH_CPU "
  [[ "$rss_int" -ge 500 ]] 2>/dev/null && risks+="HIGH_MEM "
  echo "$cmd" | grep -qiE '(nc|ncat|netcat|socat|curl|wget|bash.*-i|sh.*-i)' && risks+="NET_TOOL "
  echo "$cmd" | grep -qiE '(base64|xxd|openssl|gpg|crypto)' && risks+="ENCODING "
  echo "$cmd" | grep -qiE '(cron|at |nohup|disown|setsid)' && risks+="PERSISTENCE "
  echo "$cmd" | grep -qiE '(/tmp/|/dev/shm|/run/shm|/var/tmp)' && risks+="TMP_EXEC "
  echo "$cmd" | grep -qiE '(python|ruby|perl|php).*(-c|-e|exec|eval)' && risks+="CODE_EXEC "

  [[ -z "$risks" ]] && risks="review"

  cmd_short=$(echo "$cmd" | cut -c1-70)
  UNKNOWN_TABLE+="| ${pid} | ${user} | ${cpu}% | ${rss_mb} | ${started} | \`${cmd_short}\` | ${risks} |\n"

done < <(ps aux --no-headers 2>/dev/null | sort -k3 -rn)

if [[ $UNKNOWN_COUNT -eq 0 ]]; then
  ok "**All running processes match known-safe patterns.**"
else
  echo "> ⚠️ **${UNKNOWN_COUNT} process(es) not matched to known-safe patterns — manual review recommended**"
  echo ""
  echo -e "$UNKNOWN_TABLE"
fi
echo ""

# ---------------------------------------------------------------------------
# SECTION 5: NETWORK CONNECTIONS AUDIT
# ---------------------------------------------------------------------------
section "5. Network Connections Audit"

echo "**Established outbound connections (non-loopback):**"
echo "\`\`\`"
ss -tnp 2>/dev/null \
  | grep ESTAB \
  | grep -v '127.0.0.1\|::1' \
  | sort -k4 \
  || echo "[none]"
echo "\`\`\`"
echo ""

echo "**Listening ports:**"
echo "\`\`\`"
ss -tulpn 2>/dev/null | sort -k5 || echo "[unavailable]"
echo "\`\`\`"
echo ""

echo "**Unexpected LISTEN ports (outside known service set):**"
KNOWN_PORTS="80|443|19980|19981|19984|3000|8008|8085|22"
echo "\`\`\`"
ss -tulpn 2>/dev/null \
  | grep LISTEN \
  | grep -vE ":($KNOWN_PORTS)\b" \
  || echo "[none — all listening ports are in known set]"
echo "\`\`\`"
echo ""

# ---------------------------------------------------------------------------
# SECTION 6: FILESYSTEM INTEGRITY CHECKS
# ---------------------------------------------------------------------------
section "6. Filesystem Integrity Checks"

subsection "6a. SUID/SGID Binaries Outside Standard Paths"
echo "\`\`\`"
find / -perm /6000 -type f 2>/dev/null \
  | grep -vE '^/(bin|usr/bin|usr/sbin|sbin|lib|usr/lib|opt/bitdefender)' \
  | head -30 \
  || echo "[none found]"
echo "\`\`\`"
echo ""

subsection "6b. World-Writable Directories in Sensitive Paths"
echo "\`\`\`"
find /etc /usr /bin /sbin -perm -0002 -type d 2>/dev/null \
  | head -20 \
  || echo "[none found]"
echo "\`\`\`"
echo ""

subsection "6c. Recently Modified Files in System Paths (last 24h)"
echo "\`\`\`"
find /etc /usr/bin /usr/sbin /bin /sbin -newer /proc/1/exe -type f 2>/dev/null \
  | head -30 \
  || echo "[none found]"
echo "\`\`\`"
echo ""

subsection "6d. Files in /tmp, /dev/shm, /run/shm (execution risk)"
echo "\`\`\`"
find /tmp /dev/shm /run/shm -type f 2>/dev/null | head -30 || echo "[none]"
echo "\`\`\`"
echo ""

# ---------------------------------------------------------------------------
# SECTION 7: PERSISTENCE MECHANISMS
# ---------------------------------------------------------------------------
section "7. Persistence Mechanism Check"

subsection "7a. Crontab (root + all users)"
echo "\`\`\`"
crontab -l 2>/dev/null || echo "[no root crontab]"
echo ""
for user_home in /home/* /root; do
  user=$(basename "$user_home")
  crontab -u "$user" -l 2>/dev/null && echo "  ^^ user: $user" || true
done
echo "\`\`\`"
echo ""

subsection "7b. System Cron Files"
echo "\`\`\`"
ls -la /etc/cron.d/ /etc/cron.daily/ /etc/cron.hourly/ /etc/cron.weekly/ 2>/dev/null || echo "[no cron dirs]"
echo "\`\`\`"
echo ""

subsection "7c. SSH Authorized Keys"
echo "\`\`\`"
for key_file in /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys; do
  if [[ -f "$key_file" ]]; then
    echo "=== ${key_file} ==="
    cat "$key_file"
  fi
done
echo "\`\`\`"
echo ""

subsection "7d. New/Modified Users (UID < 1000 added recently)"
echo "\`\`\`"
awk -F: '$3 < 1000 && $1 != "root" {print $1, $3, $6, $7}' /etc/passwd
echo "\`\`\`"
echo ""

subsection "7e. Systemd/Init Drop-ins"
echo "\`\`\`"
find /etc/systemd /etc/init.d /etc/rc.local -newer /proc/1/exe -type f 2>/dev/null \
  | head -20 || echo "[none modified recently]"
echo "\`\`\`"
echo ""

# ---------------------------------------------------------------------------
# SECTION 8: DOCKER ENVIRONMENT AUDIT
# ---------------------------------------------------------------------------
section "8. Docker Environment Audit"

subsection "8a. All Running Containers"
# CHANGED: Include container name in output
echo "\`\`\`"
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null \
  || echo "[docker not available or permission denied]"
echo "\`\`\`"
echo ""

subsection "8b. Containers with Privileged or Host-Network Mode"
echo "\`\`\`"
docker ps -q 2>/dev/null | while read -r cid; do
  privileged=$(docker inspect "$cid" --format '{{.HostConfig.Privileged}}' 2>/dev/null)
  net_mode=$(docker inspect "$cid" --format '{{.HostConfig.NetworkMode}}' 2>/dev/null)
  # ADDED: Retrieve container name
  name=$(docker inspect "$cid" --format '{{.Name}}' 2>/dev/null | sed 's|^/||')
  if [[ "$privileged" == "true" || "$net_mode" == "host" ]]; then
    echo "FLAGGED: ${cid:0:12} (${name}) | privileged=${privileged} | network=${net_mode}"
  fi
done || echo "[no flagged containers]"
echo "\`\`\`"
echo ""

subsection "8c. Container c1a114 — Full Audit"
if docker inspect c1a114 &>/dev/null; then
  # ADDED: Retrieve container name for header
  c1a114_name=$(docker inspect c1a114 --format='{{.Name}}' 2>/dev/null | sed 's|^/||' || echo "[unknown]")
  echo "\`\`\`"
  echo "=== Container: c1a114 (${c1a114_name}) ==="
  echo ""
  echo "=== Inspect ==="
  docker inspect c1a114 | jq -r '.[0] | {
    Id: .Id[:12], Image: .Config.Image, Cmd: .Config.Cmd,
    Entrypoint: .Config.Entrypoint, Created: .Created,
    Mounts: .Mounts, NetworkSettings: .NetworkSettings.Networks
  }' 2>/dev/null
  echo ""
  echo "=== Processes ==="
  docker exec c1a114 ps auxf 2>/dev/null || echo "[exec failed]"
  echo ""
  echo "=== Filesystem diff ==="
  docker diff c1a114 2>/dev/null
  echo "\`\`\`"
else
  warn "Container c1a114 not found"
fi
echo ""

subsection "8d. Images Not From Known Registries"
echo "\`\`\`"
docker images --format "{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}" 2>/dev/null \
  | grep -vE '(docker\.io|ghcr\.io|gcr\.io|quay\.io|codx|traefik|milvus|ollama|postgres|node|python|openjdk)' \
  | head -20 \
  || echo "[all images from known registries]"
echo "\`\`\`"
echo ""

# ---------------------------------------------------------------------------
# SECTION 9: SUMMARY
# ---------------------------------------------------------------------------
section "9. Executive Summary"

echo "| Check | Status | Detail |"
echo "|---|---|---|"

# Zombie check
if ps axo stat 2>/dev/null | grep -q Z; then
  zombie_count=$(ps axo stat 2>/dev/null | grep -c Z || echo 0)
  echo "| Zombie Processes | 🔴 CRITICAL | ${zombie_count} zombie(s) found — see Section 1 |"
else
  echo "| Zombie Processes | ✅ Clear | No zombies at time of scan |"
fi

# High CPU workers
high_cpu_workers=$(ps aux --no-headers 2>/dev/null \
  | awk '$3 > 50 && /python/ && /worker/' | wc -l)
if [[ "$high_cpu_workers" -gt 0 ]]; then
  echo "| High-CPU Python Workers | 🟠 High | ${high_cpu_workers} worker(s) above 50% CPU |"
else
  echo "| High-CPU Python Workers | ✅ Clear | No sustained high-CPU workers |"
fi

# Unexpected listening ports
unexpected_ports=$(ss -tulpn 2>/dev/null | grep LISTEN \
  | grep -vcE ":($KNOWN_PORTS)\b" || echo 0)
if [[ "$unexpected_ports" -gt 0 ]]; then
  echo "| Unexpected Listening Ports | 🟡 Medium | ${unexpected_ports} port(s) outside known set |"
else
  echo "| Unexpected Listening Ports | ✅ Clear | All ports in known set |"
fi

# SUID outside standard
suid_outside=$(find / -perm /6000 -type f 2>/dev/null \
  | grep -vcE '^/(bin|usr/bin|usr/sbin|sbin|lib|usr/lib|opt/bitdefender)' || echo 0)
if [[ "$suid_outside" -gt 0 ]]; then
  echo "| SUID Binaries Outside Standard Paths | 🟡 Medium | ${suid_outside} file(s) found |"
else
  echo "| SUID Binaries | ✅ Clear | All SUID in standard paths |"
fi

# Tmp files
tmp_files=$(find /tmp /dev/shm /run/shm -type f 2>/dev/null | wc -l)
if [[ "$tmp_files" -gt 0 ]]; then
  echo "| Files in /tmp//dev/shm | 🟡 Review | ${tmp_files} file(s) present |"
else
  echo "| Files in /tmp//dev/shm | ✅ Clear | No files in temp execution paths |"
fi

# Unclassified processes
if [[ "$UNKNOWN_COUNT" -gt 0 ]]; then
  echo "| Unclassified Processes | 🟡 Review | ${UNKNOWN_COUNT} process(es) not in safe list |"
else
  echo "| Unclassified Processes | ✅ Clear | All processes matched safe patterns |"
fi

echo ""
echo "> **Report saved to:** \`${REPORT_FILE}\`"
echo ""
echo "_codx-junior security_audit.sh — $(date '+%Y-%m-%d %H:%M:%S')_"