# API virtual env
export CODX_JUNIOR_API_VENV=/tmp/.venv_codx_junior_api
# Browser virtual env
export BROWSER_VENV=/tmp/.venv_codx_junior_browser
# codx-junior API port
export CODX_JUNIOR_API_PORT=19980
# codx-junior API URL
export CODX_JUNIOR_API_URL=http://0.0.0.0:${CODX_JUNIOR_API_PORT}
# codx-junior web port
export CODX_JUNIOR_WEB_PORT=19981
# codx-junior code-server port
export CODX_JUNIOR_CODER_PORT=19982
# Desktop port
export CODX_JUNIOR_NOVNC_PORT=19983
# codx-junior API background port
export CODX_JUNIOR_API_PORT_BACKGROUND=19984
# llmfactory server port
export CODX_JUNIOR_LLMFACTORY_PORT=19985
export CODX_JUNIOR_LLMFACTORY_URL=http://0.0.0.0:${CODX_JUNIOR_LLMFACTORY_PORT}
export CODX_JUNIOR_LLMFACTORY_KNOWLEDGE_MODEL=${CODX_JUNIOR_LLMFACTORY_KNOWLEDGE_MODEL:-"qwen3:4b"}
export CODX_JUNIOR_LLMFACTORY_EMBEDDINGS_MODEL=${CODX_JUNIOR_LLMFACTORY_EMBEDDINGS_MODEL:-"nomic-embed-text"}

# codx-junior preview display
export CODX_JUNIOR_DISPLAY=:55
# Serving client from API
export CODX_SUPERVISOR_LOG_FOLDER=/var/log/codx-junior-supervisor

# Installation APPS
export CODX_JUNIOR_APPS=${CODX_JUNIOR_APPS:-"client api llm-factory docker"}

#Global settings path
export CODX_JUNIOR_GLOBAL_SETTINGS_PATH=${CODX_JUNIOR_GLOBAL_SETTINGS_PATH}

### OLLAMA
export CODX_JUNIOR_EMBEDDINGS_MODEL=nomic-embed-text

# Miscellaneous
export DEBIAN_FRONTEND=noninteractive
# Locales
export LANG=en_US.UTF-8  
export LANGUAGE=en_US:en  
export LC_ALL=en_US.UTF-8