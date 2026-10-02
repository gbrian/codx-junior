# Global Settings Documentation

The system utilizes a centralized configuration management system to handle AI models, providers, and general environment settings.

## Configuration Path and Storage
The configuration is stored in a JSON file defined by the `CODX_JUNIOR_CONFIG_FOLDER` environment variable, defaulting to the system `HOME` directory.
- **File Path**: `${CODX_JUNIOR_CONFIG_FOLDER}/global_settings.json`
- **Persistence**: Configuration is automatically read on initialization and can be persisted via `write_global_settings`.

### Backup Mechanism
To ensure data integrity, the system implements a backup routine in `backup_up_global_settings`:
- Backups are stored in `codx-junior-backup` within the config directory.
- Files are timestamped (e.g., `global_settings_backup_YYYYMMDD_HHMMSS.json`).
- The system automatically maintains only the 20 most recent backup files, deleting older entries.

## AI Configuration Management

### AI Providers
Providers are managed via `get_provider_settings`. This function supports environment variable expansion for `api_url` and `api_key` using `os.path.expandvars`, allowing for secure credential handling.

### AI Models
Models are retrieved using `get_model` and saved using `save_model`. The system identifies models by either their `name` or `ai_model` identifier.

### Pricing Resolution
The `_resolve_model_price` function determines token costs (input/output per 1k tokens) using a hierarchical priority:
1. **Provider Price List**: Checks the provider's `price_list` for an entry matching the `model_id`.
2. **Provider Defaults**: Fallback to the provider-level `input_k_tokens_cxjcoins` and `output_k_tokens_cxjcoins`.

## Integration Settings
- **Git Integration**: When `write_global_settings` is called, the system synchronizes local Git configurations if `username` or `email` are provided in the settings. It executes:
  - `git config --global user.name`
  - `git config --global user.email`
- **OAuth**: Providers can be queried via `get_oauth_provider` by name.

## Helper Functions
- `get_global_settings()`: Accesses the currently loaded global configuration object.
- `get_model_settings(llm_model)`: Aggregates model parameters, provider API credentials, and resolved pricing into an `AISettings` object for runtime usage.

---
### References
- *File: /codx/junior/global_settings.py*
- `backup_up_global_settings()` - Backup logic and rotation.
- `write_global_settings()` - Persistence and Git synchronization.
- `_resolve_model_price()` - Pricing resolution hierarchy.
- `get_provider_settings()` - Provider retrieval and variable expansion.

## Dependencies
**Imports from:** codx/junior/utils/utils.py, codx/junior/model/model.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/api/analytics.py, codx/junior/api/users.py, codx/junior/api/workspaces.py, codx/junior/app.py, codx/junior/background.py, codx/junior/plugins/plugin_manager.py, codx/junior/project/project_discover.py, codx/junior/security/user_management.py, codx/junior/settings.py, codx/junior/workspace/workspace_manager.py