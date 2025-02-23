#!/bin/bash

# Navigate to the project directory
cd ${CODX_JUNIOR_PATH}/browser
bash ${CODX_JUNIOR_PATH}/scripts/install_api.sh

# Run the FastAPI application using uvicorn
source ${BROWSER_VENV}/bin/activate
DEBUG=$DEBUG
uvicorn main:app --reload --host 0.0.0.0 --port $BROWSER_PORT

