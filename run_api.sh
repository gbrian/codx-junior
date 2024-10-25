#!/bin/bash
. .env.dev
set -e
export STATIC_FOLDER=$PWD/client/dist

# Navigate to the directory where your FastAPI application is located
cd api

API_VENV="/tmp/.venv_codx_junior"

if [ ! -d "$API_VENV/bin" ]; then
  echo "Installing codx-junior at $API_VENV"
  python3 -m venv $API_VENV
  source ${API_VENV}/bin/activate
  
  pip3 install wheel 
  
  pip3 install .  
fi

# Activate your python environment if any
source ${API_VENV}/bin/activate

# Run the FastAPI application using uvicorn
DEBUG=$DEBUG
uvicorn codx.junior.main:app --reload --host 0.0.0.0 --port $API_PORT