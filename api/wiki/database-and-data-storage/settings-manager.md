# GlobalSettingsManager Documentation

## Overview

GlobalSettingsManager is a robust settings management system that handles storage, versioning, and validation of configuration data. Each top-level settings section is stored independently in its own JSON file with automatic version history tracking.

### Key Features

- **Sectioned Storage**: Each settings section stored in separate JSON files under `<config_folder>/settings/`
- **Version Control**: Automatic backups maintained under `<config_folder>/history/<section>/`
- **Schema Validation**: Pydantic-based validation before persisting data
- **Rollback Capability**: Restore previous versions of any settings section
- **Flexible Data Handling**: Support for Pydantic models, dictionaries, lists, and scalar values

---

## Architecture

### Directory Structure

```
config_folder/
├── settings/
│   ├── section1.json
│   ├── section2.json
│   └── ...
└── history/
    ├── section1/
    │   ├── 20240115_120530_123456.json
    │   └── ...
    └── section2/
        └── ...
```

### Configuration Locations

The manager uses the following precedence for config folder location:

1. Explicitly provided `config_folder` parameter
2. `CODX_JUNIOR_CONFIG_FOLDER` environment variable
3. User's HOME directory

---

## Core Operations

### Reading Settings

#### Read with Model Validation
```python
read_section(section: str, model_class: Type[T], default: Optional[T] = None) -> T
```

Reads and deserializes a settings section into a Pydantic model instance. Returns the default value or an empty model instance if the file doesn't exist or contains invalid data.

#### Read Raw Data
```python
read_section_raw(section: str) -> Any
```

Reads a section as raw Python data (dict, list, or scalar) without model validation.

#### Read All Sections
```python
read_all() -> Dict[str, Any]
```

Reads all available section files and returns them as a dictionary mapping section names to their raw data.

### Writing Settings

```python
write_section(section: str, data: Any) -> None
```

Serializes and persists settings data with the following workflow:

1. **Validates** data against registered schema (if validator exists)
2. **Backs up** current version to history
3. **Writes** new data to section file
4. **Prunes** old history entries beyond `MAX_HISTORY_ENTRIES` (default: 50)

Accepts Pydantic models, dictionaries, lists, or scalar values.

---

## Version Control

### List Version History

```python
list_history(section: str) -> List[SectionVersion]
```

Returns available version snapshots for a section, ordered from newest to oldest. Each version includes:
- Section name
- Timestamp identifier
- File path

### Retrieve Specific Version

```python
get_version(section: str, timestamp: str) -> Any
```

Retrieves the raw content of a specific version snapshot by timestamp.

### Rollback to Previous Version

```python
rollback(section: str, timestamp: str) -> bool
```

Restores a section to a specific historical version. The current state is automatically backed up before rollback. Returns `True` on success, `False` if the specified version is not found.

---

## Schema Validation

### Register Single Validator

```python
register_section_validator(section: str, model_class: Type[BaseModel]) -> None
```

Registers a Pydantic model class as the validator for a section.

### Register Multiple Validators

```python
register_section_validators(validators: Dict[str, Type[BaseModel]]) -> None
```

Registers multiple section validators at once using a dictionary mapping.

### Validation Behavior

- **Pydantic Models**: Already-validated models pass through without additional checks
- **Dictionaries**: Converted to model instances for validation
- **Lists**: Each item validated against the inner model type
- **No Validator**: Validation is skipped for sections without registered validators (backward compatible)

---

## Data Models

### SectionVersion

Represents a single version snapshot of a settings section:

| Field | Type | Description |
|-------|------|-------------|
| `section` | str | Name of the section |
| `timestamp` | str | Timestamp identifier |
| `file_path` | str | Full path to the version file |

---

## Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `MAX_HISTORY_ENTRIES` | 50 | Maximum backup versions kept per section |
| `SETTINGS_DIR_NAME` | "settings" | Directory name for current settings |
| `HISTORY_DIR_NAME` | "history" | Directory name for version history |
| `ENCODING` | "utf-8" | File encoding for all read/write operations |

---

## Error Handling

- **File Not Found**: Returns default value or empty model instance
- **JSON Parsing Errors**: Logs error and returns default/empty instance
- **Validation Errors**: Raises `ValidationError` with detailed error information
- **File System Errors**: Logs errors; backup/write failures raise exceptions

All errors are logged with appropriate severity levels (DEBUG, INFO, WARNING, ERROR).