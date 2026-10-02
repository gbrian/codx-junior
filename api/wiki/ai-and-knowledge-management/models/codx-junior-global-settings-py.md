# Global Settings Module Documentation

## Overview

The global settings module provides read/write access to `GlobalSettings` using `GlobalSettingsManager`, which stores each section independently and maintains version history. This module handles both current sectioned storage and legacy single-file migration.

## Core Components

### Global State

- **GLOBAL_SETTINGS**: An optional in-memory cache of the current `GlobalSettings` instance
- **_manager**: A singleton instance of `GlobalSettingsManager` for persistent storage operations

### Manager Access

```python
get_manager() -> GlobalSettingsManager
```

Returns the singleton `GlobalSettingsManager` instance, initializing it on first use.

## Configuration Paths

- **HOME**: User home directory (defaults to `/root`)
- **GLOBAL_SETTINGS_FOLDER**: Configuration folder location (defaults to HOME, overridable via `CODX_JUNIOR_CONFIG_FOLDER` environment variable)
- **GLOBAL_SETTINGS_PATH**: Legacy single-file path for backward compatibility

## Legacy Settings Migration

### Automatic Migration

The module automatically migrates legacy `global_settings.json` files to sectioned storage:

```python
_migrate_legacy_settings() -> None
```

**Migration process:**
- Checks if legacy `global_settings.json` exists
- Skips if section files already exist (migration already complete)
- Splits legacy data into individual section files
- Preserves the original file as a backup
- Logs errors if migration fails

Migration runs automatically on module initialization.

## Core Read/Write Operations

### Reading Settings

```python
read_global_settings() -> GlobalSettings
```

Assembles all section files via the manager into a complete `GlobalSettings` instance. Falls back to defaults for any missing sections. Caches the result in the global `GLOBAL_SETTINGS` variable.

### Writing Settings

```python
write_global_settings(global_settings: GlobalSettings) -> None
```

Persists all `GlobalSettings` fields by writing each as its own section file. Also applies git configuration side effects when git credentials are present.

### Partial Section Updates

```python
write_settings_section(section: str, data: any) -> None
```

Updates a single section of `GlobalSettings` without affecting other sections. Automatically refreshes the in-memory cache after the partial update.

### Accessing In-Memory Settings

```python
get_global_settings() -> Optional[GlobalSettings]
```

Returns the current in-memory `GlobalSettings` instance, or `None` if not yet loaded.

## AI Provider and Model Management

### Provider Settings

```python
get_provider_settings(ai_provider: str, global_settings: Optional[GlobalSettings] = None) -> AIProvider
```

Retrieves an `AIProvider` by name with environment variables expanded in `api_url` and `api_key` fields.

**Raises:** `ValueError` if the provider is not found.

### Model Lookup

```python
get_model(llm_model: str, global_settings: Optional[GlobalSettings] = None) -> Optional[AIModel]
```

Finds an `AIModel` by name or `ai_model` identifier. Returns `None` if not found.

### Model Persistence

```python
save_model(model: AIModel) -> None
```

Inserts or updates an `AIModel` in the `ai_models` section. Replaces existing models with the same name.

### Complete Model Settings

```python
get_model_settings(llm_model: str, global_settings: Optional[GlobalSettings] = None) -> AISettings
```

Builds a fully-resolved `AISettings` object for a given model with:

**Pricing Resolution Priority:**
1. Model-level pricing
2. Provider's price_list entry matching the model
3. Provider-level default pricing
4. None

**Tool Limits Resolution Priority:**
1. Model-level `max_tool_calls`/`max_iterations`
2. Provider-level `max_tool_calls`/`max_iterations`
3. None (no limit)

**Raises:** `ValueError` if the model or provider is not found.

### Helper Functions

#### Price Resolution

```python
_resolve_model_price(model: AIModel, provider: AIProvider)
```

Returns a tuple of `(input_price_per_1k, output_price_per_1k)` using the priority system described above.

#### Tool Limits Resolution

```python
_resolve_tool_limits(model: AIModel, provider: AIProvider) -> tuple
```

Returns a tuple of `(max_tool_calls, max_iterations)` using the priority system described above.

## OAuth Provider Management

```python
get_oauth_provider(oauth_provider: str)
```

Retrieves an OAuth provider configuration by name. Returns `None` if not found.

## Git Configuration

### Git Config Application

```python
_apply_git_config(global_settings: GlobalSettings) -> None
```

Applies git username and email from settings to the global git configuration using the `git config --global` command. Only applies values that are configured in settings.

This function is automatically called whenever `write_global_settings()` is executed.

## Initialization Sequence

On module load, the following operations execute automatically:
1. Legacy settings migration (if applicable)
2. Initial read of global settings into memory

## Dependencies
**Imports from:** codx/junior/utils/utils.py, codx/junior/model/model.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/api/analytics.py, codx/junior/api/users.py, codx/junior/api/workspaces.py, codx/junior/app.py, codx/junior/background.py, codx/junior/plugins/plugin_manager.py, codx/junior/project/project_discover.py, codx/junior/security/user_management.py, codx/junior/settings.py, codx/junior/workspace/workspace_manager.py