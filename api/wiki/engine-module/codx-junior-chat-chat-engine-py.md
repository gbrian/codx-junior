# ChatEngine Documentation

## Overview

The `ChatEngine` is the core component of the CODX API that manages chat interactions with AI models. It orchestrates message processing, knowledge search, context building, and AI response generation across multiple chat modes (task, agent, vibe, and standard chat).

### Key Capabilities

- **Multi-mode chat processing**: Supports task refinement, agent iteration, vibe mode, and standard chat
- **Knowledge integration**: RAG-based document search with pre-search capabilities
- **Crash-safe operations**: Persists response state and intermediate results to survive failures
- **Streaming support**: Real-time partial content delivery with throttled persistence
- **Cancellation support**: Token-based request cancellation with fine-grained tracking
- **Analytics tracking**: Comprehensive session and token usage monitoring
- **Profile management**: Context-aware AI personality and tool configuration

## Initialization

```python
ChatEngine(settings: CODXJuniorSettings, event_manager, user: CodxUser = None)
```

The engine is initialized with:
- **settings**: Project configuration and LLM settings
- **event_manager**: Event emission for chat/search updates
- **user**: Optional authenticated user context

The constructor also initializes:
- Knowledge search system (RAG-based)
- Chat knowledge system (AI-driven search)
- Analytics instance for session tracking

## Chat Modes

The engine supports four primary chat modes:

### 1. Standard Chat (Default)
Regular conversational mode with optional knowledge search and context building.

### 2. Task Mode (`CHAT_MODE_TASK`)
Document refinement mode where the AI applies user comments/suggestions to existing content. Triggered when:
- `chat_mode` is explicitly set to "task"
- A profile specifies `CHAT_MODE_TASK`

### 3. Agent Mode (`CHAT_MODE_AGENT`)
Iterative task completion mode with:
- Configurable maximum iterations
- Automatic recursion until task completion or iteration limit reached
- Agent continues until `AGENT_DONE_WORD` is present in response

### 4. Vibe Mode (`CHAT_MODE_VIBE`)
Pre-search mode that uses AI to build enhanced search queries from conversation history before executing standard RAG search.

## Core Processing Flow

### Main Entry Point

```python
async def chat_with_project(
    chat: Chat,
    disable_knowledge: bool = False,
    callback=None,
    append_references: bool = True,
    chat_mode: str = None,
    iteration: int = 0,
    system: str = None
) -> Tuple[Chat, List[Document]]
```

**Cancellation Token Management**:
- Registers globally for the chat's `doc_id` on first iteration (iteration == 0)
- Token carries unique `token_id` (UUID4) stamped into response metadata
- Token reused across recursive iterations
- Unregistered after outermost call completes
- Clients can cancel via `CANCELLATION_REGISTRY.cancel(chat.doc_id)` or `cancel_by_token_id(token_id)`

### Processing Stages

1. **Project Context Validation**
   - If chat belongs to different project, delegates to that project's engine
   - Ensures all operations occur in correct project context

2. **Cancellation Token Registration**
   - Only at root iteration (iteration == 0)
   - Unique token_id stamped into response metadata immediately
   - Enables early cancellation notification to clients

3. **Query Context Extraction**
   - Extracts user message and resolves chat mode flags
   - Collects visible (non-hidden, non-improvement) messages
   - Identifies task_item type (search, analysis, etc.)

4. **Profile and Tool Resolution**
   - Resolves mentioned profiles from query and parent chat
   - Collects tools from active profiles
   - Determines LLM model (from profile or chat)
   - Merges profile instructions into system prompt

5. **File Context Collection**
   - Collects files from all visible messages (not just current message)
   - Merges query mention files and parent chat files (if not ignored)
   - Deduplicates and sorts for deterministic ordering

6. **Response Message Initialization**
   - Creates response message BEFORE AI call
   - Stamps cancellation token_id in metadata immediately
   - Enables event bridge to persist tool/lifecycle events during run

7. **ChatEventBridge Setup**
   - Binds to response message before AI call
   - Persists on every event change (merge-safe operations)
   - Handles tool event attachment and streamed content throttling
   - Persists hidden reasoning messages immediately

8. **Knowledge Search** (if not disabled)
   - **Pre-search** (vibe/search modes): AI-enhanced query building from conversation history
   - **RAG search** (standard modes): Document retrieval from knowledge base
   - Deduplicates and combines results

9. **AI Prompt Assembly**
   - Appends RAG context as system message
   - Loads explicitly attached file content
   - Applies mode-specific prompts:
     - **Refine**: Task + existing document + comments structure
     - **Agent**: Task completion instructions with iteration counter
     - **Standard**: User message passthrough
   - Prepends working files header if files attached

10. **AI Execution**
    - Invokes AI with assembled messages and tools
    - Collects hidden reasoning messages and persists immediately
    - Handles tool events via ChatEventBridge
    - Catches errors and persists error state immediately
    - Separates thinking content from main response

11. **Response Extraction**
    - Extracts code blocks with filenames
    - Finalizes metadata with timing and model information
    - Merges user message metadata (preserves fields like `cancellation_token_id`)

12. **Post-Processing**
    - Generates conversation summary (description)
    - Auto-initializes chat metadata if marked for auto-init
    - Hides non-answer messages in task/vibe modes
    - Publishes final event bridge state

13. **Agent Iteration** (if agent mode and not done)
    - Recursively calls `_chat_with_project_inner` with incremented iteration
    - Checks `AGENT_DONE_WORD` in response
    - Respects max_iterations limit

14. **Session Analytics**
    - Records chat session START (iteration 0 only)
    - Records chat session END with metrics (success/cancellation/error)
    - Includes timing, model info, profile names, file count

15. **Cleanup**
    - Unregisters cancellation token (root iteration only)
    - Returns updated chat and collected documents

## Crash-Safety Mechanisms

### Response Message Persistence

The response message is created **before** the AI call and persists through multiple safety mechanisms:

- **ChatEventBridge Persistence**: Persists on every event change (tool events, lifecycle events) using merge-safe ChatManager operations
- **Streaming Content Throttling**: `maybe_persist_stream()` called after each streaming flush, bounding disk I/O
- **Error Immediate Persist**: Response error state persisted immediately via `event_bridge.publish()` before summary/metadata steps
- **Hidden Reasoning Persist**: Intermediate reasoning messages persisted immediately via `event_bridge.persist_message()` instead of end-of-turn batch

### Defensive Message Append

`_append_message_if_missing()` guards in-memory appends by `doc_id` lookup. Since the bridge may have already inserted the message to the database, this prevents duplicates in memory.

## Knowledge Search

### Pre-Search (AI-Enhanced)

```python
async def _run_pre_search(
    chat: Chat,
    messages: List,
    query: str,
    chat_files: List[str]
) -> Tuple[List[Document], List[str], str]
```

- Combines conversation history with current query
- Uses AI to build richer search query via `ChatKnowledge.ai_search_for_context()`
- Returns documents, file list, and formatted context string

### RAG Search (Standard)

```python
def _run_rag_knowledge_search(
    chat: Chat,
    messages: List,
    query: str,
    ignore_documents: List[str],
    search_projects: List[CODXJuniorSettings]
) -> Tuple[List[Document], List[str], str]
```

- Searches across specified projects' knowledge bases
- Builds query from message history + current query
- Ignores files already in context to prevent duplication
- Formats results as code blocks

## Helper Methods

### Message Building

- `_build_message_history()`: Converts visible messages to LangChain format (excludes hidden/improvement)
- `_build_ai_prompt_messages()`: Assembles final prompt with context, files, and mode-specific content
- `_build_clean_message_history_for_description()`: Extracts conversation content without system/file details
- `convert_message()`: Converts DB Message to LangChain format (handles text, images)

### File Handling

- `_collect_files_from_visible_messages()`: Deduplicates files from all visible messages and chat-level list
- `_load_chat_files_content()`: Reads and formats explicitly attached file content
- `_extract_files_from_response()`: Parses markdown code blocks with filenames from AI response
- `_resolve_chat_file_path()`: Resolves relative/absolute file paths to filesystem location

### Metadata and Profiles

- `_resolve_profiles_and_model()`: Derives active profiles, model, tools, and system prompt content
- `_resolve_chat_mode_flags()`: Resolves boolean flags (is_refine, is_agent, is_vibe, etc.)
- `_finalize_response_metadata()`: Stamps timing, model, and extracted files into response

### Configuration and Utilities

- `_evaluate_knowledge_flags()`: Determines if knowledge search should be disabled with event emission
- `get_profile_manager()`: Returns ProfileManager for current settings
- `get_chat_manager()`: Returns ChatManager optionally scoped to project
- `get_query_mentions()`: Extracts mentions of profiles and projects from query
- `get_chat_analysis_parents()`: Traverses parent chat hierarchy and collects content
- `get_ai()`: Creates AI instance with optional model override and system prompt
- `get_all_search_projects()`: Returns current project plus child projects and dependencies

### Context Management

- `_append_refine_message()`: Builds task refinement prompt with parent context
- `_append_agent_message()`: Builds agent completion prompt with iteration counter

### Post-Processing

- `_generate_chat_description()`: AI-generated conversation summary with history tracking
- `_auto_initialize_chat_metadata()`: AI-fills missing name/board/column for auto_initialize chats
- `_hide_non_answer_messages()`: Hides prior messages in task mode

### Session Tracking

- `_record_chat_session_start()`: Records initial chat context
- `_record_chat_session_end()`: Records final metrics, duration, and error state

## Cancellation

### Methods

```python
def cancel_chat(self, chat_doc_id: str) -> bool
def cancel_chat_by_token_id(self, token_id: str) -> bool
```

- `cancel_chat()`: Cancel by chat `doc_id`
- `cancel_chat_by_token_id()`: Cancel by token UUID (preferred when token_id available)
- Both return True if token found and cancelled, False otherwise

### Cancellation State

- Triggers `CancelledError` during AI execution
- Sets `response_message.meta_data["cancelled_at"]` to ISO-8601 UTC timestamp
- Persists cancelled state immediately via event bridge
- Records session END with cancelled flag
- Preserves any partial content generated before cancellation

## Project Switching

```python
def switch_project(self, project_id: str) -> "ChatEngine"
```

Dynamically switches engine context to a different project:
- Updates internal settings
- Reinitializes ChatKnowledge
- Logs project switch
- Returns self for method chaining

## AI Integration

```python
def get_ai(self, llm_model: Optional[str] = None, system: str = None) -> AI
```

Creates configured AI instances with:
- Optional model override
- Optional system prompt override
- Current user context
- Project settings

## Code Generation

```python
def get_ai_code_generator_changes(self, response: str) -> AICodeGenerator
```

Processes AI responses to extract code changes:
- Parses response structure
- Normalizes file paths to project root
- Returns AICodeGenerator with parsed changes

## Indexing

```python
def index_chat(self, chat: Chat) -> None
```

Indexes chat conversation as a Document in the knowledge system:
- Concatenates visible messages
- Sets metadata (source, parser, loader_type)
- Enables future retrieval via knowledge search
- Logs indexing results

## Context Manager

```python
@contextmanager
def chat_action(self, chat: Chat, event: str)
```

Emits start/done/error events around chat actions:
- Logs action beginning
- Handles OSError exceptions with error event
- Always emits done event (in finally block)
- Integrates with event_manager for client notification

## Event-Driven Architecture

The engine integrates with an event manager that emits:
- `chat_event()`: Status messages, knowledge search events, model selection
- `message_event()`: Streaming partial responses with current message state
- Events include chat context, message content, and metadata
- Clients receive real-time updates including cancellation token_id

## Configuration

The engine uses `CODXJuniorSettings` for:
- Project paths and metadata
- LLM model configuration
- Knowledge base settings
- Agent iteration limits
- Knowledge search enablement flags

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/ai/cancellation.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/profiles/profile_manager.py, codx/junior/profiling/profiler.py, codx/junior/settings.py, codx/junior/utils/chat_utils.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/chat/chat_knowledge.py
**Imported by:** codx/junior/engine/chat_engine_actions.py, codx/junior/mentions/mention_manager.py, codx/junior/tools/code_writer.py, tests/chat/test_chat_manager.py