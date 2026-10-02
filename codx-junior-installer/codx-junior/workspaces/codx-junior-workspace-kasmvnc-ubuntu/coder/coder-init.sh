#!/bin/bash

TARGET_UID=${PUID:-1000}
TARGET_GID=${PGID:-1000}

# Check if the current process matches the target
if [ "$(id -u)" != "$TARGET_UID" ] || [ "$(id -g)" != "$TARGET_GID" ]; then
    echo "Re-executing as UID $TARGET_UID and GID $TARGET_GID..."
    exec sudo -u "#$TARGET_UID" -g "#$TARGET_GID" "$0" "$@"
fi

runcoder(){
  echo "Running coder for user: $(id -u):$(id -g)"

  # Ensure the install script runs
  curl -fsSL https://code-server.dev/install.sh | sh

  CODE_PORT=${CODE_SERVER_PORT:-9080}
  export CODER_HTTP_ADDRESS=0.0.0.0:${CODE_PORT}

  # Ensure directory exists before writing config
  CODE_SERVER_DIR=${HOME}/.local/share/code-server
  mkdir -p ${CODE_SERVER_DIR}

  echo "
bind-addr: 0.0.0.0:${CODE_PORT}
auth: none
password: 8e240165f98d107aade5dbdc
cert: false
" > ${CODE_SERVER_DIR}/config.yaml

  exec code-server --config ${CODE_SERVER_DIR}/config.yaml
}

runcoder

while true; do
  sleep 10
done