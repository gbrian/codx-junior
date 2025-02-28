#!/bin/bash
# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"

source ${CODX_JUNIOR_PATH}/.env

cd ${CODX_JUNIOR_PATH}/api
source ${CODX_JUNIOR_API_VENV}/bin/activate

export OLLAMA_MODELS=${CODX_JUNIOR_PATH}/ollama_models
mkdir -p OLLAMA_MODELS
ollama serve
