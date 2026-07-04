# Deployment and Operations: llmFactory Service

## Overview
The `run_llmFactory.sh` script is responsible for initializing and launching the llmFactory service within the `codx-junior` project. It automates environment configuration, virtual environment activation, and the startup of the Ollama server.

## Initialization Process
The script performs the following operations during startup:

1.  **Path Definition**: Automatically sets `CODX_JUNIOR_PATH` to the parent directory of the script's location.
2.  **Environment Setup**: Sources the `set_env.sh` file to load necessary project configurations.
3.  **Virtual Environment**: Navigates to the `/api` directory and activates the virtual environment defined by `CODX_JUNIOR_API_VENV`.
4.  **Logging**: Outputs the `CODX_JUNIOR_PATH`, current user, and home directory for maintenance and troubleshooting.

## Ollama Configuration
The script configures the local LLM runtime (Ollama) with the following logic:

*   **Model Storage**: If the `OLLAMA_MODELS` environment variable is not set, it defaults to `${CODX_JUNIOR_PATH}/ollama_models` and ensures the directory is created.
*   **Host Settings**: Sets `OLLAMA_HOST` to `0.0.0.0` using the port specified in `CODX_JUNIOR_LLMFACTORY_PORT` (defaulting to `11434` if not defined).
*   **Service Startup**: Launches the Ollama service using `ollama serve`.

## Maintenance
*   **Category**: Deployment and Operations
*   **Keywords**: deployment, operations, scripts, maintenance

---
### References
*   [Document: codx-junior /scripts/run_llmFactory.sh]