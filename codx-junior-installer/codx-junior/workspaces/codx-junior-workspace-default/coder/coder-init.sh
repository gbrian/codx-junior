#!/usr/bin/with-contenv bash

TARGET_UID=$PUID
TARGET_GID=$PGID

# Check if the current process matches the target
if [ "$(id -u)" != "$TARGET_UID" ] || [ "$(id -g)" != "$TARGET_GID" ]; then
    echo "Re-executing as UID $TARGET_UID and GID $TARGET_GID..."
    # -u: specify user/UID, -g: specify group/GID
    exec sudo -u "#$TARGET_UID" -g "#$TARGET_GID" "$0" "$@"
fi

runcoder(){
  echo "Running coder for user: $(id -u):$(id -g)"

  # Ensure the install script runs
  curl -fsSL https://code-server.dev/install.sh | sh

  CODE_PORT=${CODE_SERVER_PORT:-9080}
  export CODER_HTTP_ADDRESS=0.0.0.0:${CODE_PORT}

  # Ensure directory exists before sed
  CODE_SERVER_DIR=/config/.local/share/code-server
  mkdir -p ${CODE_SERVER_DIR}

  echo "
bind-addr: 0.0.0.0:9080
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
