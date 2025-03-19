#!/bin/bash

# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"

# Source the environment variables
source ${CODX_JUNIOR_PATH}/.env

# Update package lists
sudo apt update

# Install required packages
sudo apt install -y git wget python3 python3-pip novnc websockify

# Clone the noVNC repository if it does not exist
if [ ! -d "${CODX_JUNIOR_PATH}/noVNC" ]; then
  git clone https://github.com/novnc/noVNC.git ${CODX_JUNIOR_PATH}/noVNC
fi

# Install a VNC server, e.g., TightVNCserver
sudo apt install -y tightvncserver

# Install a lightweight desktop environment, e.g., Xfce
sudo apt install -y xfce4 xfce4-goodies

# Install Firefox
sudo apt install -y firefox-esr

# Clean up
sudo apt autoremove -y

# Copy desktop files
cp -r ${CODX_JUNIOR_PATH}/scripts/Desktop ~/Desktop

echo "Installation of noVNC and its dependencies (including Firefox) completed successfully."
