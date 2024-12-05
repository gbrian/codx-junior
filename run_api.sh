#!/bin/bash
. .env.dev
set -e
export STATIC_FOLDER=$PWD/client/dist

# Navigate to the directory where your FastAPI application is located
cd ${CODX_JUNIOR_HOME}/api
bash ${CODX_JUNIOR_HOME}/install_api.sh

# Run the FastAPI application using uvicorn
DEBUG=$DEBUG
uvicorn codx.junior.main:app --reload --host 0.0.0.0 --port $API_PORT