# Tools Module

The tools module aggregates all available tools for chat and project interactions within the codx-junior API. Tools are organized as callable functions with associated metadata for seamless integration with language models and the API.

## Tool Scope Levels

Tools are categorized by their availability scope:

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
- `validation` (string): Optional brief text used to validate the content found by the search. This helps reduce large documents and extract only important content

**Scope:** chat

### project_read_file

Allows reading project file content from a relative or absolute file path.

**Parameters:**
- `file_path` (string, required): Relative or absolute path to the file to read

**Scope:** chat

### generate_tasks_tool

Generate sub-tasks from the current chat by analyzing its context and splitting it into actionable tasks. Each sub-task becomes a separate chat connected to the parent.

**Parameters:**
- `instructions` (string): Optional additional instructions to guide task creation (e.g., 'Focus on frontend tasks' or 'Split by component')

**Scope:** chat  
**Response Type:** Dual response (ToolResponse)

## Exports

The module exports the following for external use:

- `TOOLS`: Complete tool definitions and configurations
- `ToolResponse`: Response model for dual-return tools
- All individual tool functions: `fetch_webpage`, `project_search`, `project_read_file`, `project_write_file`, `code_writer`, `code_block_generator`, `generate_tasks_tool`

## Dependencies
**Imports from:** codx/junior/tools/fetch_webpage.py, codx/junior/tools/project_tools.py, codx/junior/tools/code_writer.py
**Imported by:** codx/junior/ai/openai_ai.py, codx/junior/app.py