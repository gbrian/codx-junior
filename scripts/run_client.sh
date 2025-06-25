#!/bin/bash
# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
source ${CODX_JUNIOR_PATH}/set_env.sh

echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"
echo "Starting client USER: ${USER} HOME: ${HOME}"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

cd ${CODX_JUNIOR_PATH}/client

if [ "$DEBUG" != "" ]; then
  echo "*********** codx-junior client DEBUG ************"
  npm install
  npm run dev
else
  echo "*********** codx-junior client PRODUCTION ************"
  npm run preview
fi