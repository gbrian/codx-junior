#!/bin/bash
# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"

source ${CODX_JUNIOR_PATH}/.env

cd $CODX_JUNIOR_PATH/client
npm i
npm run build-only
