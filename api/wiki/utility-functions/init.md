# Tools Module Documentation

## Overview

The tools module aggregates all available tools for chat and project interactions within the codx-junior API. Tools are organized as callable functions with associated metadata for seamless integration with language models and the API infrastructure.

## Tool Scope Levels

Tools are categorized by their availability within the system:

- **global**: Tools always included in conversations (e.g., `code_block_generator`)
- **chat**: Tools available based on conversation context and user selection
- **profile**: Tools available based on user profile or role

## Tool Response Types

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

**Settings:** Synchronous, chat scope

---

### project_search

Searches for documents within a project using one or more search queries. Supports bulk operations to reduce tool calls by providing multiple queries at once.

**Parameters:**
- `search` (string or array, required): Single query or list of search queries
- `validation` (string): Optional text to validate and filter search results

**Settings:** Synchronous, chat scope, dual response, project settings enabled

**Note:** Combining multiple related queries in one call is more efficient than making separate calls.

---

### project_read_file

Reads project file content from one or multiple file paths. Supports bulk operations to reduce tool calls.

**Parameters:**
- `file_path` (string or array, required): Single file path or list of file paths. Supports relative/absolute paths and glob patterns

**Settings:** Synchronous, chat scope, dual response, project settings enabled

**Note:** Reading multiple files in one call is more efficient. Invalid or missing files are returned as error blocks.

---

### project_write_file

Writes content to a project file. Creates the file or directory if it doesn't exist.

**Parameters:**
- `file_path` (string, required): Relative or absolute path to the file
- `content` (string, required): The content to write to the file

**Settings:** Synchronous, chat scope, dual response, project settings enabled

---

### apply_file_changes

Safely applies a batch of exact search-and-replace edits to an existing text file. All changes are validated before writing; if any change conflicts, the file remains unchanged.

**Parameters:**
- `file_path` (string, required): Relative or absolute path to the file to modify
- `changes` (array, required): List of change objects with:
  - `search` (string): Exact text pattern to find (must match exactly once)
  - `replace` (string): Text to replace with (include exact indentation)

**Settings:** Synchronous, chat scope, dual response, project settings enabled

**Guidelines:**
- Include sufficient surrounding context to ensure uniqueness
- Do NOT rely on indentation preservation—include exact indentation explicitly
- Each search string must match exactly once in the progressively updated file

---

### project_structure

Retrieves the project structure with files and folders, excluding invalid files. Returns a tree-like representation of the project organization.

**Parameters:**
- `include_details` (boolean, default: false): Includes additional metadata like file counts and folder statistics
- `max_depth` (integer, default: null): Maximum folder depth to traverse (null for no limit)
- `include_file_sizes` (boolean, default: false): Includes file sizes in bytes for each file

**Settings:** Synchronous, chat scope, project settings enabled

---

### generate_tasks_tool

Generates sub-tasks from the current chat by analyzing its context and splitting it into actionable tasks. Each sub-task becomes a separate chat connected to the parent.

**Parameters:**
- `instructions` (string, optional): Additional instructions to guide task creation (e.g., "Focus on frontend tasks" or "Split by component")

**Settings:** Synchronous, chat scope, dual response

---

### test_tool

A simple test tool for debugging purposes.

**Returns:** `"test ok!"`

## Bulk Operations

Several tools support bulk operations to improve efficiency:

- **project_search**: Provide multiple queries as an array in a single call
- **project_read_file**: Provide multiple file paths as an array in a single call

This reduces the number of tool invocations and improves overall performance.

## Response Handling

Tools use either traditional string responses or the `ToolResponse` object for dual-return scenarios. The dual-response capability allows tools to provide both user-facing content and LLM feedback simultaneously.

## Dependencies
**Imports from:** codx/junior/tools/fetch_webpage.py, codx/junior/tools/project_tools.py, codx/junior/tools/code_writer.py
**Imported by:** codx/junior/ai/openai_ai.py, codx/junior/app.py