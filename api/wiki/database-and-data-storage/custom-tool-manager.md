# Custom Tool Manager

## Overview

The Custom Tool Manager is a database and data storage component that handles CRUD (Create, Read, Update, Delete) operations for project-specific user-defined tools. It provides file system-based storage similar to the ProfileManager, organizing tools within the project structure at `~/.codx/projects/[project_id]/custom_tools/`.

## Storage Structure

Custom tools are stored in a hierarchical directory structure:

```
~/.codx/projects/[project_id]/custom_tools/
├── [tool_id]/
│   ├── [tool_id].tool.json    (metadata + script_body)
│   └── [tool_id].sh           (script file, for reference)
```

Each tool occupies its own folder containing a metadata file and an optional script file.

## Initialization

The CustomToolManager is initialized with project settings:

```python
manager = CustomToolManager(settings: CODXJuniorSettings)
```

**Parameters:**
- `settings`: Project settings containing `project_id` and `codx_path`

The manager automatically creates the custom tools directory structure if it doesn't exist.

## Core Operations

### Create Tool

Creates a new custom tool in the project.

**Method:** `create_tool(tool: CustomTool) -> CustomTool`

**Parameters:**
- `tool`: CustomTool instance to create

**Returns:**
- CustomTool with updated metadata and tool_path

**Exceptions:**
- `ValueError`: If tool with the same ID already exists
- `IOError`: If file write operation fails

**Process:**
1. Validates that the tool ID doesn't already exist
2. Sets the project_id on the tool
3. Creates the tool folder
4. Saves metadata to JSON file
5. Saves script body to script file

### Get Tool

Retrieves a specific custom tool by its ID.

**Method:** `get_tool(tool_id: str) -> Optional[CustomTool]`

**Parameters:**
- `tool_id`: The tool identifier

**Returns:**
- CustomTool instance if found, None otherwise

**Process:**
1. Locates the metadata file
2. Deserializes JSON data into a CustomTool object
3. Sets the tool_path property

### List Tools

Retrieves all custom tools in the project with optional filtering.

**Method:** `list_tools(active_only: bool = False) -> List[CustomTool]`

**Parameters:**
- `active_only`: If True, returns only active tools (default: False)

**Returns:**
- List of CustomTool instances

### Update Tool

Updates an existing custom tool while preserving creation metadata.

**Method:** `update_tool(tool_id: str, updated_tool: CustomTool) -> CustomTool`

**Parameters:**
- `tool_id`: The tool identifier to update
- `updated_tool`: CustomTool with updated values

**Returns:**
- Updated CustomTool instance

**Exceptions:**
- `ValueError`: If tool does not exist
- `IOError`: If file write operation fails

**Process:**
1. Retrieves the existing tool
2. Preserves creation metadata (id, created_at, created_by, project_id)
3. Updates metadata file
4. Updates script file
5. Returns the updated tool

### Delete Tool

Deletes a custom tool and all its associated files.

**Method:** `delete_tool(tool_id: str) -> bool`

**Parameters:**
- `tool_id`: The tool identifier to delete

**Returns:**
- True if deleted successfully, False if not found

**Exceptions:**
- `OSError`: Logged if directory removal fails

## Helper Methods

### Path Resolution

The manager provides several internal methods for path resolution:

- `_get_custom_tools_path()`: Returns the base custom_tools directory path
- `_get_tool_folder(tool_id)`: Returns the folder path for a specific tool
- `_get_tool_metadata_path(tool_id)`: Returns the metadata file path
- `_get_tool_script_path(tool_id, language)`: Returns the script file path

### File Operations

- `_save_tool_metadata(path, tool)`: Serializes tool data to JSON format
- `_save_tool_script(path, script_body)`: Writes script content to file

Both methods automatically create necessary directories if they don't exist.

## Constants

- `CUSTOM_TOOLS_DIR`: Directory name for custom tools ("custom_tools")
- `TOOL_METADATA_SUFFIX`: Metadata file extension (".tool.json")

## Error Handling

The manager includes comprehensive error handling with logging:
- File read/write failures are caught and logged
- JSON deserialization errors are handled gracefully
- Directory operations include error logging and recovery