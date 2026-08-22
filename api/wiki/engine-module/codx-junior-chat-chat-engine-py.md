# ChatEngine Documentation

## Overview

The `ChatEngine` is the core component of the CODX Junior API responsible for managing chat interactions with AI models. It orchestrates context gathering, knowledge search, AI response generation, and multi-iteration agent processing. The engine integrates comprehensive analytics tracking for complete request-response traceability.

## Initialization

```python
ChatEngine(settings, event_manager, user=None)
```

The ChatEngine is initialized with:
- **settings**: Project-specific configuration (CODXJuniorSettings)
- **event_manager**: Manager for emitting chat and search events
- **user**: Optional authenticated user for the session (CodxUser)

The initialization also sets up:
- Knowledge management system for document retrieval
- Chat knowledge handler for AI-driven search
- Analytics instance for session tracking

## Core Features

### Chat Modes

The engine supports four distinct chat modes:

- **chat**: Standard conversational mode
- **task** (refine): Document refinement mode that applies comments to existing documents
- **agent**: Multi-iteration mode where the AI autonomously completes tasks
- **vibe**: AI-assisted context search mode

### Message Processing

The engine processes chat interactions through a structured workflow:

1. **Message Validation**: Filters hidden and improvement messages from the history
2. **Context Collection**: Gathers files referenced across visible messages
3. **Profile Resolution**: Determines active profiles, models, and available tools
4. **Knowledge Search**: Performs RAG document search or AI-driven pre-search
5. **Prompt Assembly**: Builds the final message list with context and mode-specific instructions
6. **AI Invocation**: Sends assembled messages to the configured AI model
7. **Response Processing**: Extracts files, timing metadata, and conversation summaries

### Cancellation Support

The engine implements request cancellation through a `CancellationToken` registry:

- Tokens are registered at the root iteration and unregistered after completion
- Each token carries a unique UUID that is stamped into response metadata immediately
- Cancellation can be triggered by chat document ID or token ID
- Cancelled requests set a `cancelled_at` timestamp in response metadata

See: [Cancellation Token Registration](#cancellation-token-registration)

### Knowledge Integration

The engine integrates two knowledge search mechanisms:

- **Standard RAG Search**: Document retrieval across specified projects
- **AI-Driven Pre-Search**: Uses conversation history to build richer search queries in vibe/search modes

Knowledge search is disabled when:
- Explicitly disabled via `disable_knowledge` parameter
- No search projects are found
- Project settings disable knowledge usage
- User message has `disable_knowledge` flag set

## Main Entry Point

### chat_with_project()

```python
async def chat_with_project(
    chat: Chat,
    disable_knowledge: bool = False,
    callback = None,
    append_references: bool = True,
    chat_mode: str = None,
    iteration: int = 0,
    system: str = None
)
```

The primary method for processing chat interactions. Returns a tuple of (updated Chat, list of Documents).

**Key Behaviors**:

- **Project Switching**: If the chat belongs to a different project, delegates to a switched ChatEngine instance
- **Token Registration**: Registers a cancellation token only at root iteration (iteration == 0) to avoid replacing active tokens during recursion
- **Mode Determination**: Resolves chat mode from explicit override, chat object, or defaults to standard chat
- **Context Building**: Collects files from all visible messages, not just the current user message
- **File Merging**: Incorporates files from parent chats unless `ignore_parent_files` is set
- **Analytics Recording**: Captures session start/end with comprehensive metrics
- **Agent Recursion**: Automatically recurses for agent mode until task completion or iteration limit

See: [Internal Implementation Details](#internal-implementation-details)

## Helper Methods

### Profile and Model Resolution

#### _resolve_profiles_and_model()

Derives active profiles, LLM model, tool list, and system prompt content from query mentions. Profiles are sorted by name and their content is formatted for the AI system prompt.

**Returns**:
- `chat_profiles_system_content`: Formatted profile instructions
- `chat_profile_names`: List of active profile names
- `chat_model`: Selected LLM model
- `chat_tools`: Combined list of tools from all profiles
- `is_refine`: Updated refinement mode flag

### Knowledge Search Methods

#### _run_pre_search()

Executes AI-driven pre-search for vibe and search modes. Combines conversation history with the current query to build a richer search query.

**Returns**: Tuple of (documents, file_list, context_string)

#### _run_rag_knowledge_search()

Performs standard RAG document search across specified projects. Logs search queries and handles errors gracefully.

**Returns**: Tuple of (documents, file_list, context_string)

### Context Building

#### _build_ai_prompt_messages()

Assembles the final LangChain message list for AI invocation. Appends context, working-file content, and mode-specific prompts.

**Handles**:
- Context messages with project files
- Refinement prompts for task mode
- Agent iteration prompts with remaining iteration counts
- Working file content prepending

#### _load_chat_files_content()

Reads and formats content of explicitly attached chat files. Skips files already embedded in message history to avoid duplication.

#### _document_to_context()

Converts a Document to a formatted context string with language-specific code fence. Uses the LANGUAGE_PARSER_MAPPING for proper syntax highlighting.

### Mode-Specific Message Building

#### _append_refine_message()

Creates a task-refinement prompt. If a previous AI document exists, asks the model to apply comments to it. Incorporates parent context unless `ignore_parent_knowledge` is set.

**Includes**:
- Task document header from answer messages
- Parent document context (if available)
- Existing document with comment application instructions

#### _append_agent_message()

Creates an agent-style prompt instructing the model to complete a task autonomously. Includes parent context and iteration count information.

**Content**:
- Task name and objective
- Parent context (if available)
- User request
- Remaining iteration count
- Completion indicator (AGENT_DONE_WORD)

### Response Processing

#### _execute_ai_response()

Invokes the appropriate AI or search handler and extracts response parts. Handles both standard AI chat and knowledge search requests.

**Returns**: Tuple of (think_content, response_content, extra_files, ai_chat_fn)

**Error Handling**: Catches ValueError, RuntimeError, and OSError, returning error messages in the response content.

#### _extract_files_from_response()

Extracts code blocks with filenames from AI response content. Parses markdown code blocks in the format:

```
```language filename
code content
```
```

Handles nested code fences and returns a list of dictionaries with language, file_path, and content.

#### _finalize_response_metadata()

Stamps the response message with:
- Timing information (time_taken, first_chunk_time_taken)
- AI model name
- Active profile names
- Extracted file references

Merges user message metadata without overwriting existing response metadata fields.

### Conversation Summary

#### _generate_chat_description()

Generates a short summary of the conversation using AI, excluding profile content and file details. The summary is stored in the chat object and a timestamped history entry is created.

**Process**:
1. Builds clean message history excluding system prompts and file content
2. Converts messages to LangChain format
3. Invokes AI with summary prompt
4. Updates chat description and maintains history entries

**Error Handling**: Logs exceptions without interrupting the chat flow.

#### _build_clean_message_history_for_description()

Creates a cleaner conversation history suitable for summaries. Filters out:
- Hidden and improvement messages
- Project file context markers
- Knowledge search processing messages
- System prompt content

### Auto-Initialization

#### _auto_initialize_chat_metadata()

Uses AI to auto-fill missing chat metadata (`name`, `board`, `column`) for chats marked with `auto_initialize` flag.

**Behavior**:
- Only processes if `chat.auto_initialize` is True
- Asks AI to suggest metadata values based on conversation content
- Only overwrites currently empty fields
- Clears the `auto_initialize` flag on success
- Logs exceptions without interrupting chat flow

### Analytics Recording

#### _record_chat_session_start()

Records the start of a chat session with initial context including:
- Chat identification (id, name)
- User information
- Project details
- Chat mode and profiles
- File and iteration information
- Input message count

Called only at root iteration (iteration == 0).

#### _record_chat_session_end()

Records the end of a chat session with final metrics:
- Duration in seconds
- Final message counts (user and assistant)
- Cancellation status
- Error information
- Iteration count

Called only at root iteration (iteration == 0).

## Helper Utilities

### Message Management

#### _new_chat_message()

Factory method creating a new Message with a generated UUID doc_id.

#### _build_message_history()

Converts all non-hidden, non-improvement chat messages (excluding the last) into LangChain message objects.

#### convert_message()

Static method converting DB Message objects to LangChain types. Handles:
- Text-only messages (HumanMessage or AIMessage)
- Image messages with base64 or URL content
- Role-based message type selection

### File Resolution

#### _collect_files_from_visible_messages()

Collects and deduplicates file references from visible messages plus chat-level base files. Returns a sorted list for deterministic ordering.

#### _resolve_chat_file_path()

Resolves the full filesystem path of a chat-attached file. Returns None and logs a warning if unresolvable.

### Mode Flag Resolution

#### _resolve_chat_mode_flags()

Resolves boolean flags driving branching logic from chat mode and task item. Returns a dictionary with:
- `chat_mode`: Resolved mode string
- `is_refine`: Boolean for task mode
- `is_agent`: Boolean for agent mode
- `is_vibe`: Boolean for vibe mode
- `is_search`: Boolean for search task item
- `needs_pre_search`: Boolean for vibe or search modes

### Knowledge Evaluation

#### _evaluate_knowledge_flags()

Determines whether knowledge search should be disabled. Emits events for each disable condition:
- Explicit disable parameter
- No search projects found
- Project settings disabled
- User message flag set

### Other Utilities

#### get_profile_manager()

Returns a ProfileManager instance for the current settings.

#### get_chat_manager()

Returns a ChatManager, optionally scoped to a specific project by project_id.

#### switch_project()

Switches to another project based on project ID. Reinitializes ChatKnowledge for the new project context.

#### get_ai()

Gets an AI instance configured for a specific model with optional system prompt override.

#### get_ai_code_generator_changes()

Processes AI response string to generate code changes. Normalizes file paths to absolute project paths.

#### get_query_mentions()

Extracts mentions of profiles and projects from user queries. Resolves file-based profiles and merges with chat-level profiles.

#### get_chat_analysis_parents()

Traverses all parent chats and returns concatenated non-hidden message content. Follows the parent chain recursively.

#### index_chat()

Indexes a chat as a Document in the knowledge system. Converts valid messages into a single Document with appropriate metadata.

#### get_all_search_projects()

Returns all projects including child projects and dependencies for comprehensive knowledge search.

## Cancellation Management

### cancel_chat()

```python
def cancel_chat(chat_doc_id: str) -> bool
```

Cancels an in-flight chat request by chat document ID.

### cancel_chat_by_token_id()

```python
def cancel_chat_by_token_id(token_id: str) -> bool
```

Cancels an in-flight chat request by cancellation token UUID. This is the preferred method when the token_id is available from response metadata.

## Internal Implementation Details

### Cancellation Token Registration

The `chat_with_project()` method registers a CancellationToken only at the root iteration (iteration == 0) to avoid replacing an already-registered token during agent recursion. The token ID is immediately stamped into response metadata so clients receive it in the first streaming event.

If a cancellation occurs, the `_chat_with_project_inner()` method catches the `CancelledError`, records a session end event, and returns the partially completed chat with `cancelled_at` timestamp in metadata.

### Context Building Workflow

The engine builds context through multiple stages:

1. **File Collection**: Gathers files from all visible messages and query mentions
2. **Parent Context Merging**: Incorporates parent chat files unless ignored
3. **Chat File Loading**: Reads explicitly attached file content
4. **Pre-Search**: Optional AI-driven search in vibe/search modes
5. **RAG Search**: Standard knowledge base search in non-search modes
6. **Context String Assembly**: Concatenates all search results into a project_files context block

### Message Assembly

The final prompt to AI includes:

1. **History**: Previous turns excluding hidden and improvement messages
2. **Context**: Project files from knowledge search
3. **Mode Prompt**: Mode-specific instructions (refine/agent/standard)
4. **Working Files**: Explicitly attached chat files

Each component is conditionally included based on chat mode and configuration.

### Agent Iteration

Agent mode enables autonomous task completion through iteration:

1. Check if response contains AGENT_DONE_WORD
2. If not done and iterations remain, recursively call `_chat_with_project_inner()`
3. Reuse the same cancellation token throughout the iteration chain
4. Record analytics only at root iteration (before first and after final iteration)

## Event Management

The engine emits events through the event_manager at key points:

- **chat_event()**: Logs chat progress, searches, and status updates
- **message_event()**: Streams partial and final response content with current metadata

Events include context information such as active profiles, search queries, document counts, and error messages.

## Error Handling

The engine implements graceful error handling:

- **OSError**: Logged and wrapped in event messages
- **ValueError/RuntimeError**: Caught during AI invocation and search operations
- **CancelledError**: Handled specially with cancellation metadata recording
- **JSONDecodeError**: Caught during chat initialization metadata parsing
- **Exceptions in summary generation**: Logged without interrupting chat flow

All errors are reported to the event_manager and included in analytics records when applicable.

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/ai/cancellation.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/profiles/profile_manager.py, codx/junior/profiling/profiler.py, codx/junior/settings.py, codx/junior/utils/chat_utils.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/chat/chat_knowledge.py
**Imported by:** codx/junior/engine/chat_engine_actions.py, codx/junior/mentions/mention_manager.py, codx/junior/tools/code_writer.py, tests/chat/test_chat_manager.py