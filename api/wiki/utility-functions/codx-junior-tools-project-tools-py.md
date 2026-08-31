# Project Tools Documentation

## Overview

The `project_tools.py` module provides utility functions for managing project files, searching project knowledge, and processing code within the CODX Junior framework. These tools enable AI-assisted operations on project resources with built-in validation and error handling.

## Core Functions

### get_ai()

Initializes and returns an AI instance configured for a specific tool.

**Parameters:**
- `settings` (CODXJuniorSettings): The project settings
- `tool_name` (str): The name of the tool requesting the AI instance

**Returns:**
- AI: An initialized AI instance

**Usage:**
```python
ai = get_ai(settings=settings, tool_name="my_tool")
```

---

### code_block()

Processes code to ensure it follows project standards and returns it in formatted code block syntax.

**Parameters:**
- `file_path` (str): Absolute file path
- `code` (str): The code to process
- `code_language` (str): The programming language of the code
- `**kwargs`: Additional arguments including:
  - `settings` (CODXJuniorSettings): Project settings (required)

**Returns:**
- str: The processed code in code block format

**Raises:**
- Exception: If settings are invalid or missing

---

### path_to_absolute_project_path()

Converts relative or absolute file paths to absolute project paths with validation.

**Parameters:**
- `settings` (CODXJuniorSettings): Project settings containing the absolute project path
- `file_path` (str): The file path to convert (relative or absolute)

**Returns:**
- Union[str, None]: The absolute path if the file exists within the project, None otherwise

**Behavior:**
- Handles both absolute and relative paths
- Validates that paths exist within the project root
- Uses glob patterns to locate files recursively

---

### project_read_file()

Reads content from multiple files in the project with bulk operation support.

**Parameters:**
- `file_paths` (List[str]): Array of paths to files to read. Supports multiple files in a single call to reduce API calls
- `**kwargs`: Additional arguments including:
  - `settings` (CODXJuniorSettings): Project settings (required)

**Returns:**
- ToolResponse: Contains:
  - `user_content`: Full file contents in code blocks
  - `llm_content`: Concise summary with file paths and line counts
- str: Error message if settings are invalid

**Raises:**
- ValueError: If file_paths is empty or not provided
- Exception: If settings are invalid or missing

**Features:**
- Bulk operations: Read multiple related files in one call
- Error handling: Returns error blocks for invalid files and continues processing
- Code block formatting: Automatically detects file extensions for syntax highlighting
- Logging: Tracks successful and failed file reads

**Example:**
```python
result = project_read_file(['src/auth.py', 'src/models.py', 'tests/test_auth.py'])
```

---

### project_search()

Searches for documents within the project knowledge base with support for multiple queries.

**Parameters:**
- `search` (Union[str, List[str]]): Single search query or list of search queries
- `validation` (str, optional): Brief text to validate and filter search results
- `**kwargs`: Additional arguments including:
  - `settings` (CODXJuniorSettings): Project settings

**Returns:**
- ToolResponse: Contains:
  - `user_content`: Full search results with document sources
  - `llm_content`: Summary of matched documents
- ToolResponse: Error message if no results found

**Raises:**
- ValueError: If search argument is empty or not provided

**Features:**
- Bulk operations: Execute multiple searches in one call
- AI filtering: Uses AI to extract relevant content based on validation text
- Duplicate prevention: Aggregates documents by source
- Consistent ordering: Sorts results by document index

**Example:**
```python
result = project_search(['database queries', 'authentication', 'error handling'], 
                        validation='security and performance')
```

---

### project_write_file()

Writes content to a file in the project with validation and confirmation.

**Parameters:**
- `file_path` (str): The path to the file to write (relative or absolute within project)
- `content` (str): The content to write to the file
- `**kwargs`: Additional arguments including:
  - `settings` (CODXJuniorSettings): Project settings (required)

**Returns:**
- ToolResponse: Contains:
  - `user_content`: Success confirmation with file path
  - `llm_content`: Summary with line and character counts

**Raises:**
- Exception: If settings are invalid or file path is outside project root

**Features:**
- Path validation: Ensures file paths remain within project root
- Content processing: Pre-processes content to match project standards
- Detailed logging: Tracks all write operations

---

## Error Handling

All functions implement comprehensive error handling:

- **Validation checks**: Verify settings are provided and valid
- **Path security**: Ensure all file operations remain within project root
- **Detailed logging**: DEBUG and ERROR level logs track all operations
- **Error blocks**: Failed operations return formatted error messages
- **Exception transparency**: Original error messages included in responses

## Response Format

Functions use the `ToolResponse` class to provide dual-purpose output:
- **user_content**: Detailed, formatted information for display to users
- **llm_content**: Concise summaries optimized for LLM context

This design reduces token usage while maintaining clarity for both human and AI consumers.

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/engine.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/utils/utils.py, codx/junior/ai/__init__.py, codx/junior/model/model.py
**Imported by:** codx/junior/tools/__init__.py