# ChatEngine Module Documentation

## Overview

The `ChatEngine` class is the core component for managing chat interactions with AI models in the CODX Junior system. It orchestrates message processing, knowledge search, context building, and AI response generation across various chat modes (task, agent, vibe, and standard chat).

## Key Features

### Multi-Mode Chat Processing

The engine supports four distinct chat modes:

- **Task Mode** (`CHAT_MODE_TASK`): Refines documents based on user comments
- **Agent Mode** (`CHAT_MODE_AGENT`): Enables iterative task completion with retry logic
- **Vibe Mode** (`CHAT_MODE_VIBE`): AI-driven search combining conversation history with current query
- **Standard Chat** (`CHAT_MODE_CHAT`): Direct conversation without specialized processing

### Crash Safety & Resilience

The engine implements comprehensive crash-safety mechanisms:

- **ChatEventBridge Integration**: Persists response messages on every event change, ensuring tool events and lifecycle information survive system failures
- **Streamed Content Persistence**: Throttled disk I/O of partial streamed content limits data loss to at most a few seconds
- **Hidden Reasoning Persistence**: Intermediate reasoning messages are persisted immediately upon creation
- **Error State Preservation**: Error conditions are persisted before subsequent operations that could fail

### Parent Chat Inheritance

The engine properly handles chat hierarchies through the `ignore_parent_knowledge` flag:

- When `False`, parent chat messages are included in message history
- When `True`, parent context is excluded from the conversation
- Recursive parent traversal respects the flag at each level

### Cancellation Support

Requests can be cancelled via the `CancellationToken` system:

- Tokens are registered per chat session with unique `token_id` values
- Cancellation can be triggered by chat ID or token ID
- Cancellation state is stamped into response metadata with ISO-8601 timestamps

### Session Analytics

The engine records comprehensive session metrics:

- Chat metadata (name, mode, profiles, files)
- Timing information (start time, first response delay, total duration)
- Message counts (input/output)
- Error and cancellation states

## Core Workflow

### Initialization

```python
ChatEngine(settings, event_manager, user=None)
```

The engine initializes with:
- Project settings for configuration
- Event manager for emitting chat/search events
- Optional authenticated user for session tracking
- Knowledge and ChatKnowledge instances for document search
- Analytics instance for session tracking

### Main Entry Point: `chat_with_project()`

The primary method orchestrates the complete chat interaction:

1. **Project Context Switching**: Delegates to appropriate engine if chat belongs to different project
2. **Cancellation Token Registration**: Creates unique token for in-flight request tracking
3. **User Message Extraction**: Identifies latest message and extracts query context
4. **Mode Resolution**: Determines chat mode flags and branching logic
5. **Query Mentions Resolution**: Extracts profile and project references from query
6. **File Collection**: Gathers files from all visible messages and parent chats
7. **Profile Resolution**: Determines active profiles, LLM model, and available tools
8. **Message History Building**: Constructs LangChain message list with optional parent messages
9. **Knowledge Search**: Performs RAG or pre-search based on mode
10. **AI Response Generation**: Invokes AI with assembled context and prompt
11. **Response Processing**: Extracts metadata, files, and timing information
12. **Session Recording**: Records start and end metrics for analytics
13. **Agent Iteration**: Recursively processes responses for agent mode
14. **Cancellation Cleanup**: Unregisters token on completion

## Knowledge Search

### Pre-Search (Vibe & Search Modes)

The `_run_pre_search()` method combines conversation history with current query to build richer search queries, delegating to `ChatKnowledge.ai_search_for_context()`.

### Standard RAG Search

The `_run_rag_knowledge_search()` method:
- Searches across specified projects
- Excludes specified documents
- Formats results with language-specific code fences
- Emits search events for user feedback

### Knowledge Disable Conditions

Knowledge search is disabled when:
- Explicitly disabled via invocation parameter
- No search projects are available
- Project settings disable knowledge
- User message has `disable_knowledge` flag set

## Context Building

### Message History

The `_build_message_history()` method:
- Excludes hidden and improvement messages
- Includes parent messages when `ignore_parent_knowledge=False`
- Recursively includes parent's parent messages
- Converts DB Message objects to LangChain format

### Chat Files

The `_collect_files_from_visible_messages()` helper:
- Collects files from all visible messages
- Merges with chat-level base file list
- Combines parent chat files when applicable
- Deduplicates and sorts for deterministic ordering

### File Content Loading

The `_load_chat_files_content()` method:
- Reads explicitly attached file content
- Skips files already embedded in message history
- Formats content with language-specific code fences
- Resolves file paths relative to project root

## Prompt Assembly

### Mode-Specific Prompts

- **Refine Mode**: Asks model to apply user comments to existing document
- **Agent Mode**: Instructs model to complete task with iteration limits
- **Standard Mode**: Appends user message directly

### Context Integration

The `_build_ai_prompt_messages()` method:
- Appends RAG/pre-search context as project files
- Prepends working file headers to last message
- Incorporates profile system content
- Structures prompt for optimal model performance

## Response Processing

### File Extraction

The `_extract_files_from_response()` method parses markdown code blocks in format:

```
```language filename
code content
```
```

Handles nested code fences and returns list of extracted files with language, path, and content.

### Metadata Finalization

The `_finalize_response_metadata()` method stamps response with:
- Timing metrics (total duration, first response delay)
- Model information
- Active profile names
- Extracted files list

Preserves pre-existing metadata fields like `cancellation_token_id` and `analytics`.

## Chat Description & History

### Auto-Generation

The `_generate_chat_description()` method:
- Builds clean message history excluding file contents and profiles
- Generates 5-line summaries via AI
- Maintains timestamped history entries
- Tracks context evolution over multiple turns

### Auto-Initialization

The `_auto_initialize_chat_metadata()` method:
- Auto-fills missing chat metadata for `auto_initialize` chats
- Suggests name, board, and column via AI
- Only overrides empty fields
- Clears `auto_initialize` flag on success

## Parent Chat Integration

### Message Inheritance

Parent chat messages are included when:
- Chat has `parent_id` set
- `ignore_parent_knowledge=False`
- Parent chat exists and is accessible

### Context Inheritance

The `get_chat_analysis_parents()` method:
- Traverses chat hierarchy recursively
- Collects non-hidden messages from ancestors
- Respects `ignore_parent_knowledge` flags
- Returns concatenated ancestor content

### File Inheritance

Parent chat files are merged when:
- Chat has `parent_id` set
- `ignore_parent_files=False`
- Parent file list is available

## Analytics Integration

The engine records session lifecycle events:

- **Session Start**: Recorded with initial chat metadata and profiles
- **Session End**: Recorded with duration, message counts, and error state
- **Token Usage**: Captured in response metadata
- **Tool Executions**: Attached to response message via ChatEventBridge

Sessions are keyed by chat ID and include:
- User information and project context
- Chat mode and active profiles
- File references and model information
- Timing metrics and completion status

## Error Handling

### Error Persistence

Errors are immediately persisted via ChatEventBridge to survive subsequent failures:

- AI invocation errors are caught and response content set to error message
- Error state is stamped in response metadata
- Bridge publishes error state immediately

### Cancellation Handling

Cancellation is detected via `CancelledError`:

- Cancellation timestamp is extracted or defaulted to current time
- Response state is stamped with ISO-8601 cancellation timestamp
- Partial content and events collected so far are preserved
- Message is appended if not already registered by bridge

## Profile & Tool Management

### Profile Resolution

The `_resolve_profiles_and_model()` method:
- Extracts profiles from query mentions
- Sorts profiles by name for consistent ordering
- Builds system prompt content from profile instructions
- Collects available tools from all active profiles
- Resolves LLM model from profile when chat model not specified

### Tool Integration

Tools from profiles are:
- Deduplicated across multiple profiles
- Passed to AI invocation
- Logged with source profile information
- Included in request headers as tags

## File Path Resolution

The `_resolve_chat_file_path()` method:
- Validates absolute and relative file paths
- Resolves relative paths against project root
- Returns normalized full path or None if unresolvable
- Logs resolution process for debugging

## Helper Methods

### Message Conversion

`convert_message()` converts DB Message objects to LangChain format:
- Handles text-only messages as HumanMessage/AIMessage
- Processes image messages with URL and alt text
- Maintains message role information

### Document Formatting

`_document_to_context()` formats documents for prompt:
- Extracts language from source file extension
- Maps extensions to language parser names
- Wraps content with file path and context markers

### Query Mentions

`get_query_mentions()` extracts mentions from query:
- Identifies @profile references
- Identifies @project references
- Collects file profiles from attached files
- Returns structured QueryMentions object

### Search Projects

`get_all_search_projects()` returns comprehensive project list:
- Includes current project
- Includes child projects
- Includes project dependencies

## Configuration & Dependencies

The engine depends on:

- `CODXJuniorSettings`: Project configuration
- `ChatManager`: Chat persistence and retrieval
- `Knowledge`: Vector-based document search
- `ChatKnowledge`: AI-enhanced knowledge searching
- `ProfileManager`: Profile management and resolution
- `AI`: LLM integration
- `Analytics`: Session metric recording
- `ChatEventBridge`: Event persistence and streaming
- `AgentRunContext`: Runtime context for tool execution

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/ai/cancellation.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/profiles/profile_manager.py, codx/junior/profiling/profiler.py, codx/junior/settings.py, codx/junior/utils/chat_utils.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/chat/chat_knowledge.py
**Imported by:** codx/junior/engine/chat_engine_actions.py, codx/junior/mentions/mention_manager.py, codx/junior/tools/code_writer.py, tests/chat/test_chat_manager.py