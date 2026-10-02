#!/bin/bash
# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"

source ${CODX_JUNIOR_PATH}/set_env.sh

codx nodejs

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

echo "Compiling client"
cd ${CODX_JUNIOR_PATH}/client

# NASTY: Prevents issues when mapping codx-junior folder :( ...to be removed someday 
rm -rf node_modules
rm -rf dist

# v25 requires extra dependencies on Debian/Ubuntu
nvm install v24.12.0

npm i
npm run build-only
