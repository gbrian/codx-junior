# ChatEngine Documentation

## Overview

The `ChatEngine` is the core component of the CODX Junior chat system, responsible for orchestrating all chat interactions with AI models. It handles message processing, knowledge retrieval, context building, and response generation across multiple chat modes with comprehensive crash-safety and analytics tracking.

## Key Features

### Multi-Mode Support
The engine supports four primary chat modes:
- **chat**: Standard conversational mode
- **task**: Task refinement mode for document improvement
- **agent**: Iterative agent mode with multiple attempts
- **vibe**: AI-driven search mode for context discovery
- **tutorial**: Tutorial mode (similar to task mode)

### Crash-Safety Guarantees

The engine implements multiple layers of crash protection:

1. **Response Message Persistence**: The response message is created and persisted before the AI call, ensuring metadata and partial content survive crashes
2. **Event Bridge Integration**: Tool events and lifecycle events are attached to the response message and persisted on every change
3. **Streamed Content**: Partial streamed content is throttled and persisted from the streaming callback
4. **Hidden Reasoning**: Intermediate reasoning messages are persisted immediately as they're produced
5. **Error State**: Response message errors are persisted immediately via the event bridge

### Cancellation Support

A `CancellationToken` is registered for each chat turn, keyed by `chat.doc_id`. The token's unique ID is stamped into response metadata for client-side cancellation:
- Cancel by chat ID: `CANCELLATION_REGISTRY.cancel(chat_doc_id)`
- Cancel by token ID: `CANCELLATION_REGISTRY.cancel_by_token_id(token_id)`

### Analytics Integration

Session-level analytics track:
- Chat metadata and profiles
- Token usage and timing
- Tool executions and errors
- User and project information
- Cancellation and failure states

## Initialization

```python
engine = ChatEngine(
    settings=CODXJuniorSettings,
    event_manager=event_manager,
    user=CodxUser  # Optional authenticated user
)
```

The engine initializes:
- Knowledge base instance for document search
- Chat knowledge instance for AI-driven search
- Analytics instance for session tracking

## Main Processing Flow

### Entry Point: `chat_with_project()`

The main async method processes a chat interaction with the following sequence:

1. **Project Validation**: Verifies the chat belongs to the current project context; switches if needed
2. **Cancellation Token Registration**: Registers a token at iteration 0 for tracking and cancellation
3. **Response Message Creation**: Creates and stamps the response message early with cancellation token ID
4. **Event Bridge Binding**: Binds `ChatEventBridge` to attach tool/lifecycle events
5. **Context Resolution**: Resolves profiles, files, and search projects from query mentions
6. **Message History Building**: Constructs LangChain messages from chat history, including parent messages if applicable
7. **Knowledge Search**: Executes pre-search (vibe/search modes) and RAG document search
8. **Prompt Assembly**: Builds final prompt with context, working files, and mode-specific instructions
9. **AI Execution**: Invokes AI with streaming callback and run context
10. **Response Processing**: Extracts files, updates metadata, and persists final state
11. **Post-Processing**: Generates descriptions and auto-initializes metadata if needed
12. **Agent Iteration**: Recursively calls for agent mode if task not complete and iterations remain

### Chat Mode Flags

The engine resolves mode flags via `_resolve_chat_mode_flags()`:
- `is_refine`: Task or tutorial mode requires document refinement
- `is_agent`: Agent mode enables iterative task completion
- `is_vibe`: Vibe mode triggers AI-driven pre-search
- `is_search`: Pure knowledge search mode
- `needs_pre_search`: Vibe or search modes need initial context retrieval

## Message History Management

### Building History with Parent Messages

The `_build_message_history()` method:
1. Checks for parent chat and `ignore_parent_knowledge` flag
2. Recursively includes parent messages if flag is False
3. Filters out hidden and improvement messages
4. Converts to LangChain message format

Tool and lifecycle events on response messages are NOT converted to prompt content.

### Parent Context Traversal

The `get_chat_analysis_parents()` method:
- Traverses the parent chat hierarchy upward
- Respects `ignore_parent_knowledge` flag at each level
- Stops traversal when flag is True
- Concatenates all ancestor message content

## Knowledge Search

### Pre-Search (Vibe/Search Modes)

`_run_pre_search()` executes AI-driven search:
1. Combines conversation history with current query
2. Delegates to `ChatKnowledge.ai_search_for_context()`
3. Returns documents, file list, and formatted context

### RAG Knowledge Search

`_run_rag_knowledge_search()` performs standard document retrieval:
1. Validates query and search projects
2. Creates enhanced search query from history
3. Selects relevant documents from knowledge base
4. Formats documents as code blocks with metadata
5. Handles search errors gracefully

## Profile Resolution

The `_resolve_profiles_and_model()` method:
1. Collects profiles from query mentions
2. Sorts profiles by name for consistency
3. Builds system prompt content from profile instructions
4. Collects available tools from all profiles
5. Sets chat model from first profile with model override
6. Enables refine mode if any profile specifies it

## AI Response Execution

### Key Characteristics

`_execute_ai_response()`:
- Handles search requests via `KnowledgeAISearch`
- Executes standard AI chat with run context
- Persists hidden reasoning messages immediately
- Catches errors and stamps error state on response
- Returns think content, main content, and extracted files

### Error Handling

Model parameter errors are caught and formatted via `_build_friendly_error_message()`:
- Extracts API error details from response
- Provides user-friendly parameter constraint messages
- Falls back to generic error messages

## Response Metadata

### File Extraction

`_extract_files_from_response()` parses markdown code blocks:
- Format: ` ```language filename`
- Handles nested code fences with depth tracking
- Extracts language, file path, and content
- Returns list of file dictionaries

### Metadata Finalization

`_finalize_response_metadata()` stamps response with:
- Execution timing (start time, first chunk time)
- Model information
- Profile names
- Extracted files list
- Preserves pre-existing fields like `cancellation_token_id` and `analytics`

## Post-Processing

### Chat Description Generation

`_generate_chat_description()` creates summaries:
1. Builds clean message history without system content
2. Calls AI with "Create a 5 lines summary" prompt
3. Updates `chat.description`
4. Appends timestamped history entry
5. Handles failures gracefully

### Auto-Initialization

`_auto_initialize_chat_metadata()` for auto_initialize chats:
1. Calls AI with metadata suggestion prompt
2. Parses JSON response for name, board, column
3. Only overwrites empty fields
4. Clears `auto_initialize` flag on success

### Task Mode Cleanup

`_hide_non_answer_messages()` in task mode:
- Hides all prior messages not marked as answers
- Keeps only answer-type messages visible

## Analytics Recording

### Session Start

`_record_chat_session_start()` captures:
- Chat metadata and names
- User and project information
- Active profiles and files
- Iteration and model information
- Parent chat relationship

### Session End

`_record_chat_session_end()` records:
- Duration and message counts
- Cancellation and error state
- Final iteration number
- Output message count

## Helper Methods

### Message Creation

`_new_chat_message()`: Factory method creating messages with auto-generated doc_id

### File Handling

- `_collect_files_from_visible_messages()`: Gathers files from all visible messages with deduplication
- `_load_chat_files_content()`: Reads and formats explicitly attached file content
- `_resolve_chat_file_path()`: Resolves relative/absolute file paths

### Message Conversion

`convert_message()`: Converts DB Message to LangChain format:
- Text-only messages to HumanMessage/AIMessage
- Image messages with URL references
- Handles JSON-encoded image metadata

### Query Processing

`get_query_mentions()`: Extracts profiles and projects:
1. Resolves profiles from message or chat
2. Adds file-associated profiles
3. Uses `ChatUtils` to parse mentions
4. Returns `QueryMentions` object

## Project Management

### Project Switching

`switch_project()`: Switches engine context:
- Validates project ID
- Updates settings
- Reinitializes `ChatKnowledge`
- Logs context switch

### Project Relationships

`get_all_search_projects()`: Returns hierarchical projects:
- Current project
- Child projects
- Project dependencies

## Knowledge Indexing

`index_chat()`: Indexes chat as document:
1. Filters valid (non-hidden) messages
2. Creates Document with chat metadata
3. Persists to knowledge base
4. Handles indexing errors

## Configuration

### AI Instance

`get_ai()`: Creates configured AI instance:
- Accepts optional model override
- Accepts optional system prompt
- Returns fully configured `AI` instance

### AI Code Generation

`get_ai_code_generator_changes()`: Processes AI response:
1. Parses response via `AICodeGenerator`
2. Normalizes file paths to absolute
3. Returns code change object

## Cancellation Methods

### Public Cancellation Interface

- `cancel_chat(chat_doc_id)`: Cancel by chat ID
- `cancel_chat_by_token_id(token_id)`: Cancel by token UUID

Both methods delegate to `CANCELLATION_REGISTRY` and log results.

## Error Handling

The engine implements comprehensive error handling:
- Logs exceptions with full context
- Preserves error state in response message
- Emits error events to event manager
- Gracefully degrades on knowledge search failures
- Handles metadata generation failures without blocking

## Integration Points

### External Dependencies

- **AI Module**: Language model integration with streaming
- **ChatManager**: Database persistence and retrieval
- **ProfileManager**: Profile configuration management
- **ChatKnowledge**: AI-driven search operations
- **Analytics**: Session and token tracking
- **ChatEventBridge**: Event attachment and persistence
- **AgentRunContext**: Tool execution and lifecycle tracking
- **CancellationRegistry**: Token management for request cancellation

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/ai/cancellation.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/profiles/profile_manager.py, codx/junior/profiling/profiler.py, codx/junior/settings.py, codx/junior/utils/chat_utils.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/chat/chat_knowledge.py
**Imported by:** codx/junior/engine/chat_engine_actions.py, codx/junior/mentions/mention_manager.py, codx/junior/tools/code_writer.py, tests/chat/test_chat_manager.py