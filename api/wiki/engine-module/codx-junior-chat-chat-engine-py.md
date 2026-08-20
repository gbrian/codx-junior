# ChatEngine Documentation

## Overview

The `ChatEngine` is the core component responsible for managing chat interactions with AI models within the CODX Junior system. It orchestrates message processing, knowledge search, context building, and AI response generation across multiple chat modes and project configurations.

## Architecture

The ChatEngine operates through a comprehensive workflow that handles:

- **Chat mode resolution** - Determining execution path based on chat type (task, agent, vibe, or standard chat)
- **Context building** - Aggregating files, knowledge base documents, and conversation history
- **AI orchestration** - Coordinating LLM invocations with appropriate prompts and parameters
- **Session tracking** - Recording analytics for traceability and monitoring
- **Cancellation handling** - Managing in-flight request cancellation via token-based registry

## Initialization

```python
ChatEngine(
    settings: CODXJuniorSettings,
    event_manager,
    user: CodxUser = None
)
```

The engine initializes with project settings, an event manager for emitting notifications, and optional user context. It instantiates internal components including:

- **Knowledge system** - Milvus-based vector search for RAG
- **ChatKnowledge** - Enhanced knowledge search with AI query refinement
- **Analytics** - Session and token usage tracking

## Main Entry Point: chat_with_project

The primary method for processing chat interactions:

```python
async def chat_with_project(
    chat: Chat,
    disable_knowledge: bool = False,
    callback=None,
    append_references: bool = True,
    chat_mode: str = None,
    iteration: int = 0,
    system: str = None
)
```

### Request Flow

1. **Project Context Validation** - Verifies the chat belongs to the current project context, switching if necessary
2. **Cancellation Token Registration** - Creates a unique cancellation token for tracking and request cancellation
3. **Mode Resolution** - Determines execution mode from explicit override or chat configuration
4. **Query Mentions Extraction** - Identifies referenced profiles, projects, and files
5. **File Collection** - Gathers files from all visible messages and parent chats
6. **Profile Resolution** - Compiles active profiles, tools, and LLM model configuration
7. **Knowledge Search** - Executes RAG search if enabled and applicable
8. **AI Invocation** - Sends assembled prompt to the configured model
9. **Response Processing** - Parses output, extracts code blocks, and finalizes metadata
10. **Agent Iteration** - Recursively continues if in agent mode and task incomplete
11. **Session Recording** - Logs analytics data for the complete interaction

### Response Message Metadata

The response message receives immediate annotation with a `cancellation_token_id` that is transmitted to clients in the first streaming event. This allows clients to cancel requests using either:

- `cancel_chat(chat_doc_id)` - Cancel by chat identifier
- `cancel_chat_by_token_id(token_id)` - Cancel by token UUID

Upon cancellation, the response metadata receives a `cancelled_at` ISO-8601 UTC timestamp.

## Chat Modes

### Task Mode (chat_mode = "task")

Refines an existing document based on user comments:

- Retrieves the previous AI-generated document
- Applies user comments as modifications
- Preserves unaffected document sections
- Optionally incorporates parent document context

### Agent Mode (chat_mode = "agent")

Iteratively completes tasks with multiple attempts:

- Provides task name and objective to the model
- Tracks iteration count and remaining attempts
- Continues execution until `AGENT_DONE_WORD` appears in response or iterations exhausted
- Supports recursive invocation with shared cancellation token

### Vibe Mode (chat_mode = "vibe")

Experimental exploratory chat using AI-driven search:

- Executes pre-search using combined conversation context
- Refines knowledge search query with AI assistance
- Hides non-answer messages from history

### Standard Chat Mode

Default conversational mode:

- Processes user message with conversation history
- Applies knowledge search if enabled
- Returns AI response without mode-specific constraints

## Knowledge Search Integration

### Pre-Search (Vibe/Search Modes)

The `_run_pre_search` method executes AI-driven query refinement:

```python
async def _run_pre_search(
    chat: Chat,
    messages: List,
    query: str,
    chat_files: List[str]
) -> Tuple[List[Document], List[str], str]
```

Combines conversation history with the current query to generate a richer search query, then delegates to ChatKnowledge for context retrieval.

### RAG Knowledge Search

The `_run_rag_knowledge_search` method performs standard vector search:

```python
def _run_rag_knowledge_search(
    chat: Chat,
    messages: List,
    query: str,
    ignore_documents: List[str],
    search_projects: List[CODXJuniorSettings]
) -> Tuple[List[Document], List[str], str]
```

Executes knowledge base search across specified projects, excluding files already in the chat context.

### Knowledge Disable Conditions

Knowledge search is disabled when:

- Explicitly disabled via `disable_knowledge=True` parameter
- No search projects are available
- Project settings have `use_knowledge=False`
- User message has `disable_knowledge=True`

## Profile and Tool Resolution

The `_resolve_profiles_and_model` method derives:

- **Active profiles** - Merged from query mentions and chat configuration
- **System prompt content** - Concatenated profile instructions formatted with current timestamp
- **LLM model** - From first profile with model specification, or existing chat model
- **Tool list** - Aggregated from all active profiles, deduplicated
- **Refine mode flag** - Activated if any profile has `chat_mode == CHAT_MODE_TASK`

Profiles are sorted by name for deterministic ordering and consistent context inclusion.

## File Management

### File Collection Strategy

Files are collected from multiple sources and deduplicated:

1. Chat-level `file_list`
2. All visible message `files` properties
3. Query mention `@file` references
4. Parent chat `file_list` (unless `ignore_parent_files=True`)

The `_collect_files_from_visible_messages` helper ensures that files from any prior message in the conversation are included in the working context, not just those on the most recent user message.

### File Content Loading

The `_load_chat_files_content` method reads explicitly attached files:

- Skips files already embedded as code blocks in message history
- Resolves relative paths against project root
- Formats content with language-specific code fences
- Includes source path metadata for model context

## Message History Building

The `_build_message_history` method constructs LangChain message objects:

- Excludes hidden messages (`message.hide=True`)
- Excludes improvement messages (`message.improvement=True`)
- Excludes the last message (current user query)
- Preserves conversation context for multi-turn interactions

## AI Prompt Assembly

The `_build_ai_prompt_messages` method constructs the final message list:

1. **Context Injection** - Appends RAG/pre-search results as user message
2. **Mode-Specific Prompting**:
   - Task mode: Applies refine prompt to prior AI document
   - Agent mode: Provides task completion instructions
   - Standard: Appends user message directly
3. **Working Files Prepending** - Inserts explicit chat file content before user request
4. **Profile Instructions** - Merged into system prompt at AI initialization

## Response Processing

### Content Extraction

The `_extract_files_from_response` method parses markdown code blocks:

```
```language filename
code content here
```
```

Handles nested code fences and returns list of extracted files with:
- `language` - Programming language identifier
- `file_path` - Filename from code fence
- `content` - Code block content

### Metadata Finalization

The `_finalize_response_metadata` method stamps:

- `time_taken` - Total request duration
- `first_chunk_time_taken` - Time to first token
- `model` - LLM model identifier
- `files` - Extracted code blocks
- Merged user message metadata (preserving client-side fields)

## Description and History Generation

### Chat Description Generation

The `_generate_chat_description` method:

1. Builds clean message history excluding system prompts and file details
2. Constructs LangChain message objects from clean content
3. Invokes AI with summary prompt
4. Updates current `chat.description`
5. Appends timestamped `ChatHistoryEntry` to conversation history

This maintains an evolving record of chat context as it develops across multiple turns.

### Auto-Initialization

The `_auto_initialize_chat_metadata` method auto-fills metadata for chats marked `auto_initialize`:

- Generates AI suggestions for `name`, `board`, and `column`
- Only overwrites empty fields
- Clears `auto_initialize` flag on success
- Handles JSON parsing with fallback for markdown-wrapped responses

## Session Analytics

### Session Start Recording

The `_record_chat_session_start` method captures:

- Chat identification and name
- Username and project context
- Chat mode and active profiles
- File list and iteration tracking
- Initial LLM model selection

Called before AI invocation to establish baseline metrics.

### Session End Recording

The `_record_chat_session_end` method records:

- Total duration in seconds
- Final message counts (user and assistant)
- Completion status (success, cancellation, or error)
- All context from session start for full traceability

Called after AI response or upon cancellation/error to finalize metrics.

## Cancellation Management

Cancellation operates through a global `CANCELLATION_REGISTRY`:

```python
def cancel_chat(self, chat_doc_id: str) -> bool
def cancel_chat_by_token_id(self, token_id: str) -> bool
```

**Key behaviors:**

- Tokens registered only at iteration 0 (root) and reused for agent recursion
- Token ID stamped in response metadata immediately for early client access
- `CancelledError` exception caught and handled with metadata annotation
- Session recorded with `cancelled=True` and error message
- Partial response preserved in `response_message.content`

## Project Switching

The `switch_project` method enables delegation to another project's ChatEngine:

```python
def switch_project(self, project_id: str) -> "ChatEngine"
```

When a chat's `project_id` differs from the current engine's project, the chat is automatically delegated to the appropriate project context without requiring caller awareness.

## Helper Methods

### Message Conversion

`convert_message(message: Message)` - Transforms DB Message objects to LangChain types:

- Handles text-only messages as `HumanMessage` or `AIMessage`
- Parses image metadata and constructs multimodal message content
- Supports JSON-encoded image URLs with alt text

### Query Mentions Extraction

`get_query_mentions(chat: Chat, user_message: Message) -> QueryMentions` - Identifies:

- Profile references (`@profile_name`)
- Project references (`@project`)
- File attachments from message or chat level
- Automatically adds file-based profiles via `ProfileManager`

### Parent Context Traversal

`get_chat_analysis_parents(chat: Chat) -> str` - Traverses parent chat chain:

- Recursively collects non-hidden messages from ancestors
- Concatenates content for parent document inclusion
- Handles missing parent chats with error logging

### AI Instance Creation

`get_ai(llm_model: Optional[str] = None, system: str = None) -> AI` - Returns configured AI instance:

- Sets model explicitly or uses settings default
- Allows system prompt override
- Initialized with project settings and user context

### Code Generator Extraction

`get_ai_code_generator_changes(response: str) -> AICodeGenerator` - Parses response for code changes:

- Converts response string to `AICodeGenerator` object
- Resolves file paths to absolute project paths
- Returns structured code change objects

### Chat Indexing

`index_chat(chat: Chat)` - Adds chat conversation to knowledge base:

- Collects non-hidden, non-improvement messages
- Creates Document with chat metadata
- Enables future semantic search over chat conversations

## Error Handling

The engine implements comprehensive error handling:

- **AI Communication Errors** - Caught and returned as user-friendly response
- **File I/O Errors** - Logged but don't halt processing
- **Knowledge Search Errors** - Emitted as events but allow fallback to standard chat
- **Cancellation Errors** - Intercepted and gracefully annotated
- **Analytics Recording Errors** - Logged as warnings but don't impact response

All error conditions preserve partial responses and attempt graceful degradation.

## Event Emission

The `chat_action` context manager and `event_manager` emit notifications:

- **Progress events** - "starting", "done", "error" for UI feedback
- **Status updates** - Knowledge search progress, model selection, profiles applied
- **Message events** - Partial response chunks via streaming callback
- **Analytics events** - Search queries, result counts, model choices

## Streaming and Callbacks

Response streaming via callback pattern:

```python
def callback(content: str) -> None:
    """Default streaming callback that emits partial response events."""
    send_message_event(content=content, done=False)
```

- Called repeatedly as AI generates tokens
- Updates response message metadata with timing
- Separates thinking blocks from main content
- Tracks first token arrival time
- Forwards cancellation token ID in every event

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/ai/cancellation.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/profiles/profile_manager.py, codx/junior/profiling/profiler.py, codx/junior/settings.py, codx/junior/utils/chat_utils.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/chat/chat_knowledge.py
**Imported by:** codx/junior/engine/chat_engine_actions.py, codx/junior/mentions/mention_manager.py, codx/junior/tools/code_writer.py, tests/chat/test_chat_manager.py