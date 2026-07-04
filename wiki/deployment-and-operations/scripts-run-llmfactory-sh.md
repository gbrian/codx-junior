# Deployment and Operations: llmFactory Service

## Overview
The `run_llmFactory.sh` script is responsible for initializing and starting the llmFactory service within the `codx-junior` project. It handles environment configuration, dependency activation, and local model path management.

## Script Functionality
The script performs the following operations during execution:

*   **Environment Initialization:** It dynamically determines the project root path (`CODX_JUNIOR_PATH`) based on the script's location and sources the necessary environment variables from `set_env.sh`.
*   **API Preparation:** It navigates to the project API directory and activates the virtual environment defined by `CODX_JUNIOR_API_VENV`.
*   **Model Management:**
    *   Checks if the `OLLAMA_MODELS` variable is set.
    *   If not set, it defaults the storage directory to `${CODX_JUNIOR_PATH}/ollama_models` and ensures the directory is created.
*   **Service Startup:**
    *   Configures the `OLLAMA_HOST` to listen on `0.0.0.0` using the port specified in `CODX_JUNIOR_LLMFACTORY_PORT` (defaulting to `11434`).
    *   Executes the `ollama serve` command to start the service.

## Operational Requirements
*   The script requires the project environment to be configured via the `set_env.sh` script located in the project root.
*   The system expects `OLLAMA_MODELS` to be managed; if not provided by the system environment, the script will automatically create a directory in the project path.
*   The service runs on the port defined by the `CODX_JUNIOR_LLMFACTORY_PORT` variable.

## References
*   Project: `codx-junior`
*   Category: Deployment and Operations