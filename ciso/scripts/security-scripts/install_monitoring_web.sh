#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root."
  exit 1
fi

BIND_ADDR="${BIND_ADDR:-127.0.0.1}"

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y curl ca-certificates netdata docker.io

systemctl enable --now docker || true

mkdir -p /etc/netdata

if [ -f /etc/netdata/netdata.conf ] && grep -q 'bind socket to IP' /etc/netdata/netdata.conf; then
  sed -i "s/^[# ]*bind socket to IP *=.*/        bind socket to IP = $BIND_ADDR/" /etc/netdata/netdata.conf
else
  cat >> /etc/netdata/netdata.conf <<NETDATA

[web]
        bind socket to IP = $BIND_ADDR
NETDATA
fi

systemctl enable --now netdata
systemctl restart netdata

docker pull gcr.io/cadvisor/cadvisor:latest

cat > /etc/systemd/system/cadvisor.service <<UNIT
[Unit]
Description=cAdvisor container monitoring web UI
After=docker.service
Requires=docker.service

[Service]
Restart=always
RestartSec=10
ExecStartPre=-/usr/bin/docker rm -f cadvisor
ExecStart=/usr/bin/docker run --rm --name cadvisor \\
  --volume=/:/rootfs:ro \\
  --volume=/var/run:/var/run:ro \\
  --volume=/sys:/sys:ro \\
  --volume=/var/lib/docker/:/var/lib/docker:ro \\
  --volume=/dev/disk/:/dev/disk:ro \\
  --device=/dev/kmsg \\
  --publish=$BIND_ADDR:8080:8080 \\
  gcr.io/cadvisor/cadvisor:latest
ExecStop=/usr/bin/docker stop cadvisor

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now cadvisor

echo "Monitoring installed."
echo
echo "Netdata:"
echo "  http://$BIND_ADDR:19999"
echo
echo "cAdvisor:"
echo "  http://$BIND_ADDR:8080"
echo
echo "Recommended remote access from your workstation:"
echo "  ssh -L 19999:127.0.0.1:19999 -L 8080:127.0.0.1:8080 root@135.181.0.35"
echo "  Then open:"
echo "    http://127.0.0.1:19999"
echo "    http://127.0.0.1:8080"
echo
echo "DIND note:"
echo "  Host cAdvisor shows host-level containers."
echo "  Nested containers inside DIND may require cAdvisor/Netdata inside each DIND environment."