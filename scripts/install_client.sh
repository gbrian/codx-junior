#!/bin/bash
# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"

source ${CODX_JUNIOR_PATH}/.env

codx docker
codx coder
codx nodejs
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# Copy settings.json
echo "Copying VS Code settings..."
mkdir -p ${HOME}/.local/share/code-server/Machine
cp ${CODX_JUNIOR_PATH}/code-server/User/settings.json ${HOME}/.local/share/code-server/Machine/settings.json

echo "Compiling client"
cd $CODX_JUNIOR_PATH/client
npm i
npm run build-only
