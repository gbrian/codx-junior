# Content Formatter Module Documentation

## Overview

The Content Formatter Module provides shared utility functions for formatting documents and chat messages into structured context blocks. These utilities are used across ChatEngine and ChatEngineActions to ensure consistent content extraction and formatting throughout the codebase.

## Key Functions

### format_document_to_context()

Converts a LangChain Document object into a structured context block suitable for AI consumption.

**Purpose:** Extracts language information from document metadata and wraps content in a markdown code fence with file path annotation.

**Parameters:**
- `doc` (Document): A LangChain Document with page_content and metadata

**Returns:** Formatted context string with `### FILE CONTEXT` header and code fence

**Behavior:**
- Extracts source path from metadata
- Resolves language from metadata or file extension
- Maps language against `LANGUAGE_PARSER_MAPPING` for normalization
- Wraps content in markdown code fence with language syntax highlighting

**Example Output:**
```
### FILE CONTEXT
File path is 'src/main.py', use same file path in your response.

```python src/main.py
def hello():
    print("world")
```
```

### format_message_to_context()

Formats individual chat messages into context blocks with consistent structural patterns.

**Purpose:** Creates standardized message context blocks for inclusion in larger context compilations.

**Parameters:**
- `message` (Message): The chat message to format
- `include_role` (bool, default=True): Whether to include the message role in the header
- `include_metadata` (bool, default=False): Whether to include message metadata (files, profiles, etc.)

**Returns:** Formatted message context string

**Features:**
- Wraps message content with message delimiters (`<message>` tags)
- Optionally includes role information (user, assistant, etc.)
- Optionally appends file and profile metadata

### format_chat_messages_to_context()

Consolidates multiple chat messages into a single formatted context block.

**Purpose:** Primary method used by ChatEngineActions.generate_tasks() to extract full chat content without relying on summarization.

**Parameters:**
- `messages` (List[Message]): List of Message objects from a chat
- `exclude_hidden` (bool, default=True): Skips messages with hide=True flag
- `exclude_improvements` (bool, default=True): Skips messages with improvement=True flag

**Returns:** Formatted concatenated context string for all visible messages

**Filtering:** Messages are filtered based on visibility flags before formatting, allowing control over which messages are included in the context.

### format_chat_content_for_task_generation()

Specialized formatting function designed specifically for task generation workflows.

**Purpose:** Combines parent context, full chat messages, and the latest user request in a structured format that preserves context for accurate task decomposition.

**Parameters:**
- `chat_messages` (List[Message]): Messages from the current chat
- `parent_content` (str, default=""): Concatenated content from parent chats if applicable
- `last_message_content` (str, default=""): The latest user message content

**Returns:** Formatted content string ready for task generation AI prompt

**Structure:** Organizes content into three distinct sections:
1. `<parent_context>` - Parent chat messages (if present)
2. `<chat_history>` - Full chat message history with filtering applied
3. `<main_task>` - Latest user request (if present)

## Usage Pattern

These functions follow a consistent structural pattern with section headers (prefixed with `###`) and content delimiters to create clear, parseable context blocks for AI models. The formatting ensures that formatted content maintains proper hierarchy and is easily distinguishable in larger prompt contexts.