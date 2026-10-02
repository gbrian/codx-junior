# ChatEngine Documentation

## Overview

The `ChatEngine` is the core engine for managing chat interactions with AI models in the CODX Junior system. It orchestrates message processing, knowledge search, context building, and AI response generation across various chat modes (task, agent, vibe, standard chat).

## Architecture

### Core Responsibilities

The ChatEngine handles:
- **Message Processing**: Converting database messages to LangChain format and managing conversation history
- **Knowledge Search**: Both RAG-based document search and AI-driven semantic search
- **Context Building**: Assembling comprehensive context from profiles, files, and prior conversations
- **AI Response Generation**: Invoking LLMs with appropriate prompts and handling streaming responses
- **Agent Iteration**: Managing multi-turn agent loops with configurable iteration limits
- **Session Analytics**: Tracking chat sessions, token usage, and tool executions for full request-response traceability

### Crash-Safety Mechanisms

The engine implements multiple crash-safety layers:

1. **Response Message Persistence**: The response message is created before the AI call and persisted on every event change via `ChatEventBridge`, ensuring tool events and lifecycle updates survive crashes
2. **Streamed Content Throttling**: Partial streamed content is persisted (throttled) from the streaming callback, with a hard kill losing at most a few seconds of text
3. **Hidden Reasoning Preservation**: Intermediate reasoning messages are persisted immediately upon creation rather than waiting for end-of-turn saves
4. **Error State Persistence**: Response message errors are persisted immediately via the event bridge

## Initialization

```python
ChatEngine(settings, event_manager, user=None)
```

**Parameters:**
- `settings`: The current project's settings (CODXJuniorSettings)
- `event_manager`: Event manager for emitting chat/search events
- `user`: Optional authenticated user for the session (CodxUser)

**Internal Components:**
- Knowledge base instance for RAG search
- ChatKnowledge instance for AI-driven search
- Analytics instance for session tracking

## Chat Modes

The engine supports four primary chat modes:

### Task Mode (`CHAT_MODE_TASK`)
Refines documents based on user comments and instructions. Uses existing document content as reference and applies requested modifications while preserving unaffected portions.

### Agent Mode (`CHAT_MODE_AGENT`)
Executes iterative task completion with configurable iteration limits. The agent receives remaining iteration count and returns `AGENT_DONE_WORD` when the task is complete.

### Vibe Mode (`CHAT_MODE_VIBE`)
Performs AI-driven semantic search to gather context before responding, optimizing for exploratory conversations.

### Standard Chat Mode
Direct conversation without specialized processing, suitable for general-purpose interactions.

## Main Entry Point: `chat_with_project`

```python
async chat_with_project(
    chat: Chat,
    disable_knowledge: bool = False,
    callback=None,
    append_references: bool = True,
    chat_mode: str = None,
    iteration: int = 0,
    system: str = None
)
```

### Processing Flow

1. **Cancellation Token Registration**: Registers a token (UUID4) for the chat turn, enabling external cancellation
2. **Chat Mode Resolution**: Determines effective mode from explicit override or chat configuration
3. **Query Mentions Extraction**: Identifies profiles, projects, and file references in the user query
4. **File Collection**: Gathers files from all visible messages, query mentions, and parent chats
5. **Profile Resolution**: Sorts and merges profiles, determining active tools and LLM model
6. **Message History Building**: Constructs LangChain messages including parent chat history (respecting `ignore_parent_knowledge` flag)
7. **Knowledge Search**: Executes RAG search or AI-driven search based on chat mode
8. **AI Invocation**: Sends assembled prompt to LLM with streaming callback
9. **Response Processing**: Extracts files, finalizes metadata, and handles agent recursion
10. **Session Recording**: Tracks session start/end with analytics

### Response Message Creation

The response message is created **before** the AI call and receives:
- Cancellation token ID stamped in metadata for client-side cancellation
- Tool/lifecycle events attached during the run via ChatEventBridge
- Streamed partial content persisted at throttled intervals
- Hidden reasoning messages persisted immediately

### Cancellation

Two cancellation methods are available:

```python
cancel_chat(chat_doc_id: str) -> bool
cancel_chat_by_token_id(token_id: str) -> bool
```

The cancellation token ID is included in the first streaming event's response metadata, enabling clients to cancel without knowing the internal chat ID.

## Knowledge Search

### RAG Knowledge Search

```python
_run_rag_knowledge_search(
    chat, messages, query, ignore_documents, search_projects
) -> Tuple[List[Document], List[str], str]
```

Performs standard similarity-based document retrieval across specified projects, excluding files already in the chat context.

### AI-Driven Pre-Search

```python
async _run_pre_search(
    chat, messages, query, chat_files
) -> Tuple[List[Document], List[str], str]
```

Used in vibe and search modes. Combines conversation history with the current query to build a richer search query for semantic matching.

### Knowledge Disable Conditions

Knowledge search is disabled when:
- Explicitly disabled via `disable_knowledge` parameter
- No search projects are found
- Project settings disable knowledge (via `use_knowledge` flag)
- User message has `disable_knowledge` flag set

## Profile and Model Resolution

```python
_resolve_profiles_and_model(
    chat, query_mentions, chat_files, is_refine
) -> Dict[str, Any]
```

Returns:
- `chat_profiles_system_content`: Formatted profile instructions for the system prompt
- `chat_profile_names`: List of active profile names
- `chat_model`: Selected LLM model (from first profile with model specified)
- `chat_tools`: Deduplicated tools from all active profiles
- `is_refine`: Updated flag if any profile specifies task mode

Profiles are sorted by name for consistent ordering and deterministic system prompt generation.

## Context Building

### File Loading

```python
_load_chat_files_content(chat_files, already_in_messages) -> str
```

Reads explicitly attached chat files and formats them as code blocks. Skips files already embedded in message history to avoid duplication.

### Message History Building

```python
_build_message_history(chat, include_parent_messages=True) -> List
```

**Key Features:**
- Excludes hidden and improvement messages
- Excludes the current user message
- Recursively includes parent chat messages when `ignore_parent_knowledge` is False
- Converts Message objects to LangChain format (HumanMessage/AIMessage)
- Tool and lifecycle events on response messages are not converted to prompt content

### Clean Message History (for Descriptions)

```python
_build_clean_message_history_for_description(chat) -> List
```

Creates a cleaner conversation history suitable for summaries by:
- Excluding hidden and improvement messages
- Removing system prompts and file content markers
- Extracting only the user request portion from processing messages
- Filtering out search/context messages

## AI Prompt Assembly

```python
_build_ai_prompt_messages(
    chat, messages, user_message, last_ai_message,
    context, chat_files_content, is_refine, is_agent, iterations_left
) -> List
```

Constructs the final message list by:

1. Appending RAG/pre-search context as a system message if present
2. Building mode-specific prompts:
   - **Refine Mode**: Requests application of comments to existing document
   - **Agent Mode**: Provides task description and iteration count
   - **Standard**: Appends user message directly
3. Prepending working file headers if chat files are present

### Refine Mode Prompt

Includes:
- Task document headers (from `is_answer` messages)
- Parent task context (when applicable)
- Existing document content
- User comments
- Instructions to preserve unaffected portions

### Agent Mode Prompt

Includes:
- Task name from chat
- Parent context for child documents (when applicable)
- User request
- Remaining iteration count
- Done-word instruction

## Response Handling

### File Extraction

```python
_extract_files_from_response(content: str) -> List[Dict[str, str]]
```

Parses markdown code blocks with format:
```
```language filename
code content
```
```

Returns list of dictionaries with: `language`, `file_path`, `content`

### Response Metadata Finalization

```python
_finalize_response_metadata(
    response_message, user_message, timing_info,
    ai_model, chat_profile_names, extracted_files
)
```

Stamps the response with:
- Timing metrics (total time, first response time)
- Model information
- Extracted files from code blocks
- Profile names used during execution

Merges user message metadata while preserving response-generated fields like `cancellation_token_id` and `analytics`.

## Chat Description and History

### Auto-Generated Description

```python
async _generate_chat_description(
    chat, messages, is_refine, ai_chat_fn
) -> None
```

Generates a 5-line summary of the conversation and maintains a timestamped history of descriptions (`ChatHistoryEntry`) as the chat evolves, enabling review of context changes over time.

### Auto-Initialize Metadata

```python
async _auto_initialize_chat_metadata(
    chat, messages, ai_chat_fn
) -> None
```

For chats marked with `auto_initialize` flag, uses AI to suggest:
- `name`: Short descriptive title (max 8 words)
- `board`: High-level category (Backend, Frontend, DevOps, Design, General)
- `column`: Workflow column (To Do, In Progress, Done, Backlog)

Only fills empty fields and clears the flag on success.

## Parent Chat Integration

The engine fully supports chat hierarchies with the `parent_id` and `ignore_parent_knowledge` flags:

### Message History Inheritance

Parent chat messages are prepended to the conversation when:
- Chat has a `parent_id`
- `ignore_parent_knowledge` is False
- Parent chat can be loaded

This happens recursively up the hierarchy until a parent has `ignore_parent_knowledge=True`.

### Parent Context in Task/Agent Modes

Both refine and agent modes include parent task context via `get_chat_analysis_parents()`, which:
- Traverses the parent chain
- Respects `ignore_parent_knowledge` at each level
- Concatenates non-hidden messages
- Stops traversal when encountering a parent with the ignore flag

### File Inheritance

Files from parent chat are merged into the context when:
- Parent chat exists and has `file_list`
- `ignore_parent_files` is False

## Analytics and Session Tracking

The engine records comprehensive session analytics:

### Session Start

```python
_record_chat_session_start(
    chat, mode, profiles, files, iteration, max_iterations,
    llm_model, parent_chat_id
)
```

Captures initial context including chat metadata, mode, active profiles, and files.

### Session End

```python
_record_chat_session_end(
    chat, mode, profiles, files, iteration, max_iterations,
    llm_model, start_time, parent_chat_id, cancelled, error
)
```

Records final metrics including:
- Total duration in seconds
- Message counts (input/output)
- Cancellation and error states

Sessions are tracked with timestamps enabling full request-response traceability.

## Utility Methods

### Project Management

```python
switch_project(project_id: str) -> ChatEngine
```

Switches the engine context to another project, recreating the ChatKnowledge instance for the new project.

```python
get_all_search_projects() -> List[CODXJuniorSettings]
```

Returns all searchable projects including child projects and dependencies.

### Query Mentions

```python
get_query_mentions(chat: Chat, user_message: Message) -> QueryMentions
```

Extracts mentions of profiles and projects from user message content. Profiles are inherited from chat configuration if not explicitly mentioned.

### Parent Analysis

```python
get_chat_analysis_parents(chat: Chat) -> str
```

Traverses parent chat hierarchy respecting `ignore_parent_knowledge` flags and returns concatenated non-hidden message content.

### AI Integration

```python
get_ai(llm_model: Optional[str] = None, system: str = None) -> AI
```

Creates an AI instance configured for a specific LLM model with optional system prompt override.

### Code Generation

```python
get_ai_code_generator_changes(response: str) -> AICodeGenerator
```

Parses AI response to extract code changes, normalizing file paths to absolute project paths.

### Message Conversion

```python
convert_message(message: Message)
```

Converts database Message objects to LangChain format:
- Text-only messages → HumanMessage/AIMessage
- Messages with images → Image-enabled format with multiple content types

### Knowledge Indexing

```python
index_chat(chat: Chat) -> None
```

Indexes chat conversation as a Document in the knowledge system for future retrieval, using chat file path as metadata source.

## Error Handling

The engine implements comprehensive error handling:

1. **AI Call Errors**: Caught and appended to response message with error state persisted immediately
2. **Knowledge Search Errors**: Logged and reported via event manager without blocking
3. **File Loading Errors**: Logged individually; chat processing continues
4. **Metadata Generation Errors**: Logged; chat processing completes without summaries
5. **Cancellation**: Handled gracefully with state persistence at cancel point

All errors are prefixed with descriptive context (chat name, file path, etc.) for debugging.

## Event Emission

The engine emits events through the event manager for:

- Chat action lifecycle (start, done, error)
- Knowledge search status (found N documents)
- Model selection notifications
- Profile application confirmations
- Cancellation notifications

Events include human-readable messages suitable for UI display and include error classifications for client handling.

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/ai/cancellation.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/profiles/profile_manager.py, codx/junior/profiling/profiler.py, codx/junior/settings.py, codx/junior/utils/chat_utils.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/chat/chat_knowledge.py
**Imported by:** codx/junior/engine/chat_engine_actions.py, codx/junior/mentions/mention_manager.py, codx/junior/tools/code_writer.py, tests/chat/test_chat_manager.py