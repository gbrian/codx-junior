#!/bin/bash
# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"
echo "Starting llmfactory USER: ${USER} HOME: ${HOME}"

source ${CODX_JUNIOR_PATH}/set_env.sh

cd ${CODX_JUNIOR_PATH}/api
source ${CODX_JUNIOR_API_VENV}/bin/activate

if [ "$OLLAMA_MODELS" == "" ]; then
  export OLLAMA_MODELS=${CODX_JUNIOR_PATH}/ollama_models
  mkdir -p $OLLAMA_MODELS
fi
export OLLAMA_HOST=0.0.0.0:${CODX_JUNIOR_LLMFACTORY_PORT:-11434}
ollama serve
