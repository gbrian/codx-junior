#!/usr/bin/with-contenv bash

# Define target execution IDs
TARGET_UID=${PUID:-1001}
TARGET_GID=${PGID:-1001}

runcoder(){
  echo "Preparing environments for code-server..."

  # Establish port variables
  CODE_PORT=${CODE_SERVER_PORT:-9080}
  export CODER_HTTP_ADDRESS=0.0.0.0:${CODE_PORT}

  # Define profile directory paths
  CODE_SERVER_DIR=/config/.local/share/code-server
  
  # Ensure the directory exists and has correct ownership before creating configs
  mkdir -p "${CODE_SERVER_DIR}"
  chown -R "${TARGET_UID}:${TARGET_GID}" /config

  # Write out configuration file
  echo "
bind-addr: 0.0.0.0:9080
auth: none
password: 8e240165f98d107aade5dbdc
cert: false
" > "${CODE_SERVER_DIR}/config.yaml"

  echo "Launching code-server as user ${TARGET_UID}:${TARGET_GID}..."

  # Execute code-server directly as user 1001 inside the foreground process thread
  exec sudo -E -u "#${TARGET_UID}" -g "#${TARGET_GID}" code-server --config "${CODE_SERVER_DIR}/config.yaml" &
}

runcoder
