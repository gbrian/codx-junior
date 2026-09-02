# Custom Tools Module

## Overview

The custom tools module provides utilities for managing and retrieving custom project tools, integrating them seamlessly with the standard tools system. This module serves as the bridge between custom tool definitions and the tool execution framework.

## Purpose

This module enables projects to:
- Manage custom tools specific to their needs
- Convert custom tool definitions to a format compatible with the tools system
- Retrieve and activate custom tools for use within projects
- Execute custom tools through a unified interface

## Key Components

### get_project_tools()

Retrieves all active custom tools for a project and converts them to the standard tool system format.

**Parameters:**
- `settings` (CODXJuniorSettings): Project settings required to identify and configure tools

**Returns:**
- List[Dict[str, Any]]: A list of tool definitions, each containing:
  - `tool_json`: The tool's JSON schema definition
  - `settings`: Configuration including async, scope, response type
  - `tool_call`: The executable function for the tool

**Behavior:**
- Fetches only active custom tools using CustomToolManager
- Handles errors gracefully, returning an empty list if retrieval fails
- Logs the number of tools retrieved for monitoring purposes

### CustomToolManager

Manages the retrieval and listing of custom tools from project storage. Referenced in the module's public API and used internally by `get_project_tools()`.

## Tool Format Conversion

Custom tools are automatically converted to include:
- **tool_json**: The tool's OpenAI-compatible schema
- **settings**: Standardized configuration with properties:
  - `async`: Set to False (synchronous execution)
  - `scope`: Set to "chat"
  - `dual_response`: Set to False (single string response)
  - `custom_tool`: Set to True (identifies as custom tool)
- **tool_call**: A wrapper function that executes the tool via CustomToolExecutor

## Error Handling

The module implements graceful error handling:
- Exceptions during tool retrieval are logged with error details
- An empty list is returned on failure to prevent tool system interruption
- Logging provides visibility into successful retrievals and failures

## Public API

The module exports:
- `get_project_tools()`: Primary function for tool retrieval
- `CustomToolManager`: Class for advanced tool management