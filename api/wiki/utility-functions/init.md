# Codx-Junior Tools API

## Overview
The `tools` module aggregates all available tools for chat and project interactions within the codx-junior API. Tools are organized as callable functions with associated metadata designed for seamless integration with language models and the API. Each tool definition includes a JSON schema describing its name, description, parameters, and execution settings.

## Architecture & Concepts
The module implements a structured approach to tool management, defining how tools are categorized and how they return data.

### Tool Scope Levels
Tools are assigned a scope level that dictates their availability within the application:
*   **`global`**: Tools that are always included in conversations (e.g., `code_block_generator`).
*   **`chat`**: Tools available based on conversation context and user selection.
*   **`profile`**: Tools available based on user profile or role.

### Tool Response Types
Tools return data in one of two formats:
*   **`str`**: Traditional single-string response, primarily used for providing context to the LLM.
*   **`ToolResponse`**: A dual-return object used by tools that need to produce both user-facing content and specific feedback for the LLM. See the [Tool Registry](#tool-registry) for tools utilizing this format.

## Tool Registry
All available tools are registered in the `TOOLS` list. Each entry in this registry contains:
*   `tool_json`: The OpenAI-compatible function schema (`type`, `function.name`, `function.description`, `function.parameters`).
*   `settings`: Execution metadata including `async` status, `scope`, `dual_response` flag, and project/session requirements.
*   `tags`: Categorical tags for filtering and organization.
*   `tool_call`: The actual callable Python function.

For a complete list of registered tools, refer to the [Tool Catalog](#tool-catalog).

## Tool Catalog
The following tools are currently exported and registered in the API:

### `fetch_webpage`
Fetches a webpage and converts it to markdown format.
*   **Parameters**:
    *   `url` (string, required): The URL of the webpage to fetch.
    *   `include_images` (boolean): Whether to include image references in the markdown.
    *   `max_length` (integer): Maximum length of the output markdown.
    *   `headers` (object): Optional HTTP headers for the request.
*   **Settings**: Scope: `chat`, Async: `False`.

### `project_search`
Searches for documents within a project using one or more queries. Supports bulk operations for efficiency.
*   **Parameters**:
    *   `search` (string or array, required): Single query string or list of query strings. Combining related queries reduces tool calls.
    *   `validation` (string, optional): Text used to validate and filter results, extracting only important content.
*   **Settings**: Scope: `chat`, Dual Response: `True`, Project Settings: `True`.
*   **Tags**: `project`, `search`, `navigation`, `discovery`.

### `project_read_file`
Reads content from one or multiple file paths. Supports relative/absolute paths, glob patterns, and bulk operations.
*   **Parameters**:
    *   `file_path` (string or array, required): Single path or list of paths. Invalid/missing files are returned as error blocks.
*   **Settings**: Scope: `chat`, Dual Response: `True`, Project Settings: `True`.
*   **Tags**: `project`, `file-operations`, `read`, `content-access`.

### `project_write_file`
Writes content to a project file, creating the file or directory if it does not exist.
*   **Parameters**:
    *   `file_path` (string, required): Relative or absolute path to the file.
    *   `content` (string, required): The content to write.
*   **Settings**: Scope: `chat`, Dual Response: `True`, Project Settings: `True`.
*   **Tags**:

## Dependencies
**Imports from:** codx/junior/tools/fetch_webpage.py, codx/junior/tools/project_tools.py, codx/junior/tools/code_writer.py
**Imported by:** codx/junior/ai/openai_ai.py, codx/junior/app.py