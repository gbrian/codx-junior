#!/bin/bash
# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"
echo "Starting api USER: ${USER} ($(id -u):$(id -g)) HOME: ${HOME}"
echo "Fix permissions"
sudo chown -R ${USER} ${HOME}
sudo chown ${USER} /var/run/docker.sock

source ${CODX_JUNIOR_PATH}/set_env.sh

export PYTHONPATH=${CODX_JUNIOR_PATH}/api

cd ${CODX_JUNIOR_PATH}/api


# Run the FastAPI application using uvicorn
echo "Checking venv: '${CODX_JUNIOR_API_VENV}' ..."
if [ ! -d "${CODX_JUNIOR_API_VENV}/bin" ]; then
  echo "!!! venv not found. Installing at: ${CODX_JUNIOR_API_VENV}"
  bash ${CODX_JUNIOR_PATH}/scripts/install_api.sh
else
  echo "venv found!"
fi

source ${CODX_JUNIOR_API_VENV}/bin/activate
uv sync

echo "codx-junior api BACKGROUND: '${CODX_JUNIOR_API_BACKGROUND}' DEBUG: '${DEBUG}'"

API_PORT=$CODX_JUNIOR_API_PORT
if [ "$CODX_JUNIOR_API_BACKGROUND" != "" ]; then
  API_PORT=$CODX_JUNIOR_API_PORT_BACKGROUND
fi

if [ "$DEBUG" == "" ]; then
  echo "Running PROD api"
  uvicorn codx.junior.main:app --workers ${WEB_CONCURRENCY:-8} --host 0.0.0.0 --port $API_PORT
elif [ "$CODX_JUNIOR_API_RELOAD" == "1" ] || [ "$CODX_JUNIOR_API_RELOAD" == "true" ]; then
  # Opt-in source reload for development ONLY. Never enable it when the AI
  # agents edit the project itself: every file change restarts uvicorn and
  # interrupts the in-flight chat turns (the harness would kill its own work).
  echo "Running DEBUG api with source reload"
  uvicorn codx.junior.main:app --reload --reload-exclude ".venv" --host 0.0.0.0 --port $API_PORT
else
  # DEBUG=1 only raises logging/verbosity here: the API is supervised by
  # supervisor/Docker and must not restart itself while a turn is running.
  echo "Running DEBUG api (no source reload; set CODX_JUNIOR_API_RELOAD=1 to enable)"
  uvicorn codx.junior.main:app --workers ${WEB_CONCURRENCY:-8} --host 0.0.0.0 --port $API_PORT
fi