#!/bin/bash
# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"
echo "Starting api USER: ${USER} HOME: ${HOME}"

source ${CODX_JUNIOR_PATH}/set_env.sh

export PYTHONPATH=${CODX_JUNIOR_PATH}/api
export CODX_JUNIOR_STATIC_FOLDER=${CODX_JUNIOR_PATH}/client/dist

# Run the FastAPI application using uvicorn
source ${CODX_JUNIOR_API_VENV}/bin/activate


API_PORT=$CODX_JUNIOR_API_PORT
if [ "$CODX_JUNIOR_API_BACKGROUND" != "" ]; then
  API_PORT=$CODX_JUNIOR_API_PORT_BACKGROUND
fi

export GATSBY_PREFIX_PATH_VALUE=${CODX_JUNIOR_AUTOGEN_PREFIX_PATH_VALUE}
echo "*****************************************************************
autogen studio. GATSBY_PREFIX_PATH_VALUE: '${GATSBY_PREFIX_PATH_VALUE}'"

# git clone --depth 1 --branch main https://github.com/microsoft/autogen.git $HOME/autogen
# 
# npm install -g gatsby-cli
# npm install --global yarn
# 
# cd $HOME/autogen/python/packages/autogen-studio/frontend
# 
# export NODE_ENV=development
# # ERROR: "gatsby-plugin-manifest" threw an error while running the onPostBootstrap
# # Had to remove "gatsby-plugin-manifest" :( ...ls-l
# yarn build
# 
# export PREFIX_PATH_VALUE=${CODX_JUNIOR_AUTOGEN_PREFIX_PATH_VALUE} 
# gatsby build --prefix-paths --verbose
# 
# AUTOGEN_LIB_WEB_PATH=${CODX_JUNIOR_API_VENV}/lib/python3.11/site-packages/autogenstudio/web
# 
# rm -rf ${AUTOGEN_LIB_WEB_PATH}/ui
# mkdir ${AUTOGEN_LIB_WEB_PATH}/ui
# cp -rf ./public/* ${AUTOGEN_LIB_WEB_PATH}/ui
# 
# sed -i 's|app.mount("\/", StaticFiles|app.mount("\/'$PREFIX_PATH_VALUE'", StaticFiles|' ${AUTOGEN_LIB_WEB_PATH}/app.py
# 
# cat ${AUTOGEN_LIB_WEB_PATH}/app.py | grep "$PREFIX_PATH_VALUE"
# 
# export AUTOGENSTUDIO_AUTH_DISABLED=1
autogenstudio ui --port $CODX_JUNIOR_AUTOGEN_STUDIO_PORT