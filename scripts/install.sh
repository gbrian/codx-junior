#!/bin/bash

# Function to log messages
log_info() {
  echo "[INFO] $1"
}

log_error() {
  echo "[ERROR] $1" >&2
}

# Stop script on error
set -e

# Load .env variables
source ${CODX_JUNIOR_PATH}/set_env.sh

# Fix user id
if [ "$USER_ID" != "" ];then
  echo "Setting codx-junior ID: $USER_ID"
  usermod -u $USER_ID codx-junior
  if [ "$USER_GROUP" != "" ];then
    echo "Setting codx-junior GROUP: $USER_GROUP"
    groupmod -g $USER_GROUP codx-junior
  fi
  
  chown -R codx-junior $HOME
  chown -R codx-junior $CODX_JUNIOR_API_VENV
fi


bash scripts/logo.sh

echo "Starting installation..."

# Installers
function install_client() {
  echo "Install web client"
  bash ${CODX_JUNIOR_PATH}/scripts/install_client.sh
}

function install_api() {
  echo "Install api"
  bash ${CODX_JUNIOR_PATH}/scripts/install_api.sh
}

echo "Load supervisor files"
for app in $CODX_JUNIOR_APPS; do

  # Execute custom instructions based on the app name
  case $app in
    client)
      install_client
      ;;
    api)
      install_api
      ;;
    *)
      echo "Unknown app: $app"
      ;;
  esac

done

echo "Installation complete!"