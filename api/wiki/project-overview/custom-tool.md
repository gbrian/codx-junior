# Custom Tool Models

## Overview

This module defines Pydantic models for managing custom tools in the codx-api project, including parameters, execution, and metadata management. It provides a complete framework for users to define and execute project-specific tools with type validation and schema generation.

## Core Components

### CustomToolParameter

Represents a single parameter definition for a custom tool.

**Attributes:**
- `name` - Parameter identifier (must be a valid Python variable name)
- `param_type` - Python typing string (e.g., 'str', 'int', 'List[str]')
- `description` - Human-readable parameter description
- `required` - Boolean flag indicating if parameter is mandatory
- `default_value` - Optional default value when parameter is not required

**Validation:**
- Parameter names are validated to be valid Python identifiers
- Parameter types must match supported types in the SUPPORTED_PARAM_TYPES dictionary

### CustomTool

Represents a complete user-defined custom tool for a project.

**Attributes:**
- `id` - Unique identifier (tool name, must be valid Python identifier)
- `name` - Display name of the tool
- `description` - Detailed description of tool functionality
- `language` - Script language ('sh' or 'bash', currently shell only)
- `script_body` - The actual script content to execute
- `parameters` - List of CustomToolParameter definitions
- `active` - Boolean flag for tool availability
- `created_at` - Creation timestamp (UTC)
- `updated_at` - Last modification timestamp (UTC)
- `created_by` - Username of the tool creator
- `project_id` - Associated project identifier
- `tool_path` - File system path to tool storage

**Validation:**
- Tool ID must be a valid Python identifier
- Language is normalized to 'sh'

### CustomToolExecutionRequest

Request model for executing a custom tool.

**Attributes:**
- `tool_id` - Identifier of the custom tool to execute
- `parameters` - Dictionary of parameter values for execution

### CustomToolExecutionResponse

Response model returned from custom tool execution.

**Attributes:**
- `tool_id` - Identifier of the executed tool
- `success` - Boolean indicating execution success
- `user_response` - User-facing message (stderr output)
- `llm_response` - LLM context message (stdout output)
- `execution_time_ms` - Execution duration in milliseconds
- `error` - Optional error message if execution failed

## Supported Parameter Types

The following parameter types are supported for custom tool parameters:

- Basic types: `str`, `string`, `int`, `float`, `bool`
- Collection types: `list`, `dict`
- Generic types: `List[str]`, `List[int]`, `List[Any]`, `Dict[str, Any]`
- Optional types: `Optional[str]`

## Tool JSON Schema Generation

The `CustomTool` model provides a `to_tool_json()` method that converts a custom tool definition into JSON schema format compatible with the existing tool system. This method:

- Generates a JSON schema from parameter definitions
- Maps Python type hints to JSON schema types
- Identifies required parameters
- Preserves parameter descriptions and defaults

**Type Mapping:**
Python types are automatically converted to JSON schema equivalents:
- `str`, `string` → `string`
- `int` → `integer`
- `float` → `number`
- `bool` → `boolean`
- `list`, `List[*]` → `array`
- `dict`, `Dict[*]` → `object`
- `Optional[str]` → `string`