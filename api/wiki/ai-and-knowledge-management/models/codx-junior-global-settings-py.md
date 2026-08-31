# Global Settings Module Documentation

## Overview

The Global Settings module provides comprehensive read/write access to application-wide configuration through a `GlobalSettingsManager`. It manages settings in separate section files while maintaining version history and supporting legacy single-file migration.

## Core Features

### Settings Management
- **Sectioned Storage**: Each settings field is stored as an independent section file
- **Version History**: Manager maintains historical versions of configuration changes
- **Legacy Migration**: Automatic migration from single-file to sectioned format
- **In-Memory Cache**: Global singleton instance for efficient access

### Key Components

#### Manager Singleton
```
get_manager() → GlobalSettingsManager
```
Returns the singleton instance of `GlobalSettingsManager` for centralized settings management.

#### Primary Operations

**Reading Settings**
```
read_global_settings() → GlobalSettings
```
Assembles all section files into a complete `GlobalSettings` instance. Falls back to defaults for missing sections.

**Writing Settings**
```
write_global_settings(global_settings: GlobalSettings) → None
```
Persists all settings by writing each field as a separate section file. Applies git configuration side effects when credentials are present.

**Updating Single Section**
```
write_settings_section(section: str, data: any) → None
```
Writes a single settings section without affecting others. Automatically refreshes the in-memory instance.

**Retrieving Cached Settings**
```
get_global_settings() → Optional[GlobalSettings]
```
Returns the current in-memory settings instance (loaded during module initialization).

## AI Configuration Helpers

### Provider Management
```
get_provider_settings(ai_provider: str, global_settings: Optional[GlobalSettings] = None) → AIProvider
```
Retrieves provider configuration by name with environment variables expanded. Raises `ValueError` if provider not found.

### Model Management
```
get_model(llm_model: str, global_settings: Optional[GlobalSettings] = None) → Optional[AIModel]
```
Finds a model by name or `ai_model` identifier.

```
save_model(model: AIModel) → None
```
Upserts an `AIModel` into the `ai_models` section.

### Advanced Model Resolution
```
get_model_settings(llm_model: str, global_settings: Optional[GlobalSettings] = None) → AISettings
```
Builds a fully-resolved `AISettings` object with the following resolution priorities:

**Pricing Resolution**
1. Model-specific pricing
2. Provider's price_list entry matching model identifier
3. Provider-level default pricing
4. None

**Tool Limits Resolution**
1. Model-level limits (if set)
2. Provider-level limits (if set)
3. None (no limit)

Raises `ValueError` if model or provider not found.

### Internal Resolution Functions
```
_resolve_model_price(model: AIModel, provider: AIProvider)
```
Determines token pricing based on model and provider hierarchy.

```
_resolve_tool_limits(model: AIModel, provider: AIProvider) → tuple
```
Resolves `max_tool_calls` and `max_iterations` with model-level priority over provider-level settings.

## OAuth Configuration
```
get_oauth_provider(oauth_provider: str)
```
Retrieves OAuth provider configuration by name.

## Git Configuration

### Git Config Application
```
_apply_git_config(global_settings: GlobalSettings) → None
```
Applies git username and email from settings to global git configuration. Executed automatically when settings are written.

## Migration System

### Legacy Settings Migration
```
_migrate_legacy_settings() → None
```
Automatically migrates legacy single-file format (`global_settings.json`) to sectioned storage on first run. Skips if section files already exist. Preserves the original legacy file as backup.

**Migration Conditions**
- Only runs if legacy file exists at `GLOBAL_SETTINGS_PATH`
- Skips if section files already exist (migration already completed)
- Preserves original file for safety

## Configuration Paths

- **Home Directory**: `$HOME` environment variable (default: `/root`)
- **Settings Directory**: `$CODX_JUNIOR_CONFIG_FOLDER` environment variable (default: home directory)
- **Legacy File Path**: `{GLOBAL_SETTINGS_FOLDER}/global_settings.json`

## Initialization

The module automatically:
1. Migrates legacy settings if needed
2. Loads settings into memory via `read_global_settings()`
3. Maintains singleton manager instance for subsequent operations

All operations work with the cached `GLOBAL_SETTINGS` instance, which is refreshed after any write operation.

## Dependencies
**Imports from:** codx/junior/utils/utils.py, codx/junior/model/model.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/api/analytics.py, codx/junior/api/users.py, codx/junior/api/workspaces.py, codx/junior/app.py, codx/junior/background.py, codx/junior/plugins/plugin_manager.py, codx/junior/project/project_discover.py, codx/junior/security/user_management.py, codx/junior/settings.py, codx/junior/workspace/workspace_manager.py