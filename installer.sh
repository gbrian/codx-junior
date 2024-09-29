# Installer script for the API and Client

#!/bin/bash

echo "Starting installation..."

# Install API
echo "Installing API..."

if [ ! -d "api/.venv" ]; then
  cd api
  python3 -m venv .venv
  source .venv/bin/activate
  pip install .
  cd ..
fi

# Install Client
echo "Installing Client..."
(cd client && npm install)

echo "Installation completed successfully!"