#!/bin/bash

echo "Starting setup process..."

cd /config
echo "Changed directory to /config."

# Install codx-cli
echo "Installing codx-cli..."
curl -sL "https://raw.githubusercontent.com/gbrian/codx-cli/main/codx.sh" | bash -s
echo "codx-cli installation complete."

# Install codx-junior
cd /config/codx-junior
echo "Changed directory to /config/codx-junior."

echo "Installing codx-junior..."
bash codx-junior install
echo "codx-junior installation complete."

echo "Running codx-junior..."
bash codx-junior run
echo "codx-junior is running."

echo "Setup process completed successfully."