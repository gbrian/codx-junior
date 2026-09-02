# Tools Module Overview

The Tools module aggregates all available tools for chat and project interactions within the codx-junior API. Tools are organized as callable functions with associated metadata for seamless integration with language models and the API.

## Tool Scope Levels

Tools are categorized by their availability scope:

- **global**: Tools always included in conversations (e.g., code_block_generator)
- **chat**: Tools available based on conversation context and selection
- **profile**: Tools available based on user profile or role

## Tool Response Types

Tools support two response formats:

- **str**: Traditional single-string response used for LLM context
- **ToolResponse**: Dual-return object for tools that need to produce both user-facing content and LLM feedback

## Available Tools

### fetch_webpage

Fetches a webpage and converts it to markdown format.

**Parameters:**
- `url` (string, required): The URL of the webpage to fetch
- `include_images` (boolean): Whether to include image references in the markdown
- `max_length` (integer): Maximum length of the output markdown
- `headers` (object): Optional HTTP headers for the request

**Scope:** chat

---

### project_search

Searches for documents within a project using one or more search queries.

**Features:**
- Supports single query (string) or multiple queries (array) for bulk operations
- Includes optional validation parameter to filter results from large documents
- Reduces tool calls by allowing multiple related queries in one call

**Parameters:**
- `search` (string or array, required): Single or multiple search queries
- `validation` (string): Optional text to validate and filter search results

**Scope:** chat | **Response Type:** Dual response

---

### project_read_file

Reads project file content from one or multiple file paths.

**Features:**
- Supports bulk operations with multiple file paths in one call
- Handles relative or absolute paths and glob patterns
- Returns invalid or missing files as error blocks
- More efficient than separate calls for related files

**Parameters:**
- `file_path` (string or array, required): Single file path or list of file paths

**Scope:** chat | **Response Type:** Dual response

---

### project_write_file

Writes content to a project file, creating the file or directory if needed.

**Parameters:**
- `file_path` (string, required): Relative or absolute path to the file to write
- `content` (string, required): The content to write to the file

**Scope:** chat | **Response Type:** Dual response

---

### project_structure

Retrieves the project structure with files and folders in a tree-like representation, excluding invalid files.

**Parameters:**
- `include_details` (boolean): Includes additional metadata like file counts and folder statistics (default: false)
- `max_depth` (integer): Maximum folder depth to traverse (default: null for no limit)
- `include_file_sizes` (boolean): Includes file sizes in bytes for each file (default: false)

**Scope:** chat

---

### generate_tasks_tool

Generates sub-tasks from the current chat by analyzing its context and splitting it into actionable tasks. Each sub-task becomes a separate chat connected to the parent.

**Parameters:**
- `instructions` (string): Optional additional instructions to guide task creation (e.g., 'Focus on frontend tasks' or 'Split by component')

**Scope:** chat | **Response Type:** Dual response

---

## Utility Functions

### test_tool

A simple debugging utility that returns a test message.

**Returns:** "test ok!"

---

## Module Exports

The module exports the following for external use:

- `TOOLS` - Complete tools configuration
- `ToolResponse` - Dual-return object class
- All individual tool functions
- `test_tool` - Debugging utility

## Dependencies
**Imports from:** codx/junior/tools/fetch_webpage.py, codx/junior/tools/project_tools.py, codx/junior/tools/code_writer.py
**Imported by:** codx/junior/ai/openai_ai.py, codx/junior/app.py