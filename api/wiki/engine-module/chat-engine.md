# ChatEngine Documentation

## Overview

The `ChatEngine` is the core component responsible for managing chat interactions with AI models in the CODX Junior system. It orchestrates message processing, knowledge search, context building, and AI response generation across multiple chat modes while ensuring crash-safety through continuous state persistence.

## Key Features

### Multi-Mode Chat Support

The engine supports four distinct chat modes:

- **chat**: Standard conversation mode
- **task** (refine): Document refinement mode where the AI applies comments to existing documents
- **agent**: Iterative task completion mode with configurable maximum iterations
- **vibe**: Discovery mode using AI-driven search for context

### Crash-Safety Architecture

The engine implements comprehensive crash-safety mechanisms:

- **ChatEventBridge Integration**: Persists the response message on every event change (tool executions, lifecycle events)
- **Stream Throttling**: Streamed partial content is persisted at throttled intervals via `maybe_persist_stream()`
- **Immediate Error Persistence**: Response messages with errors are persisted immediately before subsequent operations
- **Hidden Reasoning Persistence**: Multi-step reasoning messages are persisted the moment they are appended

### Cancellation Support

A global `CANCELLATION_REGISTRY` enables cancellation of in-flight requests via:
- Chat document ID: `CANCELLATION_REGISTRY.cancel(chat.doc_id)`
- Token ID: `CANCELLATION_REGISTRY.cancel_by_token_id(token_id)`

The cancellation token ID is stamped into response metadata immediately and sent with every streaming event.

### Analytics Integration

The engine tracks chat sessions with comprehensive metrics:
- Session start/end timestamps and duration
- Message counts (input/output)
- Model and profile usage
- Iteration tracking for agent mode
- Error and cancellation states

## Core Methods

### Main Entry Point

**`async chat_with_project(chat, disable_knowledge=False, callback=None, append_references=True, chat_mode=None, iteration=0, system=None)`**

Main entry point for processing chat interactions. Handles:
- Cancellation token registration/unregistration
- Delegation to internal implementation for full call-tree isolation
- Multi-iteration agent recursion

### Internal Implementation

**`async _chat_with_project_inner(...)`**

The complete chat processing pipeline including:

1. **Timing & Context Extraction**: Collects timing information and user message details
2. **Chat Mode Resolution**: Determines active mode and feature flags
3. **Response Message Initialization**: Creates response message and stamps cancellation token
4. **Event Bridge Setup**: Binds ChatEventBridge early for crash-safety
5. **Query Mention Resolution**: Extracts profiles, files, and projects from query
6. **Chat Files Collection**: Gathers files from all visible messages with deduplication
7. **Profile & Model Resolution**: Determines active profiles, LLM model, and tools
8. **Knowledge Flag Evaluation**: Checks if knowledge search should be disabled
9. **Message History Building**: Constructs LangChain message history with optional parent messages
10. **Chat Files Loading**: Reads content of explicitly attached files
11. **AI Instance Preparation**: Configures AI with merged system prompt
12. **Pre-Search Execution**: Runs AI-driven search in vibe/search modes
13. **RAG Knowledge Search**: Performs standard document search if enabled
14. **AI Prompt Assembly**: Builds final message list for AI invocation
15. **AI Response Execution**: Invokes AI/search handler with error handling
16. **Response Metadata Finalization**: Stamps timing, model, and extracted file metadata
17. **Description Generation**: Creates conversation summary and history entries
18. **Metadata Auto-Initialization**: Auto-fills chat name/board/column if marked
19. **Agent Iteration**: Recurses for multi-turn agent tasks
20. **Session Recording**: Records start/end analytics

### Message History Management

**`_build_message_history(chat, include_parent_messages=True)`**

Converts non-hidden, non-improvement chat messages to LangChain format. When `include_parent_messages=True` and the chat has a parent with `ignore_parent_knowledge=False`, prepends parent chat history recursively.

**`_build_clean_message_history_for_description(chat)`**

Creates a cleaner conversation history excluding system prompts, profile content, and file details—suitable for generating concise summaries.

### Profile & Model Resolution

**`_resolve_profiles_and_model(chat, query_mentions, chat_files, is_refine)`**

Derives active profiles, LLM model, tool list, and profile content. Profiles are sorted by name and their content is formatted for the system prompt. Falls back to default content if files are present but no profiles specified.

### Knowledge Search

**`_run_pre_search(chat, messages, query, chat_files)`**

Executes AI-driven pre-search in vibe/search modes. Combines conversation history with current query for richer search context via `ChatKnowledge.ai_search_for_context()`.

**`_run_rag_knowledge_search(chat, messages, query, ignore_documents, search_projects)`**

Performs standard RAG document search across specified projects, formatting results as context blocks.

### Response Generation

**`async _execute_ai_response(chat, messages, is_search, ai, ai_headers, chat_tools, response_message, task_item, callback, send_message_event, cancellation_token, run_context, event_bridge)`**

Invokes AI or search handler:
- For searches: Uses `KnowledgeAISearch` with query built from messages
- For chat: Calls `ai.a_chat()` with run_context for tool/lifecycle event attachment
- On error: Sets `response_message.error`, persists immediately via event bridge
- Hidden reasoning messages are persisted immediately rather than waiting for end-of-turn save

### File Extraction

**`_extract_files_from_response(content)`**

Extracts code blocks with filenames from AI response content using the format:
```
```language filename
code content
```
```

Handles nested code fences and returns list of dicts with `language`, `file_path`, and `content` keys.

### Refinement & Agent Prompts

**`_append_refine_message(chat, messages, user_message, last_ai_message)`**

Builds task-refinement prompt instructing the model to apply comments to existing documents. Incorporates parent context when `ignore_parent_knowledge=False`.

**`_append_agent_message(chat, messages, user_message, iterations_left)`**

Builds agent-style prompt for iterative task completion. Includes iteration count and parent context, instructs model to return `AGENT_DONE_WORD` when finished.

### Metadata Management

**`_finalize_response_metadata(response_message, user_message, timing_info, ai_model, chat_profile_names, extracted_files)`**

Stamps response message with timing, model metadata, and extracted files. Merges user message metadata while preserving fields already set (cancellation token ID, analytics).

**`async _auto_initialize_chat_metadata(chat, messages, ai_chat_fn)`**

Auto-fills missing chat metadata (name, board, column) for auto_initialize chats using AI suggestions. Clears flag on success.

**`async _generate_chat_description(chat, messages, is_refine, ai_chat_fn)`**

Generates 5-line conversation summary excluding technical details. Maintains timestamped history of descriptions as chat evolves.

### Helper Methods

**`_resolve_chat_mode_flags(chat, chat_mode, task_item)`**

Resolves boolean flags from chat mode and task item that drive branching logic.

**`_collect_files_from_visible_messages(valid_messages, chat_base_files)`**

Gathers unique files from all visible messages and base file list. Ensures context from earlier turns is included.

**`_evaluate_knowledge_flags(chat, disable_knowledge, search_projects, user_message)`**

Determines whether knowledge search should be disabled, emitting diagnostic events.

**`_load_chat_files_content(chat_files, already_in_messages)`**

Reads and formats content of explicitly attached files, skipping those already embedded in message history.

**`_document_to_context(doc)`**

Converts a Document to formatted context with language-specific code fence.

**`_resolve_chat_file_path(chat_file)`**

Resolves full filesystem path of chat-attached files.

**`_record_chat_session_start(chat, mode, profiles, files, iteration, max_iterations, llm_model, parent_chat_id)`**

Records initial chat session context for analytics tracking.

**`_record_chat_session_end(chat, mode, profiles, files, iteration, max_iterations, llm_model, start_time, parent_chat_id, cancelled, error)`**

Records final chat session metrics including duration and outcome.

**`_hide_non_answer_messages(chat)`**

In task mode, hides all prior non-answer messages for cleaner output.

**`_append_message_if_missing(chat, message)`**

Appends message only if not already present (by doc_id). Prevents duplicates when ChatEventBridge has already persisted the message.

**`_build_friendly_error_message(error)`**

Extracts API error details for user-friendly display, handling OpenAI BadRequestError with parameter constraints.

### Chat Analysis

**`get_chat_analysis_parents(chat)`**

Traverses parent chat hierarchy and returns concatenated non-hidden message content. Respects `ignore_parent_knowledge` flag at each level.

### Utility Methods

**`convert_message(message)`**

Converts DB Message object to LangChain message type, handling text, images, and role-based conversion.

**`get_profile_manager()`**

Returns ProfileManager instance for current settings.

**`get_chat_manager(project_id=None)`**

Returns ChatManager optionally scoped to specific project.

**`get_ai(llm_model=None, system=None)`**

Returns configured AI instance for specified model with optional system prompt.

**`get_ai_code_generator_changes(response)`**

Processes AI response to extract code generator changes.

**`get_query_mentions(chat, user_message)`**

Extracts mentions of profiles and projects from query content.

**`get_all_search_projects()`**

Returns all projects including child projects and dependencies.

**`index_chat(chat)`**

Indexes chat as Document in knowledge system.

### Cancellation Management

**`cancel_chat(chat_doc_id)`**

Cancels in-flight chat request by chat document ID.

**`cancel_chat_by_token_id(token_id)`**

Cancels in-flight chat request by cancellation token ID (preferred when token_id is available).

**`switch_project(project_id)`**

Switches to another project and reinitializes knowledge system.

## Chat Mode Details

### Task (Refine) Mode

- Asks AI to apply user comments to existing document
- Preserves unchanged document parts
- Incorporates parent task context when available
- Hides non-answer messages after completion

### Agent Mode

- Iterative task completion with configurable max iterations
- Returns `AGENT_DONE_WORD` when task complete
- Recursively calls `_chat_with_project_inner` for next iteration
- Tracks iteration count and remaining attempts

### Vibe Mode

- Uses AI-driven pre-search for context discovery
- Builds richer search query from conversation history
- Typically combined with document refinement

### Search Mode

- Pure knowledge search focused on finding relevant documents
- Bypasses standard chat flow
- Uses `KnowledgeAISearch` for context building

## Context Manager

**`chat_action(chat, event)`**

Context manager emitting start/done/error events around chat actions for logging and notifications.

## Error Handling

The engine handles errors through:

1. **Model Parameter Errors**: Catches BadRequestError, extracts parameter info, returns user-friendly message
2. **Cancellation**: Catches CancelledError, stamps cancelled_at metadata, persists state immediately
3. **Knowledge Search Errors**: Catches OSError/ValueError/RuntimeError, emits error events, continues
4. **General Exceptions**: Sets response_message.error, persists via bridge before subsequent steps

## Integration Points

- **ChatEventBridge**: Attaches tool/lifecycle events to response message, persists on changes
- **AgentRunContext**: Carries run_id and event listeners for tool tracking
- **Knowledge System**: Integrates Milvus knowledge base and AI search
- **Analytics**: Tracks chat sessions for observability
- **ProfileManager**: Resolves profiles and extracts system prompt content
- **ChatManager**: Manages persistent chat storage
- **AI Instance**: Executes LLM calls with configured model and tools

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/ai/cancellation.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/profiles/profile_manager.py, codx/junior/profiling/profiler.py, codx/junior/settings.py, codx/junior/utils/chat_utils.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/chat/chat_knowledge.py
**Imported by:** codx/junior/engine/chat_engine_actions.py, codx/junior/mentions/mention_manager.py, codx/junior/tools/code_writer.py, tests/chat/test_chat_manager.py