#!/bin/bash
# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"
echo "Starting api USER: ${USER} HOME: ${HOME}"

source ${CODX_JUNIOR_PATH}/set_env.sh

export PYTHONPATH=${CODX_JUNIOR_PATH}/api

cd ${CODX_JUNIOR_PATH}/api
if [ ! -d "$CODX_JUNIOR_API_VENV/bin" ]; then
  echo "Installing codx-junior API for the first time at $CODX_JUNIOR_API_VENV ...will take some time."
  python3.11 -m venv $CODX_JUNIOR_API_VENV
  source ${CODX_JUNIOR_API_VENV}/bin/activate
  
  pip3 install wheel 
  
  pip3 install .  
fi


# Run the FastAPI application using uvicorn
source ${CODX_JUNIOR_API_VENV}/bin/activate

echo "codx-junior api BACKGROUND: '${CODX_JUNIOR_API_BACKGROUND}' DEBUG: '${DEBUG}'"

API_PORT=$CODX_JUNIOR_API_PORT
if [ "$CODX_JUNIOR_API_BACKGROUND" != "" ]; then
  API_PORT=$CODX_JUNIOR_API_PORT_BACKGROUND
fi

sudo chown -R $USER ${CODX_JUNIOR_CONFIG_FOLDER}
sudo chown -R $USER ${CODX_JUNIOR_PROJECTS_PATH}

if [ "$DEBUG" == "" ]; then
  uvicorn codx.junior.main:app --workers ${WEB_CONCURRENCY:-4} --host 0.0.0.0 --port $API_PORT
else
  uvicorn codx.junior.main:app --reload --host 0.0.0.0 --port $API_PORT
fi