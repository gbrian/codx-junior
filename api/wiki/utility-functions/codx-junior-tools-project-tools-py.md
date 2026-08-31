# Project Tools Utility Functions

## Overview

The `project_tools.py` module provides a collection of utility functions for managing project files, searching project knowledge bases, and processing code within the CODX Junior framework. These tools facilitate integration with the project's settings, AI capabilities, and file management system.

## Core Functions

### get_ai

Creates and returns an AI instance configured with the provided settings.

**Parameters:**
- `settings`: Project settings object
- `tool_name`: Identifier for the AI tool instance

**Returns:** An AI instance ready for use

---

### code_block

Processes code to ensure it follows project standards and returns it in a formatted code block.

**Parameters:**
- `file_path` (str): Absolute file path
- `code` (str): The code to process
- `code_language` (str): Programming language of the code
- `**kwargs`: Additional arguments including `settings`

**Returns:** str - Code formatted as a markdown code block with language and file path

**Raises:** Exception if project settings are not provided

**Notes:** This is an async function that leverages `CODXJuniorSession` to process files before saving.

---

### path_to_absolute_project_path

Converts relative file paths to absolute project paths.

**Parameters:**
- `settings` (CODXJuniorSettings): Project configuration
- `file_path` (str): File path to convert

**Returns:** Absolute file path if found, otherwise None

**Behavior:** 
- Accepts both absolute and relative paths
- Uses glob patterns with root directory lookup for flexible path resolution
- Returns the path as-is if already absolute and within project bounds

---

### project_search

Searches the project knowledge base for documents matching a query string.

**Parameters:**
- `search` (str): Search query string (required)
- `validation` (str): Optional validation query for AI-based content extraction
- `**kwargs`: Additional arguments including `settings`

**Returns:** str - Concatenated formatted documents matching the search, or a message indicating no results

**Raises:** ValueError if search string is empty

**Features:**
- Limits results to 10 documents
- Deduplicates documents by source path
- Optionally uses AI to extract relevant lines based on validation criteria
- Returns formatted results with project name and search query

---

### project_read_file

Reads and returns the content of a project file.

**Parameters:**
- `file_path` (str): Path to file to read
- `**kwargs`: Additional arguments including `settings`

**Returns:** str - File content formatted in a markdown code block with language extension and full path

**Raises:** 
- Exception if settings are invalid or missing
- Exception if file path is outside project boundaries
- FileNotFoundError if file does not exist

---

### project_write_file

Writes content to a project file.

**Parameters:**
- `file_path` (str): Path to file to write
- `content` (str): Content to write to file
- `**kwargs`: Additional arguments including `settings`

**Returns:** str

**Raises:**
- Exception if settings are invalid or missing
- Exception if file path is outside project boundaries

**Notes:** Overwrites existing file content.

---

## Configuration

The module includes basic logging configuration at the DEBUG level. Logger name is derived from the module name.

## Dependencies

- `codx.junior.settings.CODXJuniorSettings` - Project configuration
- `codx.junior.engine.CODXJuniorSession` - Session management
- `codx.junior.knowledge.knowledge_milvus.Knowledge` - Knowledge base access
- `codx.junior.ai.AI` - AI capabilities
- `codx.junior.model.model.CodxUser` - User model

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/engine.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/utils/utils.py, codx/junior/ai/__init__.py, codx/junior/model/model.py
**Imported by:** codx/junior/tools/__init__.py