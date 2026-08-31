# Tools Module

## Overview

The Tools module aggregates all available tools for chat and project interactions within the codx-junior API. Tools are implemented as callable functions with associated metadata for seamless integration with language models and the API.

## Tool Scope Levels

Tools are organized by their availability and usage context:

- **global**: Tools always included in conversations (e.g., `code_block_generator`)
- **chat**: Tools available based on conversation context and selection
- **profile**: Tools available based on user profile or role

## Tool Response Types

Tools can return responses in two formats:

- **str**: Traditional single-string response used for LLM context
- **ToolResponse**: Dual-return object for tools that need to produce both user-facing content and LLM feedback

## Available Tools

### fetch_webpage

Fetch a webpage and convert it to markdown format.

**Parameters:**
- `url` (string, required): The URL of the webpage to fetch
- `include_images` (boolean): Whether to include image references in the markdown
- `max_length` (integer): Maximum length of the output markdown
- `headers` (object): Optional HTTP headers for the request

**Scope:** chat

### project_search

Search for documents within a project using the provided search string.

**Parameters:**
- `search` (string, required): The search query string used to find relevant documents
- `validation` (string): Optional brief text used to validate content found by the search, helping reduce large documents and extract only important content

**Scope:** chat

### project_read_file

Read project file content from a relative or absolute file path.

**Parameters:**
- `file_path` (string, required): Relative or absolute path to the file to read

**Scope:** chat

### project_structure

Get the project structure with files and folders, excluding invalid files. Returns a tree-like representation of the project organization.

**Parameters:**
- `include_details` (boolean): If true, includes additional metadata like file counts and folder statistics (default: false)
- `max_depth` (integer): Maximum folder depth to traverse; null for no limit (default: null)
- `include_file_sizes` (boolean): If true, includes file sizes in bytes for each file (default: false)

**Scope:** chat

### generate_tasks_tool

Generate sub-tasks from the current chat by analyzing its context and splitting it into actionable tasks. Each sub-task becomes a separate chat connected to the parent.

**Parameters:**
- `instructions` (string): Optional additional instructions to guide task creation (e.g., "Focus on frontend tasks" or "Split by component")

**Scope:** chat | **Dual Response:** Enabled

### code_writer

Utility for writing and managing code within projects.

**Scope:** global

### code_block_generator

Utility for generating code blocks with proper formatting and syntax highlighting.

**Scope:** global

## Test Tool

A simple debugging utility that returns a test confirmation message.

## Dependencies
**Imports from:** codx/junior/tools/fetch_webpage.py, codx/junior/tools/project_tools.py, codx/junior/tools/code_writer.py
**Imported by:** codx/junior/ai/openai_ai.py, codx/junior/app.py