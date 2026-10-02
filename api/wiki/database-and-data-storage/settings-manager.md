# GlobalSettingsManager

## Overview

GlobalSettingsManager is a comprehensive settings management system that handles reading, writing, and version control of application settings. Settings are organized into independent sections, with each section stored as a separate JSON file and maintaining its own version history.

## Architecture

### Directory Structure

Settings are organized in the following directory hierarchy:

```
<config_folder>/
├── settings/
│   ├── section1.json
│   ├── section2.json
│   └── ...
└── history/
    ├── section1/
    │   ├── 20240115_143022_123456.json
    │   └── ...
    └── section2/
        └── ...
```

- **Settings Directory**: Contains the current state of each section as individual JSON files
- **History Directory**: Maintains version snapshots organized by section, with timestamps in the format `YYYYMMdd_HHMMSS_microseconds`

### Configuration

The manager's config folder defaults to the following priority:

1. Explicitly provided `config_folder` parameter
2. `CODX_JUNIOR_CONFIG_FOLDER` environment variable
3. User's home directory

## Core Functionality

### Reading Settings

#### `read_section(section, model_class, default=None)`

Reads and deserializes a settings section into a Pydantic model.

**Parameters:**
- `section`: Name of the section (matches GlobalSettings field name)
- `model_class`: Pydantic model class for deserialization
- `default`: Default instance if file is missing or corrupt (optional)

**Returns:** Deserialized model instance

**Behavior:**
- Returns default or empty model instance if section file doesn't exist
- Handles JSON deserialization errors gracefully with logging

#### `read_section_raw(section)`

Reads a section as raw Python data without model conversion.

**Returns:** Parsed JSON data (dict, list, or scalar) or None if file not found

#### `read_all()`

Reads all available section files at once.

**Returns:** Dictionary mapping section names to their raw parsed data

### Writing Settings

#### `write_section(section, data)`

Serializes and persists a settings section with automatic backup and validation.

**Parameters:**
- `section`: Name of the section
- `data`: Data to persist (Pydantic model, dict, list, or scalar)

**Process:**
1. Validates data against registered schema (if available)
2. Creates backup of previous version
3. Writes new data to section file
4. Prunes history if it exceeds maximum entries

**Raises:** `ValidationError` if data fails schema validation

## Version Control

### History Management

#### `list_history(section)`

Lists all available version snapshots for a section.

**Returns:** List of `SectionVersion` objects ordered from newest to oldest

**SectionVersion Structure:**
- `section`: Section name
- `timestamp`: Timestamp string of the version
- `file_path`: Absolute path to the version file

#### `get_version(section, timestamp)`

Retrieves the raw content of a specific version snapshot.

**Parameters:**
- `section`: Section name
- `timestamp`: Timestamp string from history

**Returns:** Parsed JSON data of the snapshot or None if not found

#### `rollback(section, timestamp)`

Restores a section to a previous historical version.

**Process:**
1. Retrieves the specified version
2. Backs up current state
3. Restores the historical version as the current state

**Returns:** True if successful, False if version not found

### History Pruning

The manager automatically maintains version history with these constraints:

- **Maximum entries per section:** 50 (configurable via `MAX_HISTORY_ENTRIES`)
- **Pruning strategy:** Removes oldest entries when limit exceeded
- **Timing:** Occurs after each new backup creation

## Validation System

### Registering Validators

#### `register_section_validator(section, model_class)`

Registers a Pydantic model class as the validator for a section.

**Parameters:**
- `section`: Section name (must match GlobalSettings field name)
- `model_class`: Pydantic BaseModel class

#### `register_section_validators(validators)`

Registers multiple validators at once.

**Parameters:**
- `validators`: Dictionary mapping section names to model classes

### Validation Behavior

The `_validate_section_data()` method enforces validation with the following logic:

- **Pydantic models:** Automatically considered valid if already correct type
- **Dictionaries:** Validated by attempting model instantiation
- **Lists:** Each item validated against inner model type
- **No validator registered:** Validation skipped for backward compatibility

## Configuration Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `MAX_HISTORY_ENTRIES` | 50 | Maximum version snapshots retained per section |
| `SETTINGS_DIR_NAME` | "settings" | Directory name for current settings |
| `HISTORY_DIR_NAME` | "history" | Directory name for version history |
| `ENCODING` | "utf-8" | File encoding for JSON files |

## Error Handling

The manager implements comprehensive error handling:

- **File I/O Errors:** Logged with detailed traceback information
- **JSON Deserialization Errors:** Gracefully returns defaults or empty instances
- **Validation Errors:** Raised with detailed error information
- **Directory Creation:** Automatic with parent directory support

All errors are logged at appropriate levels (error, warning, debug) for troubleshooting.

## Usage Example

```python
from settings_manager import GlobalSettingsManager
from pydantic import BaseModel

class AppConfig(BaseModel):
    debug: bool
    timeout: int

# Initialize manager
manager = GlobalSettingsManager()

# Register validator
manager.register_section_validator("app_config", AppConfig)

# Write settings
config = AppConfig(debug=True, timeout=30)
manager.write_section("app_config", config)

# Read settings
loaded_config = manager.read_section("app_config", AppConfig)

# List version history
versions = manager.list_history("app_config")

# Rollback to previous version
manager.rollback("app_config", versions[0].timestamp)
```