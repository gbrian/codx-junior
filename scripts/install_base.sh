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

# Function to update and install packages
install_packages() {
    echo "Updating package list and installing packages..."
    sudo apt-get update
    sudo apt-get install -y \
        curl wget supervisor nano \
        locales python3.11 python3.11-venv firefox-esr \
        procps git tesseract-ocr
    sudo apt-get clean
    sudo rm -rf /var/lib/apt/lists/*
}

# Invoke the function to install packages
install_packages

# Configure Git
echo "Configuring Git..."
git config --global --add safe.directory '*'

# Create necessary directories
echo "Creating necessary directories..."
sudo mkdir -p "${CODX_SUPERVISOR_LOG_FOLDER}"

# Install codx APPS
echo "Installing codx APPS..."
curl -sL "https://raw.githubusercontent.com/gbrian/codx-cli/main/codx.sh" | bash -s

