# Project Tools Documentation

## Overview

The Project Tools module provides comprehensive utilities for file operations, searching, and reading within a project. This module enables developers to interact with project files including reading, writing, and searching functionality with support for bulk operations.

## Key Features

- **Bulk File Operations**: Read multiple files efficiently in a single call
- **Flexible Path Resolution**: Support for relative paths, absolute paths, and glob patterns
- **Search Capabilities**: Query project documents with optional validation filtering
- **File Writing**: Create and modify project files with automatic directory handling
- **Error Handling**: Comprehensive error reporting and logging

## Core Functions

### Reading Files

#### `project_read_file(file_path, **kwargs)`

Reads the content of one or multiple files from the project with support for bulk operations.

**Parameters:**
- `file_path`: Single file path (string) or list of file paths
- `settings` (kwargs): CODXJuniorSettings instance (required)

**Returns:**
- `ToolResponse` containing:
  - `user_response`: Summary of successfully read files and errors
  - `llm_response`: Formatted file contents with error blocks

**Features:**
- Supports bulk reading up to 10 files
- Handles both relative and absolute paths
- Returns formatted code blocks for each file
- Logs warnings for operations exceeding recommended limits

**Example:**
```python
result = project_read_file(["src/main.py", "config/settings.py"], settings=settings)
```

### Searching Project

#### `project_search(search, validation=None, **kwargs)`

Searches for documents within the project using one or more search queries with optional result filtering.

**Parameters:**
- `search`: Single query (string) or list of queries
- `validation`: Optional text to filter search results (default: uses search queries)
- `settings` (kwargs): CODXJuniorSettings instance

**Returns:**
- `ToolResponse` containing:
  - `user_response`: Search statistics
  - `llm_response`: Formatted search results with code blocks

**Features:**
- Supports up to 5 bulk queries
- Deduplicates results by source
- Optional AI-powered content filtering using validation text
- Comprehensive logging and error handling

**Example:**
```python
result = project_search(["authentication", "user session"], settings=settings)
```

### Writing Files

#### `project_write_file(file_path, content, **kwargs)`

Writes content to a project file, creating it if it doesn't exist.

**Parameters:**
- `file_path`: Path to the file to write
- `content`: Content to write to the file
- `settings` (kwargs): CODXJuniorSettings instance (required)

**Returns:**
- `ToolResponse` containing:
  - `user_response`: Confirmation message with file size
  - `llm_response`: Operation summary

**Features:**
- Automatically creates parent directories
- UTF-8 encoding support
- Validates file paths against project directory
- Returns byte size information

**Example:**
```python
result = project_write_file("src/new_file.py", "print('hello')", settings=settings)
```

## Utility Functions

### Path Resolution

#### `path_to_absolute_project_path(settings, file_path)`

Converts relative or absolute file paths to absolute project paths with glob pattern support.

**Parameters:**
- `settings`: CODXJuniorSettings instance
- `file_path`: Relative or absolute path to resolve

**Returns:**
- Absolute path if valid, `None` otherwise

### Single File Reading

#### `_read_single_file(settings, file_path)`

Internal function that reads a single file and returns formatted content or error information.

**Returns:**
- Tuple of `(formatted_content, error_message)` or `(error_block, error_description)`

### Code Block Processing

#### `code_block(file_path, code, code_language, **kwargs)`

Ensures code follows project standards and returns it in formatted code block syntax.

**Parameters:**
- `file_path`: Absolute file path
- `code`: Code content to process
- `code_language`: Programming language identifier

**Returns:**
- Formatted code block string

### AI Instance Management

#### `get_ai(settings, tool_name)`

Initializes and returns a configured AI instance for tool usage.

**Parameters:**
- `settings`: CODXJuniorSettings instance
- `tool_name`: Name of the requesting tool

**Returns:**
- Configured AI instance

## Configuration Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `BULK_OPERATION_THRESHOLD` | 3 | Minimum files for bulk operation |
| `MAX_FILES_BULK_OP` | 10 | Maximum recommended files per bulk read |
| `MAX_QUERIES_BULK_OP` | 5 | Maximum recommended queries per bulk search |
| `FILE_READ_ERROR_TEMPLATE` | Error format string | Standard error message format |

## Error Handling

All functions include comprehensive error handling:

- **Invalid Paths**: Returns error blocks when paths fall outside project directory
- **Missing Files**: Provides clear error messages for non-existent files
- **I/O Errors**: Catches and logs IOError and OSError exceptions
- **Missing Settings**: Validates required settings before operations

## Response Format

All tool functions return `ToolResponse` objects with two components:

- **user_response**: Human-readable summary suitable for user display
- **llm_response**: Detailed response content for language model consumption

This dual-response approach ensures clear communication with both end users and AI systems.

## Best Practices

1. **Bulk Operations**: Use bulk operations for related files to reduce tool calls
2. **Path Formats**: Use relative paths for better portability
3. **Search Queries**: Combine related queries in single calls when possible
4. **Validation Filtering**: Use validation parameter in searches to extract only relevant content
5. **Error Monitoring**: Monitor logs for warnings about exceeding operation limits

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/engine.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/utils/utils.py, codx/junior/ai/__init__.py, codx/junior/model/model.py
**Imported by:** codx/junior/tools/__init__.py