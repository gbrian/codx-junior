#!/bin/bash

# Navigate to the project directory
cd ${CODX_JUNIOR_HOME}/browser
bash ${CODX_JUNIOR_HOME}/install_api.sh

# Run the FastAPI application using uvicorn
DEBUG=$DEBUG
uvicorn main:app --reload --host 0.0.0.0 --port $BROWSER_PORT

