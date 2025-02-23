#!/bin/bash
source ../.venv

export PYTHONPATH=${CODX_JUNIOR_PATH}/api
export CODX_JUNIOR_STATIC_FOLDER=${CODX_JUNIOR_PATH}/client/dist

# Navigate to the directory where your FastAPI application is located
cd ${CODX_JUNIOR_PATH}/api
bash ${CODX_JUNIOR_PATH}/scripts/install_api.sh

# Run the FastAPI application using uvicorn
source ${CODX_JUNIOR_API_VENV}/bin/activate
DEBUG=$DEBUG
uvicorn codx.junior.main:app --reload --host 0.0.0.0 --port $CODX_JUNIOR_API_PORT