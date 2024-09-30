#!/bin/bash
. .env.dev

export STATIC_FOLDER=$PWD/client/dist

# Navigate to the directory where your FastAPI application is located
cd api

if [ ! -d "$PWD/.venv" ]; then
  echo "Installing codx-junior at $PWD/.env"
  python3 -m venv .venv
  source .venv/bin/activate
  pip install .  
fi

# Activate your python environment if any
source .venv/bin/activate

# Run the FastAPI application using uvicorn
uvicorn codx.junior.main:app --reload --port $API_PORT