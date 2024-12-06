#!/bin/bash

# Navigate to the directory where your FastAPI application is located
cd ${CODX_JUNIOR_HOME}/api
bash ${CODX_JUNIOR_HOME}/scripts/install_api.sh

# Run the FastAPI application using uvicorn
source ${API_VENV}/bin/activate
DEBUG=$DEBUG
uvicorn codx.junior.main:app --reload --host 0.0.0.0 --port $API_PORT