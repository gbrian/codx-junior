# Tools Module Documentation

## Overview

The tools module provides a comprehensive collection of callable functions designed for chat and project interactions within the codx-junior API. Tools are organized with associated metadata to enable seamless integration with language models and the API infrastructure.

## Tool Scope Levels

Tools are categorized by their availability scope:

- **global**: Tools always included in conversations (e.g., `code_block_generator`)
- **chat**: Tools available based on conversation context and selection
- **profile**: Tools available based on user profile or role

## Tool Response Types

The module supports two response formats:

- **str**: Traditional single-string response used for LLM context
- **ToolResponse**: Dual-return object for tools that need to produce both user-facing content and LLM feedback

## Available Tools

### fetch_webpage

Retrieves and converts webpage content to markdown format.

**Parameters:**
- `url` (string, required): The URL of the webpage to fetch
- `include_images` (boolean): Whether to include image references in the markdown
- `max_length` (integer): Maximum length of the output markdown
- `headers` (object): Optional HTTP headers for the request

**Scope:** chat

### project_search

Searches for documents within a project using one or more search queries. Supports bulk operations to reduce tool calls by accepting multiple queries simultaneously.

**Parameters:**
- `search` (string or array, required): Single search query or list of search queries
- `validation` (string): Optional text to validate and filter search results

**Scope:** chat  
**Response Type:** Dual response

### project_read_file

Reads project file content from one or multiple file paths. Supports bulk operations for efficiency.

**Parameters:**
- `file_path` (string or array, required): Single file path or list of file paths. Supports relative or absolute paths and glob patterns

**Scope:** chat  
**Response Type:** Dual response  
**Note:** Invalid or missing files are returned as error blocks

### project_write_file

Writes content to a project file. Creates the file or directory if it doesn't exist.

**Parameters:**
- `file_path` (string, required): Relative or absolute path to the file to write
- `content` (string, required): The content to write to the file

**Scope:** chat  
**Response Type:** Dual response

### project_structure

Retrieves the project structure with files and folders, excluding invalid files. Returns a tree-like representation of the project organization.

**Parameters:**
- `include_details` (boolean): Includes additional metadata like file counts and folder statistics (default: False)
- `max_depth` (integer): Maximum folder depth to traverse (default: null for no limit)
- `include_file_sizes` (boolean): Includes file sizes in bytes for each file (default: False)

**Scope:** chat

### generate_tasks_tool

Generates sub-tasks from the current chat by analyzing its context and splitting it into actionable tasks. Each sub-task becomes a separate chat connected to the parent.

**Parameters:**
- `instructions` (string): Optional additional instructions to guide task creation (e.g., 'Focus on frontend tasks' or 'Split by component')

**Scope:** chat  
**Response Type:** Dual response

### code_writer

Enables writing and modifying code within the project context.

**Scope:** chat

### code_block_generator

Generates code blocks with associated metadata.

**Scope:** global

## Bulk Operation Best Practices

To optimize performance and reduce tool calls:

- **project_search**: Provide multiple related queries as a list instead of making separate calls
  - Example: `search=["authentication", "user session"]`
  
- **project_read_file**: Read multiple related files in one call by providing a list of paths
  - Example: `file_path=["src/main.py", "config/settings.py"]`

## ToolResponse Class

The `ToolResponse` class enables tools to provide dual-return functionality, supporting both user-facing content and LLM feedback simultaneously. This is utilized by search, read, write, and task generation tools to deliver comprehensive responses.

## Dependencies
**Imports from:** codx/junior/tools/fetch_webpage.py, codx/junior/tools/project_tools.py, codx/junior/tools/code_writer.py
**Imported by:** codx/junior/ai/openai_ai.py, codx/junior/app.py