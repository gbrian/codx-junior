# Tools Module Documentation

## Overview

The Tools module is a centralized hub for all available tools in the codx-junior API. It aggregates callable functions with associated metadata for seamless integration with language models and API endpoints. Tools are designed to extend chat capabilities and enable project interactions.

## Tool Organization

Tools are organized by scope level, which determines their availability:

- **global**: Always included in conversations (e.g., `code_block_generator`)
- **chat**: Available based on conversation context and user selection
- **profile**: Available based on user profile or role

## Response Types

Tools support two response formats:

- **str**: Traditional single-string response for LLM context integration
- **ToolResponse**: Dual-return object for tools requiring both user-facing content and LLM feedback

## Available Tools

### Web Tools

#### fetch_webpage
Retrieves and converts webpage content to markdown format.

**Parameters:**
- `url` (string, required): The webpage URL
- `include_images` (boolean): Include image references in markdown output
- `max_length` (integer): Limit markdown output length
- `headers` (object): Optional HTTP headers for the request

**Scope:** Chat

---

### Project Tools

#### project_search
Search for documents within a project using one or more queries.

**Key Feature:** Bulk operation support—provide multiple queries as a list to reduce tool calls.

**Parameters:**
- `search` (string or array, required): Single query or list of queries
- `validation` (string): Optional text to validate and filter results from large documents

**Scope:** Chat | **Dual Response:** Yes

#### project_read_file
Read content from one or multiple project files.

**Key Feature:** Bulk operation support—read multiple files in one call by providing a path list instead of separate calls.

**Parameters:**
- `file_path` (string or array, required): Single file path or list of paths. Supports relative/absolute paths and glob patterns

**Scope:** Chat | **Dual Response:** Yes

#### project_write_file
Write or create content in a project file. Creates directories if needed.

**Parameters:**
- `file_path` (string, required): Relative or absolute file path
- `content` (string, required): Content to write

**Scope:** Chat | **Dual Response:** Yes

#### project_structure
Retrieve the project structure with files and folders in tree-like format.

**Parameters:**
- `include_details` (boolean): Add metadata like file counts and statistics
- `max_depth` (integer): Maximum folder depth to traverse
- `include_file_sizes` (boolean): Include file sizes in bytes

**Scope:** Chat

---

### Code Tools

#### code_writer
Code generation and manipulation tool for project development.

**Scope:** Global

#### code_block_generator
Generate code blocks with proper formatting and syntax highlighting.

**Scope:** Global

#### apply_file_changes
Safely apply batch search-and-replace edits to existing text files.

**Key Features:**
- Validates all changes before writing
- Requires exact text matching (one match per search string)
- Preserves file if any change conflicts
- Requires explicit indentation in search and replace strings

**Parameters:**
- `file_path` (string, required): File to modify
- `changes` (array, required): List of change objects with `search` and `replace` keys

**Scope:** Chat | **Dual Response:** Yes

---

### Task Generation

#### generate_tasks_tool
Generate actionable sub-tasks from current chat context.

**Parameters:**
- `instructions` (string): Optional guidance for task creation (e.g., "Focus on frontend tasks")

**Scope:** Chat | **Dual Response:** Yes

---

### Image Tools

#### explain_image
Analyze image content using Vision API.

**Parameters:**
- `image_base64` (string, required): Base64-encoded image (PNG, JPG, etc.). Prefix optional.

**Scope:** Chat

#### generate_image
Generate images from text prompts using DALL-E.

**Parameters:**
- `prompt` (string, required): Image description (max 4000 characters)
- `size` (string): Dimensions—256x256, 512x512, 1024x1024, 1024x1792, or 1792x1024 (default: 1024x1024)
- `quality` (string): 'standard' or 'hd' (default: standard)

**Scope:** Chat

---

## Best Practices

### Bulk Operations
Several tools support bulk operations for efficiency:
- **project_search**: Combine multiple related queries in one call
- **project_read_file**: Read multiple files in a single call instead of separate requests

### File Changes with apply_file_changes
- Include sufficient surrounding context to ensure unique matching
- Explicitly include indentation in search and replace strings
- Do not rely on automatic indentation preservation

### Image Processing
- For `explain_image`: Provide base64-encoded images with optional data URI prefix
- For `generate_image`: Use descriptive prompts for better results

## Dependencies
**Imports from:** codx/junior/tools/fetch_webpage.py, codx/junior/tools/project_tools.py, codx/junior/tools/code_writer.py
**Imported by:** codx/junior/ai/openai_ai.py, codx/junior/app.py