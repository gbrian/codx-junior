# Tools Module Documentation

## Overview

The tools module serves as the central aggregation point for all available tools in the codx-junior API. These tools enable chat interactions and project manipulations through callable functions with associated metadata designed for language model integration.

## Tool Organization

Tools are organized into three distinct scope levels that determine their availability:

- **global**: Tools that are always included in conversations (e.g., `code_block_generator`)
- **chat**: Tools available based on conversation context and user selection
- **profile**: Tools available based on user profile or role

## Response Types

Tools support two response mechanisms:

- **str**: Traditional single-string responses used for language model context
- **ToolResponse**: A dual-return object for tools requiring both user-facing content and language model feedback

## Available Tools

### fetch_webpage

Retrieves and converts webpage content to markdown format.

**Parameters:**
- `url` (string, required): The URL of the webpage to fetch
- `include_images` (boolean): Whether to include image references in the markdown
- `max_length` (integer): Maximum length of the output markdown
- `headers` (object): Optional HTTP headers for the request

**Scope:** chat | **Async:** No

### project_search

Searches for documents within a project using one or more search queries. Supports bulk operations to reduce tool calls by providing multiple queries simultaneously.

**Parameters:**
- `search` (string or array, required): Single search query or list of search queries
- `validation` (string): Optional text to validate and filter search results from large documents

**Scope:** chat | **Async:** No | **Dual Response:** Yes

**Note:** Providing multiple related queries in one call is more efficient than making separate calls.

### project_read_file

Reads project file content from one or multiple file paths. Supports bulk operations for reading multiple files at once.

**Parameters:**
- `file_path` (string or array, required): Single file path or list of file paths; supports relative/absolute paths and glob patterns

**Scope:** chat | **Async:** No | **Dual Response:** Yes

**Note:** Invalid or missing files are returned as error blocks. Multiple file reads in one call are more efficient.

### project_write_file

Writes content to a project file, automatically creating the file or directory if it doesn't exist.

**Parameters:**
- `file_path` (string, required): Relative or absolute path to the file
- `content` (string, required): The content to write to the file

**Scope:** chat | **Async:** No | **Dual Response:** Yes

**Note:** Currently supports writing a single file per call.

### project_structure

Retrieves the project structure with files and folders, presenting a tree-like representation of project organization.

**Parameters:**
- `include_details` (boolean): Includes additional metadata like file counts and folder statistics (default: False)
- `max_depth` (integer): Maximum folder depth to traverse; null for unlimited (default: None)
- `include_file_sizes` (boolean): Includes file sizes in bytes for each file (default: False)

**Scope:** chat | **Async:** No

### code_block_generator

Tool for generating code blocks with associated metadata for integration with the API.

**Scope:** global

### code_writer

Tool for writing and managing code within the project context.

### generate_tasks_tool

Generates sub-tasks from the current chat by analyzing its context and splitting it into actionable tasks. Each sub-task becomes a separate chat connected to the parent.

**Parameters:**
- `instructions` (string): Optional additional instructions to guide task creation (e.g., 'Focus on frontend tasks')

**Scope:** chat | **Async:** No | **Dual Response:** Yes

## Bulk Operations

Several tools support bulk operations to improve efficiency:

- **project_search**: Provide multiple search queries as an array
- **project_read_file**: Provide multiple file paths as an array

This approach reduces the number of tool calls and improves overall performance compared to making separate requests.

## Error Handling

- The `project_read_file` tool returns invalid or missing files as error blocks
- All tools maintain logging capabilities through the integrated logger for debugging purposes

## Dependencies
**Imports from:** codx/junior/tools/fetch_webpage.py, codx/junior/tools/project_tools.py, codx/junior/tools/code_writer.py
**Imported by:** codx/junior/ai/openai_ai.py, codx/junior/app.py