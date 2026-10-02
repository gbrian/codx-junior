#!/usr/bin/env bash
set -uo pipefail

BASE="${BASE:-/var/log/postmortem-collections}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${1:-$BASE/$STAMP}"
JOURNAL_SINCE="${JOURNAL_SINCE:-72 hours ago}"
DOCKER_LOG_SINCE="${DOCKER_LOG_SINCE:-72h}"

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

echo "Collecting postmortem data into: $OUT"

run acquisition-notes sh -c 'echo "Collector: postmortem_collect.sh"; date -u --iso-8601=seconds; hostname -f 2>/dev/null; uname -a; cat /etc/os-release 2>/dev/null || true'
run uptime uptime
run who who -a
run last-logins last -aiwx
run failed-logins lastb -aiwx
run processes ps auxwww
run process-tree sh -c 'command -v pstree >/dev/null && pstree -apuls || ps -efww'
run network-listening ss -tulpn
run network-established ss -tunap
run routes ip route show table all
run addresses ip addr show
run arp-neigh ip neigh show
run mounts findmnt
run disk-usage df -hT
run open-files sh -c 'command -v lsof >/dev/null && lsof -nP || true'
run deleted-open-files sh -c 'command -v lsof >/dev/null && lsof -nP +L1 || true'
run loaded-kernel-modules lsmod
run systemd-units systemctl list-units --all
run systemd-timers systemctl list-timers --all
run enabled-services systemctl list-unit-files
run installed-packages sh -c 'dpkg-query -W -f="${binary:Package}\t${Version}\n" 2>/dev/null || rpm -qa 2>/dev/null || true'
run apt-history sh -c 'cat /var/log/apt/history.log /var/log/apt/history.log.* 2>/dev/null || true'
run sudoers sh -c 'grep -R "^[^#]" /etc/sudoers /etc/sudoers.d 2>/dev/null || true'
run passwd-group-shadow-meta sh -c 'ls -la /etc/passwd /etc/group /etc/shadow /etc/gshadow 2>/dev/null; getent passwd; getent group'
run cron-listings sh -c 'ls -la /etc/cron* /var/spool/cron /var/spool/cron/crontabs 2>/dev/null; grep -R "^[^#]" /etc/cron* /var/spool/cron /var/spool/cron/crontabs 2>/dev/null || true'
run ssh-configs sh -c 'grep -R "^[^#]" /etc/ssh/sshd_config /etc/ssh/sshd_config.d 2>/dev/null || true'
run authorized-keys sh -c 'find /root /home -maxdepth 4 -name authorized_keys -type f -print -exec sh -c "echo === {}; sed -n '\''1,300p'\'' {}" \; 2>/dev/null || true'
run recent-files-tmp sh -c 'find /tmp /var/tmp /dev/shm -xdev -printf "%TY-%Tm-%Td %TT %m %u %g %s %p\n" 2>/dev/null | sort || true'
run recent-system-files sh -c 'find /etc /usr/local /opt -xdev -mtime -14 -printf "%TY-%Tm-%Td %TT %m %u %g %s %p\n" 2>/dev/null | sort || true'
run suid-sgid-files sh -c 'find / -xdev \( -perm -4000 -o -perm -2000 \) -type f -printf "%TY-%Tm-%Td %TT %m %u %g %s %p\n" 2>/dev/null | sort || true'
run running-exe-hashes sh -c 'for p in /proc/[0-9]*; do pid=${p#/proc/}; exe=$(readlink -f "$p/exe" 2>/dev/null || true); cmd=$(tr "\0" " " < "$p/cmdline" 2>/dev/null || true); [ -n "$exe" ] && [ -r "$exe" ] && sha256sum "$exe" 2>/dev/null | sed "s|$| pid=$pid cmd=$cmd|"; done | sort -u'

mkdir -p "$OUT/journal" "$OUT/var-log"
journalctl --since "$JOURNAL_SINCE" --no-pager > "$OUT/journal/all.log" 2>&1 || true
journalctl --since "$JOURNAL_SINCE" -u ssh -u sshd --no-pager > "$OUT/journal/ssh.log" 2>&1 || true
journalctl --since "$JOURNAL_SINCE" -k --no-pager > "$OUT/journal/kernel.log" 2>&1 || true

for f in /var/log/auth.log /var/log/auth.log.1 /var/log/secure /var/log/messages /var/log/syslog /var/log/syslog.1 /var/log/kern.log /var/log/cloud-init.log; do
  if [ -f "$f" ]; then
    cp -a "$f" "$OUT/var-log/" 2>/dev/null || true
  fi
done

if command -v docker >/dev/null 2>&1; then
  run docker-info docker info
  run docker-version docker version
  run docker-ps docker ps -a --no-trunc
  run docker-images docker images --digests
  run docker-networks docker network ls
  run docker-volumes docker volume ls

  mkdir -p "$OUT/docker-inspect" "$OUT/docker-logs" "$OUT/docker-top" "$OUT/docker-events"
  docker events --since "$DOCKER_LOG_SINCE" --until 0s > "$OUT/docker-events/events.log" 2>&1 || true

  docker ps -aq | while read -r c; do
    [ -z "$c" ] && continue
    name="$(docker inspect --format '{{.Name}}' "$c" 2>/dev/null | sed 's#^/##' | tr '/ :' '___')"
    docker inspect "$c" > "$OUT/docker-inspect/${name:-$c}.json" 2>&1 || true
    docker top "$c" auxww > "$OUT/docker-top/${name:-$c}.txt" 2>&1 || true
    docker logs --timestamps --since "$DOCKER_LOG_SINCE" "$c" > "$OUT/docker-logs/${name:-$c}.log" 2>&1 || true
  done
fi

ARCHIVE="$OUT.tar.gz"
tar -C "$(dirname "$OUT")" -czf "$ARCHIVE" "$(basename "$OUT")" 2>/dev/null || true
sha256sum "$ARCHIVE" > "$ARCHIVE.sha256" 2>/dev/null || true
chmod 600 "$ARCHIVE" "$ARCHIVE.sha256" 2>/dev/null || true

{
  echo "Postmortem collection complete."
  echo "Directory: $OUT"
  echo "Archive: $ARCHIVE"
  echo "Hash: $ARCHIVE.sha256"
  echo
  echo "Warning: archive may contain secrets, tokens, IPs, usernames, and logs."
} | tee "$OUT/README.txt"