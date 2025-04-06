# API virtual env
export CODX_JUNIOR_API_VENV=/tmp/.venv_codx_junior_api
# Browser virtual env
export BROWSER_VENV=/tmp/.venv_codx_junior_browser
# codx-junior API port
if [ -z "$CODX_JUNIOR_API_PORT" ];then 
  export CODX_JUNIOR_API_PORT=19980
fi
# codx-junior API URL
if [ -z "$CODX_JUNIOR_API_URL" ]; then
  export CODX_JUNIOR_API_URL=http://0.0.0.0:${CODX_JUNIOR_API_PORT}
fi
# codx-junior web port
if [ -z "$CODX_JUNIOR_WEB_PORT" ]; then
  export CODX_JUNIOR_WEB_PORT=19981
fi
# codx-junior code-server port
if [ -z "$CODX_JUNIOR_CODER_PORT" ]; then
  export CODX_JUNIOR_CODER_PORT=19982
fi
# Desktop port
if [ -z "$CODX_JUNIOR_NOVNC_PORT" ]; then
  export CODX_JUNIOR_NOVNC_PORT=19983
fi
# codx-junior API background port
if [ -z "$CODX_JUNIOR_API_PORT_BACKGROUND" ]; then
  export CODX_JUNIOR_API_PORT_BACKGROUND=19984
fi
# llmfactory server port
if [ -z "$CODX_JUNIOR_LLMFACTORY_PORT" ]; then
  export CODX_JUNIOR_LLMFACTORY_PORT=19985
fi
if [ -z "$CODX_JUNIOR_LLMFACTORY_URL" ]; then
  export CODX_JUNIOR_LLMFACTORY_URL=http://0.0.0.0:${CODX_JUNIOR_LLMFACTORY_PORT}
fi
# codx-junior preview display
if [ -z "$CODX_JUNIOR_DISPLAY" ]; then
  export CODX_JUNIOR_DISPLAY=:55
fi
# Serving client from API
if [ -z "$CODX_SUPERVISOR_LOG_FOLDER" ]; then
  export CODX_SUPERVISOR_LOG_FOLDER=/var/log/codx-junior-supervisor
fi

### OLLAMA
if [ -z "$CODX_JUNIOR_EMBEDDINGS_MODEL" ]; then
  export CODX_JUNIOR_EMBEDDINGS_MODEL=nomic-embed-text
fi

# Miscellaneous
export DEBIAN_FRONTEND=noninteractive
# Locales
export LANG=en_US.UTF-8  
export LANGUAGE=en_US:en  
export LC_ALL=en_US.UTF-8