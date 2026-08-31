# Tools Module Documentation

The Tools module provides a comprehensive collection of callable functions designed for chat and project interactions within the codx-junior API. These tools are organized with associated metadata to facilitate seamless integration with language models and the API infrastructure.

## Overview

Tools are categorized by scope levels that determine their availability:

- **global**: Tools always included in conversations (e.g., `code_block_generator`)
- **chat**: Tools available based on conversation context and selection
- **profile**: Tools available based on user profile or role

Tools can return responses in two formats:
- **str**: Traditional single-string responses used for LLM context
- **ToolResponse**: Dual-return objects for tools requiring both user-facing content and LLM feedback

## Available Tools

### fetch_webpage

Fetches a webpage and converts it to markdown format.

**Parameters:**
- `url` (string, required): The URL of the webpage to fetch
- `include_images` (boolean, optional): Whether to include image references in the markdown
- `max_length` (integer, optional): Maximum length of the output markdown
- `headers` (object, optional): Optional HTTP headers for the request

**Scope:** chat

### project_search

Searches for documents within a project using provided search strings. Supports multiple searches in a single call to reduce API calls.

**Parameters:**
- `search` (array of strings, required): Array of search query strings. Use multiple queries to search for different topics in a single call (e.g., `['authentication logic', 'user database schema', 'API endpoints']`)
- `validation` (string, optional): Brief text used to validate content found by searches, helping reduce large documents and extract only relevant content

**Scope:** chat  
**Dual Response:** Yes

### project_read_file

Reads project file contents from relative or absolute file paths. Supports reading multiple files in a single call to improve efficiency.

**Parameters:**
- `file_paths` (array of strings, required): Array of paths to files to read. Always read multiple related files in a single call instead of making separate calls (e.g., `['src/config.py', 'src/main.py', 'tests/test_config.py']`)

**Scope:** chat  
**Dual Response:** Yes

### project_structure

Returns the project structure with files and folders as a tree-like representation, excluding invalid files.

**Parameters:**
- `include_details` (boolean, optional, default: false): If true, includes additional metadata like file counts and folder statistics
- `max_depth` (integer, optional): Maximum folder depth to traverse; leave null for no limit
- `include_file_sizes` (boolean, optional, default: false): If true, includes file sizes in bytes for each file

**Scope:** chat

### generate_tasks_tool

Generates sub-tasks from the current chat by analyzing its context and splitting it into actionable tasks. Each sub-task becomes a separate chat connected to the parent.

**Parameters:**
- `instructions` (string, optional): Additional instructions to guide task creation (e.g., 'Focus on frontend tasks' or 'Split by component')

**Scope:** chat  
**Dual Response:** Yes

## Best Practices

- Use batch operations when possible: tools supporting multiple inputs should be utilized to reduce API calls
- The `validation` parameter in `project_search` helps extract only relevant content from larger documents
- For file operations, read multiple related files in single calls rather than making separate requests

## Dependencies
**Imports from:** codx/junior/tools/fetch_webpage.py, codx/junior/tools/project_tools.py, codx/junior/tools/code_writer.py
**Imported by:** codx/junior/ai/openai_ai.py, codx/junior/app.py