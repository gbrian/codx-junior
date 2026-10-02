#!/bin/bash

# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"

source ${CODX_JUNIOR_PATH}/set_env.sh

# Install docker
codx docker &

export PYTHONPATH=${CODX_JUNIOR_PATH}/api

cd ${CODX_JUNIOR_PATH}/api

if [ ! -d "$CODX_JUNIOR_API_VENV/bin" ]; then
  echo "Installing codx-junior API for the first time at $CODX_JUNIOR_API_VENV ...will take some time."

  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Add uv to PATH
  PATH=$HOME/.local/bin:$PATH
  # No hardlinks in docker
  export UV_LINK_MODE=copy
  
  # Create environment using uv with specified Python version
  uv venv --python 3.11 "$CODX_JUNIOR_API_VENV"
  source "${CODX_JUNIOR_API_VENV}/bin/activate"
  
  # Install editable package using uv with the best-match strategy
  uv pip install -e . \
    --extra-index-url https://pytorch.org \
    --index-strategy unsafe-best-match

else
  echo "!!codx-junior API already installed at ${CODX_JUNIOR_API_VENV}"
fi
