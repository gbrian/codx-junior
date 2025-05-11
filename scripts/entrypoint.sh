#!/bin/bash
# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"

su $USER -

source ${CODX_JUNIOR_PATH}/set_env.sh

bash ${CODX_JUNIOR_PATH}/scripts/logo.sh

if [ ! -f ${CODX_JUNIOR_PATH}/codx-junior.installed ]; then
  bash ${CODX_JUNIOR_PATH}/codx-junior install
  touch ${CODX_JUNIOR_PATH}/codx-junior.installed
fi

if [ "$CODX_APPS" != "" ]; then
  for app in ${CODX_APPS//,/ }
  do
    echo "Installing codx app: $app"
    codx $app
  done
fi

#bash ${CODX_JUNIOR_PATH}/codx-junior supervisor

while true; do
  sleep 10
done
