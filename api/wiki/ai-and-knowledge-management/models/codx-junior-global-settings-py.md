# Global Settings Management

This module handles the persistence, loading, and retrieval of global application settings, including configurations for AI models, API providers, and general system settings.

## Core Concepts

The primary configuration structure is managed by `GlobalSettings`. This configuration includes various components:

*   **AI Models (`ai_models`):** Definitions of supported Large Language Models (LLMs).
*   **API Providers (`ai_providers`):** Credentials and endpoints for external AI services.
*   **OAuth Providers (`oauth_providers`):** Settings for OAuth authentication providers.
*   **Git User Info:** Configuration for git username and email.

### Paths and Storage

Global settings are stored in a JSON file located at:
*   `GLOBAL_SETTINGS_FOLDER`: Defaults to the `HOME` environment variable, or can be set via `CODX_JUNIOR_CONFIG_FOLDER`.
*   `GLOBAL_SETTINGS_PATH`: The full path to the configuration file (`{GLOBAL_SETTINGS_FOLDER}/global_settings.json`).

## Function Reference

### Settings Persistence and Initialization

#### `read_global_settings()`
This function attempts to load the global settings from the configured JSON path (`GLOBAL_SETTINGS_PATH`).

*   If successful, it deserializes the data into a `GlobalSettings` object and stores it globally.
*   If an error occurs during loading, it logs the error, initializes a default empty `GlobalSettings` instance, and writes that default structure back to the file upon execution (Section: `read_global_settings`).

#### `write_global_settings(global_settings: GlobalSettings)`
Saves the provided `GlobalSettings` object to the global settings file.

*   **Steps:**
    1.  Serializes the `GlobalSettings` dictionary.
    2.  Calls `backup_up_global_settings()` before saving.
    3.  Writes the data to `GLOBAL_SETTINGS_PATH`.
    4.  If Git username and email are specified, it executes git commands (`git config --global user.name`, etc.) using the system command utility (Section: `write_global_settings`).

#### `backup_up_global_settings()`
Handles the creation of a backup copy of the current global settings file before writing new settings.

*   **Mechanism:** Creates a directory named `codx-junior-backup` in the parent directory of `GLOBAL_SETTINGS_PATH`.
*   **Naming:** Backup files are timestamped (e.g., `global_settings_backup_YYYYMMDD_HHMMSS.json`).
*   **Cleanup:** It automatically removes historical backups, ensuring that only the last 20 backups are retained (Section: `backup_up_global_settings`).

### Configuration Retrieval Utilities

#### `get_provider_settings(ai_provider: str, global_settings = None)`
Retrieves a specific AI API provider's configured settings.

*   **Input:** The name of the AI provider (`ai_provider`) and optional `global_settings`.
*   **Output:** An initialized `AIProvider` object.
*   **Process:** Finds the matching provider by name within the `GlobalSettings` object, expands environment variables in API URLs and keys, and returns the instance (Section: `get_provider_settings`).

#### `get_model(llm_model: str, global_settings = None)`
Retrieves a specific AI Model's configuration.

*   **Input:** The name or model ID of the LLM (`llm_model`) and optional `global_settings`.
*   **Output:** An initialized `AIModel` object.
*   **Process:** Searches through `GlobalSettings.ai_models` matching either the `name` or `ai_model` attribute (Section: `get_model`).

#### `get_oauth_provider(oauth_provider: str)`
Retrieves a specific OAuth authentication provider configuration.

*   **Input:** The name of the oauth provider (`oauth_provider`).
*   **Output:** An initialized structure matching the `OAuthProvider` definition, or `None`.
*   **Process:** Searches through `GlobalSettings.oauth_providers` (Section: `get_oauth_provider`).

#### `get_model_settings(llm_model: str, global_settings = None)`
Retrieves a comprehensive set of operational settings required to run an LLM model instance.

*   **Input:** The model name (`llm_model`) and optional `global_settings`.
*   **Output:** An initialized `AISettings` object containing resolved credentials, cost data, system prompts, etc.
*   **Process:**
    1.  Retrieves the raw `AIModel` (using `get_model`).
    2.  Retrieves the corresponding `APIProvider` (using `get_provider_settings`).
    3.  Calculates pricing using `_resolve_model_price`.
    4.  Assembles all details, including expanded environment variables and resolved costs, into a single `AISettings` object (Section: `get_model_settings`).

#### `save_model(model: AIModel, global_settings = None)`
Updates the current global settings configuration by ensuring a specific model is listed.

*   **Input:** The `AIModel` instance to be saved and optional `global_settings`.
*   **Action:** It updates the list of models in `GlobalSettings`, replacing an existing entry if it has the same name, or adding the new model (Section: `save_model`).

### Pricing Resolution

#### `_resolve_model_price(model: AIModel, provider: AIProvider)`
A private utility function responsible for determining the specific cost per 1k input and output tokens. It follows a strict priority order:

1.  **Provider Price List Match:** Checks if the provider's attached `price_list` contains an entry matching the model ID (highest priority).
2.  **Fallback to Provider Defaults:** If no specific list match is found, it uses the default input and output token costs set on the entire `AIProvider` object (lowest priority) (Section: `_resolve_model_price`).

## Dependencies
**Imports from:** codx/junior/utils/utils.py, codx/junior/model/model.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/api/analytics.py, codx/junior/api/users.py, codx/junior/api/workspaces.py, codx/junior/app.py, codx/junior/background.py, codx/junior/plugins/plugin_manager.py, codx/junior/project/project_discover.py, codx/junior/security/user_management.py, codx/junior/settings.py, codx/junior/workspace/workspace_manager.py