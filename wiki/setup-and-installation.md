# Setup and Installation: codx-junior API

This guide details the automated installation process for the `codx-junior` API environment and the relevant environment configurations based on project variables. It outlines how core paths, system context, service endpoints, and infrastructure parameters are defined and utilized.

## Overview
The setup script manages environment configuration, **image building**, Docker initialization, and the creation of a Python virtual environment to manage dependencies. Configuration relies heavily on sourcing exported variables which set global paths, service URLs, and infrastructure settings, enabling smooth deployment via services like Traefik as a reverse proxy for traffic management.

## Environment Variables (Configuration Definitions)
The following environment variables define core operational settings, default paths, ports, models, and services across the codx-junior ecosystem, derived from the export script configuration.

### Core Paths & Global Settings
| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `CODX_JUNIOR_PROJECTS_PATH` | Root folder for new projects. | `/home/codx-junior-projects` |
| `CODX_JUNIOR_API_VENV` | API virtual environment path. | `/tmp/.venv_codx_junior_api` |
| `BROWSER_VENV` | Browser virtual environment path. | `/tmp/.venv_codx_junior_browser` |
| `CODX_JUNIOR_API_LOGS` | API logs directory. | `/tmp/codx-junior-logs` |
| `CODX_SUPERVISOR_LOG_FOLDER` | Supervisor log folder location. | `/var/log/codx-junior-supervisor` |
| `CODX_JUNIOR_CONFIG_FOLDER` | Global application state settings path. | `/home/codx-junior/codx-junior-global-settings.json` |
| `CODX_JUNIOR_WORKSPACES_FOLDER` | Folder for predefined workspaces. | `${CODX_JUNIOR_CONFIG_FOLDER}/workspaces` |
| `CODX_JUNIOR_DEFAULT_WORKSPACE_PATH` | Path for workspace templates. | `/home/codx-junior-projects/codx-junior/workspace-templates` |
| `CODX_JUNIOR_API_ANALYTICS_DATA_PATH` | General path for all analytics data storage. | `/home/codx-junior/analytics` |
| `CODX_JUNIOR_AI_RAW_LOG_PATH` | Dedicated chat logs directory. | `/home/codx-junior/analytics/chats` |
| `CODX_JUNIOR_STATIC_FOLDER` | Folder for static client assets. | `~/codx-junior-static` |

### Ports, Endpoints, and Services
| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `CODX_JUNIOR_API_PORT` | Primary API container port. | `19980` |
| `CODX_JUNIOR_API_URL` | Full primary API endpoint URL. | `http://0.0.0.0:${CODX_JUNIOR_API_PORT}` |
| `CODX_JUNIOR_WEB_PORT` | Web Interface port. | `19981` |
| `CODX_JUNIOR_API_PORT_BACKGROUND` | Secondary background API port. | `19984` |
| `USER_PORT_RANGE_START` | Start of the reserved user allocated port range. | `99000` |
| `USER_PORT_RANGE_END` | End of the reserved user allocated port range. | `99050` |
| `CODX_JUNIOR_LLMFACTORY_URL` | LLM Factory service URL. | `http://litellm-codx-junior:4000/v1` |
| `CODX_JUNIOR_LLMFACTORY_KEY` | LLM Factory API key. | `${LITELLM_MASTER_KEY}` |
| `CODX_JUNIOR_MILVUS_UI_URL` | Milvus Vector DB UI connection URL. | `http://milvus-codx-junior:9091` |
| `CODX_JUNIOR_MILVUS_URL` | Primary Milvus Vector DB connection URL. | `http://milvus-codx-junior:19530` |

### Model Configurations & Runtime Settings
| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `CODX_JUNIOR_LLMFACTORY_KNOWLEDGE_MODEL` | Default LLM knowledge model. | `"ollama/phi4"` |
| `CODX_JUNIOR_LLMFACTORY_EMBEDDINGS_MODEL` | Default embeddings model name. | `"nomic-embed-text"` |
| `VLLM_TARGET_DEVICE` | Global device target for VLLM services. | `CPU` |
| `CODX_JUNIOR_DISPLAY` | Preview display identifier. | `:55` |
| `CODX_JUNIOR_APPS` | Installation applications list. | `"client api"` |

### System Context Variables
*   **System Locale**: The system uses English UTF-8:
    *   `LANG`, `LC_ALL` = `en_US.UTF-8`
    *   `LANGUAGE` = `en_US:en`
*   **Interactive Frontend**: The setup disables the Debian frontend using `DEBIAN_FRONTEND=noninteractive`.

## Installation Steps

### 1. Environment Configuration
The setup process requires sourcing export variables. The script dynamically establishes paths for project roots, virtual environments, and logging/data folders by prioritizing existing environment variables or falling back to defined default values.

### 2. Traffic Management (Traefik)
The system uses Traefik as a reverse proxy managing web traffic via configured ports (`CODX_JUNIOR_WEB_PORT` and `CODX_JUNIOR_API_PORT`).

### 3. Image Building and Docker Initialization
Builds are performed using `docker-compose` for defined infrastructure components.

### 4. API Environment Setup
The system manages the Python virtual environment at `$CODX_JUNIOR_API_VENV`.
*   **First-time Installation**: If the directory is missing, it initializes via `python3.11 -m venv`. The environment is then configured to target `VLLM_TARGET_DEVICE=CPU`.

### 5. Global Configuration Integration
Upon setup, the system populates the `CODX_JUNIOR_CONFIG_FOLDER` to manage application state, including:
*   **Workspaces**: Defined at `$CODX_JUNIOR_WORKSPACES_FOLDER` using templates from `$CODX_JUNIOR_DEFAULT_WORKSPACE_PATH` (containing Dockerfile, docker-compose.yaml, and .env files).
*   **Analytics**: Data is managed via paths defined in `$CODX_JUNIOR_API_ANALYTICS_DATA_PATH` and `$CODX_JUNIOR_AI_RAW_LOG_PATH`.

---
### Reference
*   **Project**: codx-junior
*   **Source Data**: [Environment Variable Definitions](https://github.com/codx-junior/setup-guide)

[Link to Source Documentation](https://github.com/codx-junior/setup-guide)