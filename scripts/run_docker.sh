#!/bin/bash
# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"
echo "Starting llmfactory USER: ${USER} HOME: ${HOME}"

source ${CODX_JUNIOR_PATH}/set_env.sh

dockerd