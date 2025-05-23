#!/bin/bash
# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"
echo "Starting api USER: ${USER} HOME: ${HOME}"

source ${CODX_JUNIOR_PATH}/set_env.sh

export PYTHONPATH=${CODX_JUNIOR_PATH}/api
export CODX_JUNIOR_STATIC_FOLDER=${CODX_JUNIOR_PATH}/client/dist

# Navigate to the directory where your FastAPI application is located
cd ${CODX_JUNIOR_PATH}/api
bash ${CODX_JUNIOR_PATH}/scripts/install_api.sh

# Run the FastAPI application using uvicorn
source ${CODX_JUNIOR_API_VENV}/bin/activate
export CODX_JUNIOR_API_BACKGROUND=1

if [ "$DEBUG" != ""]; then
  echo "*********** codx-junior api DEBUG ************"
  uvicorn codx.junior.main:app --reload --host 0.0.0.0 --port $CODX_JUNIOR_API_PORT_BACKGROUND
else
  echo "*********** codx-junior api PRODUCTION ************"
  uvicorn codx.junior.main:app --workers ${WEB_CONCURRENCY:-4} --host 0.0.0.0 --port $CODX_JUNIOR_API_PORT_BACKGROUND
fi