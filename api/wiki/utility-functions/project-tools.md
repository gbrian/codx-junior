# Project Tools Documentation

## Overview

The `project_tools.py` module provides a comprehensive set of utilities for file operations, searching, and reading within a project. It supports bulk operations to optimize performance and reduce tool call overhead.

**Key Features:**
- Single and bulk file reading with glob pattern support
- Document search with validation filtering
- File writing with git integration
- Automatic path resolution and conversion
- Error handling and logging

---

## Core Functions

### File Reading Operations

#### `project_read_file(file_path, **kwargs)`

Reads the content of one or multiple files from the project with support for bulk operations.

**Parameters:**
- `file_path` (Union[str, List[str]]): Single file path or list of file paths
  - Supports relative and absolute paths
  - Supports glob patterns for flexible file matching
- `**kwargs`: Additional arguments
  - `settings` (CODXJuniorSettings): Project settings (**required**)

**Returns:**
- `ToolResponse`: Contains:
  - `user_response`: Summary of read operations
  - `llm_response`: File contents with error blocks for invalid/missing files

**Exceptions:**
- `ValueError`: If file_path is not provided or empty
- `Exception`: If project settings are not provided

**Performance Notes:**
- Maximum recommended files per call: 10 (MAX_FILES_BULK_OP)
- Exceeding the limit triggers a warning but operation continues
- Use bulk reading for related files to reduce tool calls

**Example:**
```python
result = project_read_file(["src/main.py", "config/settings.py"])
```

---

### Search Operations

#### `project_search(search, validation=None, **kwargs)`

Searches for documents within the project using one or more search queries with optional content filtering.

**Parameters:**
- `search` (Union[str, List[str]]): Single query or list of search queries
- `validation` (Optional[str]): Text to validate and filter search results
  - Helps extract relevant content from large documents
  - Defaults to joined search queries if not provided
- `**kwargs`: Additional arguments
  - `settings` (CODXJuniorSettings): Project settings

**Returns:**
- `ToolResponse`: Contains:
  - `user_response`: Summary of search execution
  - `llm_response`: Formatted search results with code blocks

**Exceptions:**
- `ValueError`: If search argument is not provided or empty

**Performance Notes:**
- Maximum recommended queries per call: 5 (MAX_QUERIES_BULK_OP)
- Returns up to 10 documents per query
- Deduplicates results by source file
- Converts absolute paths to relative paths in results

**Example:**
```python
result = project_search(["authentication", "user session", "login"])
```

---

### File Writing Operations

#### `project_write_file(file_path, content, **kwargs)`

Writes content to a project file, creating it if it doesn't exist. Integrates with git to stage changes before writing.

**Parameters:**
- `file_path` (str): Path to the file to write
- `content` (str): Content to write to the file
- `**kwargs`: Additional arguments
  - `settings` (CODXJuniorSettings): Project settings (**required**)

**Returns:**
- `ToolResponse`: Contains:
  - `user_response`: Confirmation message with file path and byte size
  - `llm_response`: Summary of write operation

**Exceptions:**
- `Exception`: If project settings are not provided or file path is invalid

**Git Integration:**
- Automatically stages file changes if git is initialized in the project
- Skips git operations if `.git` directory is not present
- Logs warnings if git staging fails but continues with file writing

**Example:**
```python
result = project_write_file("src/new_file.py", "print('hello')")
```

---

## Utility Functions

### Path Conversion

#### `path_to_absolute_project_path(settings, file_path)`

Converts a relative or absolute file path to an absolute project path.

**Parameters:**
- `settings` (CODXJuniorSettings): Project settings
- `file_path` (str): Relative or absolute path to resolve

**Returns:**
- `Optional[str]`: Absolute path if valid, None otherwise

**Features:**
- Handles both relative and absolute paths
- Supports glob patterns for flexible file matching
- Validates that resolved path belongs to project directory

#### `_to_relative_path(settings, abs_path)`

Converts an absolute file path to a relative path within the project.

**Parameters:**
- `settings` (CODXJuniorSettings): Project settings
- `abs_path` (str): Absolute path to convert

**Returns:**
- `str`: Relative path from project root, or original path if outside project

---

### Code Processing

#### `code_block(file_path, code, code_language, **kwargs)`

Ensures code follows project standards and returns it in code block format.

**Parameters:**
- `file_path` (str): Absolute file path
- `code` (str): Code to process
- `code_language` (str): Programming language identifier
- `**kwargs`: Additional arguments
  - `settings` (CODXJuniorSettings): Project settings (**required**)

**Returns:**
- `str`: Processed code in formatted code block

**Processing:**
- Applies project-specific code formatting rules
- Integrates with CODXJuniorSession for standardization

---

### AI Integration

#### `get_ai(settings, tool_name)`

Initializes and returns a configured AI instance for tool usage.

**Parameters:**
- `settings` (CODXJuniorSettings): Project settings
- `tool_name` (str): Name of the tool requesting AI instance

**Returns:**
- `AI`: Configured AI instance with user context

---

## Configuration Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `BULK_OPERATION_THRESHOLD` | 3 | Minimum files for bulk operation consideration |
| `MAX_FILES_BULK_OP` | 10 | Maximum recommended files per read operation |
| `MAX_QUERIES_BULK_OP` | 5 | Maximum recommended queries per search operation |
| `FILE_READ_ERROR_TEMPLATE` | Format string | Template for file read error messages |

---

## Error Handling

The module provides comprehensive error handling:

- **Invalid Paths**: Returns error blocks indicating path validation failures
- **Missing Files**: Reports files not found with descriptive error messages
- **Read/Write Failures**: Logs IOError and OSError with detailed messages
- **Git Operations**: Gracefully handles git-related failures without blocking file operations
- **Search Failures**: Returns empty results with informative summaries

All errors are logged at appropriate levels (warning, error) for debugging and monitoring.

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/engine.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/utils/utils.py, codx/junior/ai/__init__.py, codx/junior/model/model.py
**Imported by:** codx/junior/tools/__init__.py