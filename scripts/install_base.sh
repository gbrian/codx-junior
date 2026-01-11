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

bash scripts/logo.sh

echo "Starting installation..."

# Configure Git
echo "Configuring Git..."
git config --global --add safe.directory '*'

# Create necessary directories
echo "Creating necessary directories..."
sudo mkdir -p "${CODX_SUPERVISOR_LOG_FOLDER}"

# Install codx-cli
curl -sL "https://raw.githubusercontent.com/gbrian/codx-cli/main/codx.sh" | bash -s
