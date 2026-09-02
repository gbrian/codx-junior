# Custom Tool Models

## Overview

This module defines Pydantic models for managing custom tools in the codx-api project. It provides a comprehensive structure for creating, configuring, and executing user-defined project tools with support for parameters, metadata, and execution management.

## Supported Parameter Types

The custom tool system supports the following Python type hints:

- **Basic Types**: `str`, `string`, `int`, `float`, `bool`
- **Collection Types**: `list`, `dict`
- **Generic Types**: `List[str]`, `List[int]`, `List[Any]`, `Dict[str, Any]`
- **Optional Types**: `Optional[str]`

## Core Models

### CustomToolParameter

Represents a single parameter for a custom tool.

**Attributes:**
- `name` (str): Parameter identifier, must be a valid Python variable name
- `param_type` (str): Python typing string (e.g., 'str', 'int', 'List[str]')
- `description` (str): Human-readable description of the parameter
- `required` (bool): Whether parameter is required for tool execution (default: True)
- `default_value` (Any, optional): Optional default value if not required

**Validation:**
- Parameter names are validated to ensure they are valid Python identifiers
- Parameter types must be from the supported types list

### CustomTool

Represents a user-defined custom tool for a project.

**Attributes:**
- `id` (str): Unique identifier (tool name), must be a valid Python identifier
- `name` (str): Display name of the tool
- `description` (str): Detailed description of what the tool does
- `language` (str): Script language (currently only 'sh' supported, default: "sh")
- `script_body` (str): The script content to execute
- `parameters` (List[CustomToolParameter]): List of tool parameters
- `active` (bool): Whether tool is available for use (default: True)
- `created_at` (datetime): Timestamp of tool creation
- `updated_at` (datetime): Timestamp of last update
- `created_by` (str): Username of creator
- `project_id` (str): Associated project identifier
- `tool_path` (str, optional): File system path to tool

**Methods:**

#### to_tool_json()
Converts the custom tool to tool JSON format for integration with the tools system.

**Returns:** A dictionary containing:
- `type`: "function"
- `function`: Object containing:
  - `name`: Tool ID
  - `description`: Tool description
  - `parameters`: JSON schema object with properties and required fields

**Example Output:**
```json
{
  "type": "function",
  "function": {
    "name": "tool_id",
    "description": "Tool description",
    "parameters": {
      "type": "object",
      "properties": {
        "param_name": {
          "type": "string",
          "description": "Parameter description"
        }
      },
      "required": ["param_name"]
    }
  }
}
```

#### _python_type_to_json_type()
Static method that converts Python type hints to JSON schema types.

**Mapping:**
- `str`, `string` → `"string"`
- `int` → `"integer"`
- `float` → `"number"`
- `bool` → `"boolean"`
- `list`, `List[str]`, `List[int]`, `List[Any]` → `"array"`
- `dict`, `Dict[str, Any]` → `"object"`
- `Optional[str]` → `"string"`

### CustomToolExecutionRequest

Request model for executing a custom tool.

**Attributes:**
- `tool_id` (str): Custom tool ID
- `parameters` (Dict[str, Any]): Execution parameters

### CustomToolExecutionResponse

Response model from custom tool execution.

**Attributes:**
- `tool_id` (str): Identifier of executed tool
- `success` (bool): Whether execution was successful
- `user_response` (str): stderr output - user-facing message
- `llm_response` (str): stdout output - LLM context
- `execution_time_ms` (float): Execution duration in milliseconds
- `error` (str, optional): Error message if execution failed

## Validation Rules

- **Tool ID**: Must be a valid Python identifier
- **Parameter Names**: Must be valid Python identifiers
- **Parameter Types**: Must be from the supported types list
- **Language**: Only 'sh' and 'bash' are accepted (automatically normalized to 'sh')
- **Required Fields**: `id`, `name`, and `script_body` are mandatory for CustomTool; `name` and `param_type` are mandatory for CustomToolParameter