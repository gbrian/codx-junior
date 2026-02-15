#!/bin/bash
set -e

# 1. Start Docker daemon in the background
# We redirect output to a log file so it doesn't clutter the init process
rm -f /var/run/docker.pid || true
rm /var/run/docker/containerd/containerd.pid || true
dockerd-entrypoint.sh dockerd > /var/log/dockerd.log 2>&1 &

# 2. Wait for Docker to be ready
echo "[init] Waiting for Docker daemon to start..."
until docker info >/dev/null 2>&1; do
  tail -n 1 /var/log/dockerd.log
  sleep 1
done
echo "[init] Docker daemon is up and running."

# 3. Execute custom scripts from /custom-cont-init.d
if [ -d "/custom-cont-init.d" ]; then
    echo "[init] Running custom initialization scripts..."
    for f in $(ls /custom-cont-init.d/ | sort); do
        case "$f" in
            *.sh) echo "[init] executing /custom-cont-init.d/$f"; . "/custom-cont-init.d/$f" ;;
            *)    echo "[init] ignoring /custom-cont-init.d/$f" ;;
        esac
    done
fi

# 4. Keep the container alive by tailing the daemon logs
# This ensures the container stays running after scripts finish
echo "[init] Custom initialization complete. Tailing logs..."
cd /home/codx-junior/codx-junior/codx-junior-installer/codx-junior
docker-compose logs --tail=0 --follow
