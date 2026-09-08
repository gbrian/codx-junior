# ChatEngine Documentation

## Overview

The `ChatEngine` is the core component of the CODX Junior API responsible for managing chat interactions with AI models. It orchestrates message processing, knowledge base searching, context building, and AI response generation across multiple chat modes.

## Key Features

### Chat Modes

The engine supports four distinct chat modes:

- **chat**: Standard conversational mode
- **task**: Document refinement mode where the AI applies feedback to existing documents
- **agent**: Iterative task completion mode with multiple attempts
- **vibe**: AI-driven search mode using semantic understanding

### Crash-Safety Architecture

The engine implements comprehensive crash-safety mechanisms:

- **ChatEventBridge**: Persists response messages on every event change, ensuring tool events and lifecycle events survive crashes
- **Streamed Content Persistence**: Throttled persist of partial content from streaming callbacks
- **Hidden Reasoning Persistence**: Intermediate reasoning messages are persisted immediately via the event bridge
- **Error State Persistence**: Response message errors are persisted immediately upon occurrence

### Cancellation Support

External callers can cancel in-flight requests using:

```python
# By chat document ID
CANCELLATION_REGISTRY.cancel(chat.doc_id)

# By cancellation token ID
CANCELLATION_REGISTRY.cancel_by_token_id(token_id)
```

The cancellation token ID is stamped into response message metadata immediately upon creation, allowing clients to receive it in the first streaming event.

## Core Methods

### Main Entry Point: `chat_with_project()`

Processes a chat interaction with comprehensive workflow management:

```python
async def chat_with_project(
    self,
    chat: Chat,
    disable_knowledge: bool = False,
    callback=None,
    append_references: bool = True,
    chat_mode: str = None,
    iteration: int = 0,
    system: str = None
)
```

**Workflow Steps:**

1. **Project Context Validation**: Switches project context if chat belongs to different project
2. **Cancellation Token Registration**: Registers token for request cancellation (root iteration only)
3. **Query Context Extraction**: Processes user message and identifies task items
4. **Chat Mode Resolution**: Determines active flags for vibe, search, refine, and agent modes
5. **Response Message Creation**: Creates response message before AI call and stamps cancellation token ID
6. **Event Bridge Initialization**: Binds ChatEventBridge early to persist events during run
7. **Query Mentions Resolution**: Extracts profiles, files, and projects from query
8. **Chat Files Collection**: Gathers files from all visible messages and parent chats
9. **Profile & Model Resolution**: Determines active profiles, LLM model, and tools
10. **Message History Building**: Constructs LangChain messages including parent messages (if not ignored)
11. **Search Project Resolution**: Identifies projects for knowledge search
12. **Knowledge Disable Evaluation**: Determines if knowledge search should be disabled
13. **AI Instance Configuration**: Merges profile system content with optional system prompt
14. **Pre-Search Execution**: Runs AI-driven search for vibe/search modes
15. **RAG Knowledge Search**: Performs standard document search if enabled
16. **Prompt Assembly**: Builds final message list with context and mode-specific prompts
17. **AI Response Execution**: Invokes AI with tool support and run context
18. **Response Finalization**: Extracts files, stamps metadata, persists state
19. **Description Generation**: Creates conversation summary via AI
20. **Auto-Initialization**: Fills missing metadata for auto_initialize chats
21. **Agent Iteration**: Recurses if agent mode and iterations remain
22. **Session Recording**: Records analytics for the complete session

### Context Building Methods

#### `_build_message_history()`

Converts chat messages to LangChain format with optional parent message inclusion:

- Excludes hidden and improvement messages
- Includes parent chat history when `ignore_parent_knowledge=False`
- Recursively processes parent's parent messages
- Returns list ready for LLM consumption

#### `_collect_files_from_visible_messages()`

Gathers unique file references across all visible messages:

- Unions chat-level files with per-message files
- Deduplicates and sorts for deterministic ordering
- Essential for multi-turn context preservation

### Knowledge Search Methods

#### `_run_pre_search()`

Executes AI-driven search for vibe and search modes:

- Combines conversation history with current query
- Delegates to ChatKnowledge for semantic search
- Returns documents, file list, and formatted context string

#### `_run_rag_knowledge_search()`

Performs standard RAG document search:

- Searches across specified projects
- Excludes already-provided documents
- Formats results as code blocks in context string
- Handles search errors gracefully

### Profile & Model Resolution

#### `_resolve_profiles_and_model()`

Derives active profiles, model, and tools from query mentions:

- Sorts profiles by name for consistency
- Builds system prompt content from profile instructions
- Collects tools from all active profiles
- Selects LLM model from profile if not explicitly set
- Returns complete resolution dictionary

### Message Assembly

#### `_build_ai_prompt_messages()`

Assembles final LangChain message list for AI invocation:

- Appends context as user message if available
- Adds mode-specific prompts (refine/agent/standard)
- Prepends working files content
- Handles context-specific message formatting

#### `_append_refine_message()`

Builds task-refinement prompt for document updates:

- References existing document if available
- Includes parent context when not ignored
- Instructs model to apply comments while preserving unchanged content

#### `_append_agent_message()`

Creates agent-style prompt for iterative task completion:

- Provides task context and iteration limits
- Includes parent context when available
- Instructs model to return completion marker when done

### Response Handling

#### `_execute_ai_response()`

Invokes AI or search handler with comprehensive error handling:

- Supports both standard AI chat and knowledge search modes
- Handles hidden reasoning messages with immediate persistence
- Manages cancellation and errors with response message state preservation
- Returns think content, main content, extracted files, and callable for future AI operations

#### `_extract_files_from_response()`

Parses code blocks from AI response:

- Matches markdown fence format: ` ```language filename`
- Handles nested code fences
- Returns list of extracted file objects with language, path, and content

#### `_finalize_response_metadata()`

Stamps response message with comprehensive metadata:

- Records timing information (total and first-chunk times)
- Includes model name and active profile names
- Stores extracted files from response
- Preserves pre-existing metadata fields like cancellation token ID

### Description & Metadata Generation

#### `_generate_chat_description()`

Creates conversation summaries via AI:

- Builds clean message history excluding file contents and profiles
- Alternates between user and assistant roles
- Uses only last message in refine mode
- Maintains timestamped history entries for context tracking
- Handles errors gracefully without blocking chat completion

#### `_auto_initialize_chat_metadata()`

Auto-fills missing chat metadata for marked chats:

- Queries AI for suggested name, board, and column values
- Parses JSON response with error handling
- Only overwrites empty fields
- Clears auto_initialize flag on success

### Analytics Recording

#### `_record_chat_session_start()`

Records initial session context:

- Captures chat metadata, mode, profiles, files
- Records initial message counts
- Enables per-session tracking across iterations

#### `_record_chat_session_end()`

Records final session metrics:

- Calculates duration and final message counts
- Captures cancellation and error states
- Completes session analytics for traceability

## Cancellation Support

### `cancel_chat()`

Cancels request by chat document ID:

```python
def cancel_chat(self, chat_doc_id: str) -> bool
```

### `cancel_chat_by_token_id()`

Cancels request by cancellation token ID (preferred method):

```python
def cancel_chat_by_token_id(self, token_id: str) -> bool
```

## Utility Methods

### `get_query_mentions()`

Extracts profiles, projects, and files from user query:

- Resolves @profile and @project mentions
- Identifies file-associated profiles
- Returns QueryMentions object with resolved references

### `get_chat_analysis_parents()`

Traverses parent chat hierarchy:

- Collects non-hidden message content from ancestors
- Respects ignore_parent_knowledge flag at each level
- Returns concatenated parent content string

### `get_profile_manager()`

Returns ProfileManager instance for current project settings.

### `get_chat_manager()`

Returns ChatManager, optionally scoped to specific project:

```python
def get_chat_manager(self, project_id: str = None) -> ChatManager
```

### `get_ai()`

Instantiates AI with specified model and optional system prompt:

```python
def get_ai(self, llm_model: Optional[str] = None, system: str = None) -> AI
```

### `switch_project()`

Switches engine context to different project:

```python
def switch_project(self, project_id: str) -> "ChatEngine"
```

### `convert_message()`

Converts DB Message to LangChain message type:

- Handles text, images, and role-based conversion
- Parses image metadata from JSON
- Returns appropriate LangChain message object

### `get_all_search_projects()`

Returns all searchable projects:

- Includes current project, child projects, and dependencies
- Useful for multi-project knowledge search

### `index_chat()`

Indexes chat as Document in knowledge system:

- Converts valid messages to single document
- Includes source and metadata
- Handles indexing errors gracefully

## Error Handling

### `_build_friendly_error_message()`

Extracts and formats API errors for user consumption:

- Parses OpenAI BadRequestError parameter constraints
- Provides user-friendly error messages
- Includes suggestions for resolution

## Helper Methods

### `_resolve_chat_mode_flags()`

Resolves boolean flags from chat mode and task item:

- Returns dictionary with mode flags and derived states
- Drives branching logic throughout processing

### `_evaluate_knowledge_flags()`

Determines if knowledge search should be disabled:

- Checks multiple disable conditions
- Emits appropriate event messages
- Returns final disable decision

### `_load_chat_files_content()`

Loads explicitly attached chat files:

- Reads file content from filesystem
- Formats with language-specific code fences
- Skips files already in message history

### `_hide_non_answer_messages()`

Hides non-answer messages in task mode:

- Marks all prior messages except answers as hidden
- Cleans up chat for document-focused workflows

## Configuration

The ChatEngine requires:

- **settings**: CODXJuniorSettings with project configuration
- **event_manager**: For emitting chat and search events
- **user** (optional): CodxUser for authenticated sessions

## Integration Points

- **LangChain**: Message format conversion and AI communication
- **AgentRuntime**: Provides AgentRunContext for tool execution tracking
- **ChatEventBridge**: Persists events and response state
- **ChatKnowledge**: Handles AI-driven document search
- **Knowledge/Milvus**: Vector database for RAG searches
- **ProfileManager**: Resolves active profiles and tools
- **Analytics**: Records session metrics and traceability
- **ChatManager**: Database operations for chat persistence

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/ai/cancellation.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/profiles/profile_manager.py, codx/junior/profiling/profiler.py, codx/junior/settings.py, codx/junior/utils/chat_utils.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/chat/chat_knowledge.py
**Imported by:** codx/junior/engine/chat_engine_actions.py, codx/junior/mentions/mention_manager.py, codx/junior/tools/code_writer.py, tests/chat/test_chat_manager.py