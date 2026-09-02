# Custom Tools Module

## Overview

The custom tools module provides utilities for managing and retrieving custom project tools while integrating them seamlessly with the standard tools system. This module is essential for extending the capabilities of codx-junior with project-specific tools.

## Key Components

### `get_project_tools()`

Retrieves all active custom tools for a project and converts them to the format expected by the tools system.

**Parameters:**
- `settings` (CODXJuniorSettings): Project settings containing project configuration and context

**Returns:**
- `List[Dict[str, Any]]`: List of tool definitions compatible with the tools system. Each tool definition includes:
  - `tool_json`: Tool metadata and schema
  - `settings`: Tool-specific configuration
  - `tool_call`: Callable function to execute the tool

**Error Handling:**
- If an error occurs during tool retrieval, the function logs the error and returns an empty list

**Example:**
```python
tools = get_project_tools(settings)
# Each tool contains: tool_json, settings, tool_call
```

### `_convert_to_tool_format()`

Converts a CustomTool instance to the standard tool system format.

**Parameters:**
- `custom_tool` (CustomTool): The custom tool instance to convert
- `settings` (CODXJuniorSettings): Project settings

**Returns:**
- `Dict[str, Any]`: Tool definition containing:
  - `tool_json`: Tool schema generated from the custom tool
  - `settings`: Configuration object specifying synchronous execution, chat scope, and single string response
  - `tool_call`: Wrapper function that delegates execution to CustomToolExecutor

## Tool Settings Configuration

Custom tools are configured with the following default settings:

| Setting | Value | Purpose |
|---------|-------|---------|
| `async` | False | Tools execute synchronously |
| `scope` | "chat" | Tools are available in chat context |
| `dual_response` | False | Tools return a single string response |
| `custom_tool` | True | Marks the tool as a custom tool |

## CustomToolManager

The `CustomToolManager` class is exposed through this module and handles the retrieval and management of custom tools from project storage.

## Exported Components

- `get_project_tools`: Function for retrieving active custom tools
- `CustomToolManager`: Class for managing custom tools