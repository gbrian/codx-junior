#!/bin/bash
# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"

source ${CODX_JUNIOR_PATH}/set_env.sh

export PYTHONPATH=${CODX_JUNIOR_PATH}/api

cd ${CODX_JUNIOR_PATH}/api
if [ ! -d "$CODX_JUNIOR_API_VENV/bin" ]; then
  echo "Installing codx-junior at $CODX_JUNIOR_API_VENV"
  python3.11 -m venv $CODX_JUNIOR_API_VENV
  source ${CODX_JUNIOR_API_VENV}/bin/activate
  
  pip3 install wheel 
  
  pip3 install .  
fi