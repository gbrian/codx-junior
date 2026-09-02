# Project Tools Module Documentation

## Overview

The Project Tools module provides comprehensive utilities for file operations, searching, and reading within a project. It enables efficient interaction with project files through support for bulk operations and intelligent content processing.

## Core Functions

### File Reading Operations

#### `project_read_file()`

Reads the content of one or multiple files from the project with support for bulk operations.

**Parameters:**
- `file_path` (Union[str, List[str]]): Single file path or list of file paths to read. Supports relative paths, absolute paths, and glob patterns.
- `**kwargs`: Additional arguments including:
  - `settings` (CODXJuniorSettings): Project settings (required)

**Returns:**
- `ToolResponse`: Contains user-facing summary and LLM-compatible response with file contents and error information

**Key Features:**
- Supports reading multiple files in a single call to reduce tool invocations
- Automatic error handling for invalid or missing files
- Relative path conversion for consistency
- Logging of successful and failed read operations
- Warning when exceeding recommended bulk operation limit (10 files)

**Example:**
```python
project_read_file(["src/main.py", "config/settings.py"])
```

#### `_read_single_file()`

Internal function that reads a single file and handles error reporting.

**Parameters:**
- `settings` (CODXJuniorSettings): Project settings
- `file_path` (str): Path to the file to read

**Returns:**
- `tuple[str, Optional[str]]`: Returns formatted content with None error, or error block with error description

**Error Handling:**
- Validates file path belongs to project directory
- Checks file existence before reading
- Catches IOError and OSError exceptions
- Returns formatted error blocks for debugging

### File Writing Operations

#### `project_write_file()`

Writes content to a project file, creating the file and parent directories if needed.

**Parameters:**
- `file_path` (str): The path to the file to write
- `content` (str): The content to write to the file
- `**kwargs`: Additional arguments including:
  - `settings` (CODXJuniorSettings): Project settings (required)

**Returns:**
- `ToolResponse`: Contains confirmation message and operation summary

**Features:**
- Automatic parent directory creation
- Path validation to ensure file belongs to project
- File size reporting in response
- Comprehensive error handling with descriptive messages

### Search Operations

#### `project_search()`

Searches for documents within a project using one or more search queries with optional result filtering.

**Parameters:**
- `search` (Union[str, List[str]]): Single search query or list of queries to execute
- `validation` (Optional[str]): Optional text to validate and filter search results
- `**kwargs`: Additional arguments including:
  - `settings` (CODXJuniorSettings): Project settings

**Returns:**
- `ToolResponse`: Contains formatted search results and summary of queries executed

**Key Features:**
- Supports bulk searching with multiple queries in a single call
- Document deduplication by source
- AI-powered content filtering when validation text is provided
- Automatic relative path conversion for project files
- Limit of 10 documents per query
- Warning when exceeding recommended bulk operation limit (5 queries)

**Example:**
```python
project_search(["authentication", "user session", "login"])
```

## Utility Functions

### Path Conversion

#### `path_to_absolute_project_path()`

Converts relative or absolute file paths to absolute project paths.

**Parameters:**
- `settings` (CODXJuniorSettings): Project settings
- `file_path` (str): Relative or absolute path to resolve

**Returns:**
- `Optional[str]`: Absolute path if valid, None otherwise

**Features:**
- Handles both relative and absolute paths
- Supports glob patterns for file discovery
- Validates path belongs to project directory

#### `_to_relative_path()`

Converts absolute file paths to relative paths within the project.

**Parameters:**
- `settings` (CODXJuniorSettings): Project settings
- `abs_path` (str): Absolute path to convert

**Returns:**
- `str`: Relative path from project root

### Code Processing

#### `code_block()`

Processes code to ensure project standards compliance and returns it in formatted code block.

**Parameters:**
- `file_path` (str): Absolute file path
- `code` (str): The code to process
- `code_language` (str): Programming language of the code
- `**kwargs`: Additional arguments including:
  - `settings` (CODXJuniorSettings): Project settings (required)

**Returns:**
- `str`: Processed code in code block format

**Process:**
- Uses CODXJuniorSession for code validation
- Applies project-specific formatting rules
- Returns formatted code block with language and path information

#### `get_ai()`

Initializes and returns an AI instance for tool usage.

**Parameters:**
- `settings` (CODXJuniorSettings): Project settings
- `tool_name` (str): Name of the tool requesting the AI instance

**Returns:**
- `AI`: Configured AI instance with proper settings

## Configuration Constants

- `BULK_OPERATION_THRESHOLD`: 3 - Minimum files for considering bulk operation
- `MAX_FILES_BULK_OP`: 10 - Recommended maximum files per read operation
- `MAX_QUERIES_BULK_OP`: 5 - Recommended maximum searches per operation
- `FILE_READ_ERROR_TEMPLATE`: Error message format for file read failures

## Response Structure

All public functions return a `ToolResponse` object containing:
- `user_response`: Human-readable summary and confirmation messages
- `llm_response`: Detailed response content for language model consumption

## Error Handling

The module implements comprehensive error handling:
- Path validation to prevent directory traversal attacks
- File existence verification before operations
- Exception catching for IOError and OSError
- Detailed error logging for debugging
- Graceful degradation with error blocks in responses

## Bulk Operations

For optimal performance, the module encourages bulk operations:
- Multiple files can be read in a single `project_read_file()` call
- Multiple queries can be executed in a single `project_search()` call
- Warnings are logged when exceeding recommended limits
- All operations maintain individual error tracking

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/engine.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/utils/utils.py, codx/junior/ai/__init__.py, codx/junior/model/model.py
**Imported by:** codx/junior/tools/__init__.py