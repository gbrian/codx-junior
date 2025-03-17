#!/bin/bash

# Stop script on error
set -e

# Load .env variables
export $(grep -v '^#' ${CODX_JUNIOR_PATH}/.env | xargs)

bash scripts/logo.sh

echo "Starting installation..."

# Function to update and install packages
install_packages() {
    echo "Updating package list and installing packages..."
    sudo apt-get update
    sudo apt-get install -y \
        curl wget supervisor nano \
        locales python3 python3-venv \
        procps git sudo tesseract-ocr
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
codx docker
codx coder
codx nodejs

# Copy settings.json
echo "Copying VS Code settings..."
mkdir -p ${HOME}/.local/share/code-server/Machine
cp code-server/User/settings.json ${HOME}/.local/share/code-server/Machine/settings.json

# Create FileSync directory
echo "Creating FileSync directory..."
mkdir -p "${HOME}/FileSync"

echo "Install api"
bash ${CODX_JUNIOR_PATH}/scripts/install_api.sh

echo "Install client"
bash ${CODX_JUNIOR_PATH}/scripts/install_client.sh

echo "Install ollama"
bash ${CODX_JUNIOR_PATH}/scripts/install_ollama.sh

echo "Install noVNC"
bash ${CODX_JUNIOR_PATH}/scripts/install_noVNC.sh

echo "Installation complete!"