# ChatEngine Documentation

## Overview

The `ChatEngine` is the core engine for managing chat interactions with AI models in the CODX Junior platform. It handles message processing, knowledge search, context building, and AI response generation across multiple chat modes (task, agent, vibe, and standard chat).

## Key Features

### Chat Modes

- **Task Mode (`task`)**: Refines documents based on user comments and feedback
- **Agent Mode (`agent`)**: Iterative task completion with multiple attempts
- **Vibe Mode (`vibe`)**: AI-driven search for contextual understanding
- **Standard Chat (`chat`)**: Regular conversational interaction

### Crash Safety & Persistence

The engine implements multiple layers of crash-safety:

1. **ChatEventBridge Integration**: Persists response messages on every event change using merge-safe database operations
2. **Stream Persistence**: Throttled persistence of streamed partial content to survive hard kills
3. **Hidden Reasoning**: Intermediate reasoning messages are persisted immediately upon creation
4. **Error State**: Error conditions are persisted immediately to prevent data loss

### Cancellation Support

Requests can be cancelled via:
- `cancel_chat(chat_doc_id)` - by chat document ID
- `cancel_chat_by_token_id(token_id)` - by cancellation token UUID

A cancellation token is registered at the start of processing and unregistered after completion.

## Core Workflow

### Processing Pipeline

1. **Initialization**: Create response message and bind ChatEventBridge early for event collection
2. **Mode Resolution**: Determine chat mode flags and behavior
3. **Query Parsing**: Extract mentions of profiles, files, and projects
4. **Context Building**:
   - Include parent chat messages (if `ignore_parent_knowledge` is False)
   - Collect files from all visible messages
   - Load explicitly attached file content
5. **Knowledge Search**:
   - Pre-search for vibe/search modes
   - Standard RAG knowledge search if enabled
6. **Prompt Assembly**: Build final message list with context, working files, and mode-specific instructions
7. **AI Execution**: Invoke AI with assembled messages and run context
8. **Response Processing**: Extract files, finalize metadata, generate summary
9. **Agent Recursion**: Continue iteration if agent mode and iterations remain
10. **Session Recording**: Track analytics for the complete chat session

## Key Methods

### Main Entry Point

**`chat_with_project(chat, disable_knowledge, callback, append_references, chat_mode, iteration, system)`**

Main async entry point for processing chat interactions. Registers cancellation token, delegates to inner implementation, and ensures cleanup.

### Message Processing

**`_build_message_history(chat, include_parent_messages)`**

Converts non-hidden, non-improvement chat messages into LangChain format. Optionally includes parent chat messages respecting the `ignore_parent_knowledge` flag.

**`_collect_files_from_visible_messages(valid_messages, chat_base_files)`**

Gathers and deduplicates file references across all visible messages plus chat-level files.

### Context Building

**`_load_chat_files_content(chat_files, already_in_messages)`**

Reads and formats content of explicitly attached files, skipping duplicates already in message history.

**`_run_pre_search(chat, messages, query, chat_files)`**

Executes AI-driven pre-search for vibe and search modes by combining conversation history with current query.

**`_run_rag_knowledge_search(chat, messages, query, ignore_documents, search_projects)`**

Performs standard RAG document search across specified projects.

### AI Execution

**`_execute_ai_response(chat, messages, is_search, ai, ai_headers, chat_tools, response_message, task_item, callback, send_message_event, cancellation_token, run_context, event_bridge)`**

Invokes the appropriate AI or search handler. Handles hidden reasoning persistence, tool events, and error recovery with immediate persistence via event bridge.

**`_build_ai_prompt_messages(chat, messages, user_message, last_ai_message, context, chat_files_content, is_refine, is_agent, iterations_left)`**

Assembles final LangChain message list by appending context, file content, and mode-specific prompts to history.

### Mode-Specific Processing

**`_append_refine_message(chat, messages, user_message, last_ai_message)`**

Appends task-refinement prompt that asks the model to apply comments to a previous document.

**`_append_agent_message(chat, messages, user_message, iterations_left)`**

Appends agent-style prompt instructing the model to complete a task with remaining iteration count.

### Metadata Management

**`_finalize_response_metadata(response_message, user_message, timing_info, ai_model, chat_profile_names, extracted_files)`**

Stamps response message with timing, model information, and extracted files while preserving pre-existing fields.

**`_auto_initialize_chat_metadata(chat, messages, ai_chat_fn)`**

Uses AI to auto-fill missing chat metadata (name, board, column) for auto-initialize chats.

**`_generate_chat_description(chat, messages, is_refine, ai_chat_fn)`**

Generates and stores a summary of the conversation, maintaining timestamped history entries.

### Analytics & Logging

**`_record_chat_session_start(chat, mode, profiles, files, iteration, max_iterations, llm_model, parent_chat_id)`**

Records initial chat session context for analytics tracking.

**`_record_chat_session_end(chat, mode, profiles, files, iteration, max_iterations, llm_model, start_time, parent_chat_id, cancelled, error)`**

Records final chat session metrics including duration, message counts, and error state.

### Utility Methods

**`_resolve_profiles_and_model(chat, query_mentions, chat_files, is_refine)`**

Derives active profiles, LLM model, tool list, and profile system content from query mentions and chat state.

**`_evaluate_knowledge_flags(chat, disable_knowledge, search_projects, user_message)`**

Determines whether knowledge search should be disabled, emitting appropriate events.

**`_extract_files_from_response(content)`**

Extracts code blocks with filenames from AI response using regex parsing.

**`get_chat_analysis_parents(chat)`**

Traverses parent chat hierarchy and concatenates message content, respecting `ignore_parent_knowledge` flags.

**`convert_message(message)`**

Converts database Message objects into LangChain format (HumanMessage, AIMessage, or image content).

## Configuration

The engine uses `CODXJuniorSettings` for project configuration, including:
- Project paths and names
- LLM model settings
- Knowledge base configuration
- Agent iteration limits

## Error Handling

- **BadRequestError**: Extracts and formats API parameter errors for user consumption
- **CancelledError**: Sets cancellation metadata and persists error state immediately
- **General Exceptions**: Logs details and persists error to response message via event bridge

## Parent Chat Integration

The engine supports hierarchical chat structures where child chats inherit context from parents:

- Parent messages are included in history when `ignore_parent_knowledge` is False
- Parent files are merged into context when `ignore_parent_files` is False
- Parent task analysis is incorporated into refine and agent prompts
- Traversal respects ignore flags at each level

## Analytics Integration

Chat sessions are tracked with:
- Session start/end events
- Duration and timing metrics
- Message counts (input/output)
- Profile and file usage
- Model selection
- Cancellation and error states
- Iteration tracking for agent mode

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/ai/cancellation.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/profiles/profile_manager.py, codx/junior/profiling/profiler.py, codx/junior/settings.py, codx/junior/utils/chat_utils.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/chat/chat_knowledge.py
**Imported by:** codx/junior/engine/chat_engine_actions.py, codx/junior/mentions/mention_manager.py, codx/junior/tools/code_writer.py, tests/chat/test_chat_manager.py