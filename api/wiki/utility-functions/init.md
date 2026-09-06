# Tools Module Documentation

## Overview

The Tools module is the central aggregator for all available tools in the codx-junior API. It provides callable functions with associated metadata designed for seamless integration with language models and the API infrastructure.

## Module Organization

Tools are organized by **scope levels** that determine their availability:

- **global**: Always included in conversations (e.g., `code_block_generator`)
- **chat**: Available based on conversation context and user selection
- **profile**: Available based on user profile or role

## Response Types

Tools can return data in two formats:

- **str**: Traditional single-string response used for LLM context
- **ToolResponse**: Dual-return object for tools requiring both user-facing content and LLM feedback

## Available Tools

### fetch_webpage
Retrieves and converts webpage content to markdown format.

**Parameters:**
- `url` (string, required): The webpage URL
- `include_images` (boolean, optional): Include image references
- `max_length` (integer, optional): Maximum output length
- `headers` (object, optional): Custom HTTP headers

**Scope:** chat

---

### project_search
Searches for documents within a project using single or multiple queries.

**Features:**
- Supports bulk operations with multiple queries in one call
- Optional validation text to filter results from large documents
- Returns dual response format

**Parameters:**
- `search` (string or array, required): Single query or list of queries
- `validation` (string, optional): Text to validate and filter results

**Scope:** chat  
**Dual Response:** Yes

---

### project_read_file
Reads project file content from single or multiple file paths.

**Features:**
- Bulk operation support for reading multiple files at once
- Supports relative, absolute paths, and glob patterns
- Invalid or missing files returned as error blocks

**Parameters:**
- `file_path` (string or array, required): Single path or list of paths

**Scope:** chat  
**Dual Response:** Yes

---

### project_write_file
Writes content to a project file, creating the file or directory if needed.

**Parameters:**
- `file_path` (string, required): Relative or absolute file path
- `content` (string, required): Content to write

**Scope:** chat  
**Dual Response:** Yes

---

### apply_file_changes
Safely applies batch search-and-replace edits to an existing text file.

**Features:**
- Validates all changes before writing
- Each search string must match exactly once
- Changes applied progressively to the updated file
- Requires explicit indentation in search and replace patterns
- File remains unchanged if any conflict occurs

**Parameters:**
- `file_path` (string, required): Path to the file to modify
- `changes` (array, required): List of change objects with:
  - `search` (string): Exact text pattern to find
  - `replace` (string): Replacement text with exact formatting

**Scope:** chat  
**Dual Response:** Yes

---

### project_structure
Retrieves the project structure as a tree-like representation.

**Parameters:**
- `include_details` (boolean, optional): Add metadata like file counts and folder statistics
- `max_depth` (integer, optional): Maximum folder depth to traverse
- `include_file_sizes` (boolean, optional): Include file sizes in bytes

**Scope:** chat

---

### generate_tasks_tool
Generates sub-tasks from the current chat by analyzing context and splitting into actionable items. Each sub-task creates a separate connected chat.

**Parameters:**
- `instructions` (string, optional): Additional guidance for task generation (e.g., "Focus on frontend tasks")

**Scope:** chat  
**Dual Response:** Yes

---

### test_tool
Simple debugging tool that returns a test message.

**Returns:** "test ok!"

## Best Practices

### Bulk Operations
When using `project_search` and `project_read_file`, combine multiple queries or file paths in a single call to reduce API overhead:

```
search=["authentication", "user session"]  // Good
file_path=["src/main.py", "config/settings.py"]  // Good
```

### apply_file_changes
- Include sufficient surrounding context to ensure unique search patterns
- Always specify exact indentation explicitly in both search and replace strings
- Verify all changes before applying to prevent file conflicts

### Exported API
All tools are exported in the `__all__` list for external module access, including:
- Tool functions
- `ToolResponse` model
- `TOOLS` configuration array

## Dependencies
**Imports from:** codx/junior/tools/fetch_webpage.py, codx/junior/tools/project_tools.py, codx/junior/tools/code_writer.py
**Imported by:** codx/junior/ai/openai_ai.py, codx/junior/app.py