# Root folder for new projects
export CODX_JUNIOR_PROJECTS_PATH=${CODX_JUNIOR_PROJECTS_PATH:-/home/codx-junior-projects}
# API virtual env
export CODX_JUNIOR_API_VENV=${CODX_JUNIOR_API_VENV:-/tmp/.venv_codx_junior_api}
# Logs
export CODX_JUNIOR_API_LOGS=${CODX_JUNIOR_API_LOGS:-/tmp/codx-junior-logs}
# Browser virtual env
export BROWSER_VENV=/tmp/.venv_codx_junior_browser
# codx-junior API port
export CODX_JUNIOR_API_PORT=${CODX_JUNIOR_API_PORT:-19980}
# codx-junior API URL
export CODX_JUNIOR_API_URL=${CODX_JUNIOR_API_URL:-http://0.0.0.0:${CODX_JUNIOR_API_PORT}}
# codx-junior web port
export CODX_JUNIOR_WEB_PORT=${CODX_JUNIOR_WEB_PORT:-19981}
# codx-junior API background port
export CODX_JUNIOR_API_PORT_BACKGROUND=${CODX_JUNIOR_API_PORT_BACKGROUND:-19984}

export CODX_JUNIOR_STATIC_FOLDER=${CODX_JUNIOR_STATIC_FOLDER:-~/codx-junior-static}

# llmfactory server port
export CODX_JUNIOR_LLMFACTORY_URL=http://litellm-codx-junior:4000/v1
export CODX_JUNIOR_LLMFACTORY_KEY=${LITELLM_MASTER_KEY}

export CODX_JUNIOR_LLMFACTORY_KNOWLEDGE_MODEL=${CODX_JUNIOR_LLMFACTORY_KNOWLEDGE_MODEL:-"ollama/phi4"}
export CODX_JUNIOR_LLMFACTORY_EMBEDDINGS_MODEL=${CODX_JUNIOR_LLMFACTORY_EMBEDDINGS_MODEL:-"nomic-embed-text"}

# milvus vector DB
export CODX_JUNIOR_MILVUS_UI_URL=${CODX_JUNIOR_MILVUS_UI_URL:-"http://milvus-codx-junior:9091"}
export CODX_JUNIOR_MILVUS_URL=${CODX_JUNIOR_MILVUS_URL:-"http://milvus-codx-junior:19530"}

# User codxspaces and apps base port
export USER_PORT_RANGE_START=${USER_PORT_RANGE_START:-99000}
export USER_PORT_RANGE_END=${USER_PORT_RANGE_END:-99050}

# codx-junior preview display
export CODX_JUNIOR_DISPLAY=:55
# Serving client from API
export CODX_SUPERVISOR_LOG_FOLDER=/var/log/codx-junior-supervisor

# Installation APPS
export CODX_JUNIOR_APPS=${CODX_JUNIOR_APPS:-"client api"}

#Global settings path
export CODX_JUNIOR_CONFIG_FOLDER=${CODX_JUNIOR_CONFIG_FOLDER:-/home/codx-junior/codx-junior-global-settings.json}

# Workspaces
export CODX_JUNIOR_WORKSPACES_FOLDER=${CODX_JUNIOR_CONFIG_FOLDER}/workspaces

# Analytics
export CODX_JUNIOR_API_ANALYTICS_DATA_PATH=${CODX_JUNIOR_API_ANALYTICS_DATA_PATH:-/home/codx-junior/analytics}

# Chat logs
export CODX_JUNIOR_AI_RAW_LOG_PATH=${CODX_JUNIOR_AI_RAW_LOG_PATH:-/home/codx-junior/analytics/chats}

# Miscellaneous
export DEBIAN_FRONTEND=noninteractive
# Locales
export LANG=en_US.UTF-8  
export LANGUAGE=en_US:en  
export LC_ALL=en_US.UTF-8