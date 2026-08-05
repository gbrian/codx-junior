#!/usr/bin/env bash
set -uo pipefail

OUT="${1:-/var/log/ir-active-analysis/$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$OUT"
chmod 700 "$OUT"

run() {
  local name="$1"
  shift
  {
    echo "### $name"
    echo "### UTC: $(date -u --iso-8601=seconds)"
    echo "### CMD: $*"
    echo
    "$@"
  } > "$OUT/$name.txt" 2>&1
}

echo "Writing active threat scan to: $OUT"

run host-date date -u
run host-uname uname -a
run host-uptime uptime
run host-who who -a
run host-last-logins last -aiwx
run host-lastb-failed-logins lastb -aiwx
run host-users getent passwd
run host-sudoers sh -c 'grep -R "^[^#]" /etc/sudoers /etc/sudoers.d 2>/dev/null || true'
run host-env sh -c 'env | sort'
run processes-cpu ps auxwww --sort=-%cpu
run processes-mem ps auxwww --sort=-%mem
run process-tree sh -c 'command -v pstree >/dev/null && pstree -apuls || ps -efww'
run network-listening ss -tulpn
run network-established ss -tunap
run routes ip route show table all
run addresses ip addr show
run iptables sh -c 'iptables-save 2>/dev/null; nft list ruleset 2>/dev/null'
run systemd-units systemctl list-units --type=service --all
run systemd-timers systemctl list-timers --all
run enabled-services systemctl list-unit-files --type=service
run cron-system sh -c 'ls -la /etc/cron* /var/spool/cron /var/spool/cron/crontabs 2>/dev/null; grep -R "^[^#]" /etc/cron* /var/spool/cron /var/spool/cron/crontabs 2>/dev/null || true'
run ssh-config sh -c 'grep -R "^[^#]" /etc/ssh/sshd_config /etc/ssh/sshd_config.d 2>/dev/null || true'
run recent-auth-logins sh -c 'journalctl --since "24 hours ago" -u ssh -u sshd --no-pager 2>/dev/null || true'
run recent-auth-files sh -c 'grep -E "Accepted|Failed|Invalid|sudo|session" /var/log/auth.log /var/log/secure 2>/dev/null | tail -1000 || true'
run suspicious-process-names sh -c 'ps auxwww | grep -Ei "xmrig|kinsing|kdevtmpfsi|kthrotlds|kinsing|masscan|zgrab|pnscan|minerd|cryptonight|watchbog|tsm|systemten|skidmap|ddgs|mirai|gafgyt|bash -i|/dev/tcp|curl .*\|.*sh|wget .*\|.*sh" | grep -v grep || true'
run deleted-running-binaries sh -c 'command -v lsof >/dev/null && lsof -nP +L1 || true'
run tmp-executables sh -c 'find /tmp /var/tmp /dev/shm -xdev -type f -perm /111 -printf "%TY-%Tm-%Td %TT %m %u %g %s %p\n" 2>/dev/null | sort || true'
run recent-executables sh -c 'find /bin /sbin /usr/bin /usr/sbin /usr/local/bin /usr/local/sbin /opt -xdev -type f -perm /111 -mtime -14 -printf "%TY-%Tm-%Td %TT %m %u %g %s %p\n" 2>/dev/null | sort || true'
run suid-sgid-files sh -c 'find / -xdev \( -perm -4000 -o -perm -2000 \) -type f -printf "%TY-%Tm-%Td %TT %m %u %g %s %p\n" 2>/dev/null | sort || true'
run world-writable-dirs sh -c 'find / -xdev -type d -perm -0002 -printf "%m %u %g %p\n" 2>/dev/null | sort || true'
run root-authorized-keys sh -c 'find /root /home -maxdepth 3 -name authorized_keys -type f -print -exec sh -c "echo === {}; sed -n '\''1,200p'\'' {}" \; 2>/dev/null || true'
run running-exe-hashes sh -c 'for p in /proc/[0-9]*; do pid=${p#/proc/}; exe=$(readlink -f "$p/exe" 2>/dev/null || true); [ -n "$exe" ] && [ -r "$exe" ] && sha256sum "$exe" 2>/dev/null | sed "s|$| pid=$pid|"; done | sort -u'

if command -v docker >/dev/null 2>&1; then
  run docker-info docker info
  run docker-ps docker ps -a --no-trunc
  run docker-images docker images --digests
  run docker-networks docker network ls
  run docker-volumes docker volume ls
  run docker-stats docker stats --no-stream --no-trunc

  {
    echo "### Docker container risk review"
    echo "### UTC: $(date -u --iso-8601=seconds)"
    echo
    docker ps -aq | while read -r c; do
      [ -z "$c" ] && continue
      name="$(docker inspect --format '{{.Name}}' "$c" 2>/dev/null | sed 's#^/##')"
      image="$(docker inspect --format '{{.Config.Image}}' "$c" 2>/dev/null)"
      privileged="$(docker inspect --format '{{.HostConfig.Privileged}}' "$c" 2>/dev/null)"
      pidmode="$(docker inspect --format '{{.HostConfig.PidMode}}' "$c" 2>/dev/null)"
      netmode="$(docker inspect --format '{{.HostConfig.NetworkMode}}' "$c" 2>/dev/null)"
      restart="$(docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' "$c" 2>/dev/null)"
      echo "container=$name id=$c image=$image privileged=$privileged pidmode=$pidmode netmode=$netmode restart=$restart"
      docker inspect --format '{{range .Mounts}}  mount {{.Source}} -> {{.Destination}} rw={{.RW}}{{println}}{{end}}' "$c" 2>/dev/null
      if [ "$privileged" = "true" ] || [ "$pidmode" = "host" ] || [ "$netmode" = "host" ]; then
        echo "  WARNING: high-risk namespace/privilege configuration"
      fi
      docker inspect --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}' "$c" 2>/dev/null | grep -E '/var/run/docker.sock|/var/lib/docker| -> /$| -> /root$| -> /etc$' >/dev/null && echo "  WARNING: sensitive host mount or Docker socket detected"
      echo
    done
  } > "$OUT/docker-risk-review.txt" 2>&1

  mkdir -p "$OUT/docker-inspect" "$OUT/docker-logs" "$OUT/docker-top"
  docker ps -aq | while read -r c; do
    [ -z "$c" ] && continue
    name="$(docker inspect --format '{{.Name}}' "$c" 2>/dev/null | sed 's#^/##' | tr '/ :' '___')"
    docker inspect "$c" > "$OUT/docker-inspect/${name:-$c}.json" 2>&1
    docker top "$c" auxww > "$OUT/docker-top/${name:-$c}.txt" 2>&1 || true
    docker logs --since 24h "$c" > "$OUT/docker-logs/${name:-$c}.log" 2>&1 || true
  done
fi

{
  echo "Active threat scan complete."
  echo "Output directory: $OUT"
  echo
  echo "Review first:"
  echo "  $OUT/suspicious-process-names.txt"
  echo "  $OUT/network-established.txt"
  echo "  $OUT/deleted-running-binaries.txt"
  echo "  $OUT/tmp-executables.txt"
  echo "  $OUT/docker-risk-review.txt"
} | tee "$OUT/README.txt"