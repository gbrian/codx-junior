# ChatEngine Documentation

## Overview

The `ChatEngine` is the core engine for managing chat interactions with AI models in the CODX Junior system. It handles message processing, knowledge search, context building, and AI response generation for various chat modes. The engine integrates comprehensive analytics tracking for chat sessions, token usage, and tool executions to enable full request-response traceability.

## Initialization

The `ChatEngine` is initialized with project settings, an event manager, and an optional authenticated user:

```python
def __init__(
    self,
    settings: CODXJuniorSettings,
    event_manager,
    user: CodxUser = None
) -> None
```

The engine sets up knowledge management components (`Knowledge`, `ChatKnowledge`) and analytics tracking for the current project context.

## Core Features

### Chat Modes

The engine supports multiple chat modes that drive different processing behaviors:

- **CHAT_MODE_TASK** (`"task"`): Task/refinement mode that processes document refinement with comments
- **CHAT_MODE_AGENT** (`"agent"`): Agent mode with iterative task completion
- **CHAT_MODE_VIBE** (`"vibe"`): Vibe mode using AI-driven search
- Standard chat mode: Regular conversational interaction

### Message Processing

The engine maintains separate handling for different message types:

- **Standard messages**: User and assistant messages included in LLM prompt context
- **Tool/lifecycle messages**: Messages with `role == ROLE_TOOL` are visible to users but excluded from LLM prompts (persisted via `ChatEventBridge`)
- **Hidden messages**: Messages marked with `hide` flag are excluded from processing
- **Improvement messages**: Messages marked as improvements are filtered out

### Knowledge Search

Two knowledge search mechanisms are available:

1. **Pre-search** (for vibe and search modes): AI-driven search combining conversation history with current query
2. **RAG knowledge search** (standard mode): Document retrieval across configured search projects

## Main Entry Point

### chat_with_project

The primary method for processing chat interactions:

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

#### Processing Flow

The method follows this sequence:

1. **Project Context**: Switches project context if the chat belongs to a different project
2. **Cancellation Registration**: Registers a `CancellationToken` at the root iteration, enabling client-side cancellation via token ID or chat ID
3. **Mode Resolution**: Determines active chat mode and resolves boolean flags
4. **Query Analysis**: Extracts mentions of profiles, projects, and files from the user query
5. **File Collection**: Gathers files from all visible messages and parent chats
6. **Profile Resolution**: Determines active profiles, LLM model, and available tools
7. **Knowledge Evaluation**: Assesses whether knowledge search should be enabled
8. **Message History**: Builds LangChain message history excluding hidden/tool messages
9. **AI Configuration**: Sets up AI instance with merged system prompts from profiles
10. **Pre-search Execution**: Runs AI-driven search for vibe/search modes
11. **RAG Search**: Performs standard knowledge search if enabled
12. **Prompt Assembly**: Constructs final message list for AI invocation
13. **Tool/Event Bridge**: Creates `ChatEventBridge` and `AgentRunContext` for surfacing tool events
14. **AI Response**: Executes AI call with streaming support and handles cancellation
15. **Response Parsing**: Extracts code blocks and metadata from response
16. **Description Generation**: Creates conversation summary via AI
17. **Metadata Auto-initialization**: Auto-fills chat metadata for `auto_initialize` chats
18. **Agent Recursion**: Recurses for agent mode if task not completed and iterations remain
19. **Session Recording**: Records analytics for chat session start and end

#### Cancellation Support

A `CancellationToken` is registered for each chat at the root iteration (iteration == 0). The token ID is stamped into the response message's `meta_data` immediately, allowing clients to receive it in the first streaming event. Cancellation can be triggered via:

- `CANCELLATION_REGISTRY.cancel(chat.doc_id)` — by chat ID
- `CANCELLATION_REGISTRY.cancel_by_token_id(token_id)` — by token UUID

When cancelled, the response message includes a `"cancelled_at"` timestamp in its metadata.

#### Tool and Lifecycle Events

Tool executions and agent runtime lifecycle events are surfaced in real-time as `role="tool"` chat messages through the `ChatEventBridge`. These messages are:

- Persisted on every change for crash-safety
- Streamed to clients immediately
- Visible in the UI but excluded from LLM prompt context

## Helper Methods

### Message History Building

**`_build_message_history`**: Converts non-hidden, non-improvement, non-tool messages (excluding the last) into LangChain message objects for the LLM context.

**`_build_clean_message_history_for_description`**: Creates a cleaner message history that excludes system prompts, profile content, and file details, suitable for generating summaries.

### File Management

**`_collect_files_from_visible_messages`**: Collects and deduplicates all file references from visible messages and chat-level base files, ensuring deterministic ordering.

**`_load_chat_files_content`**: Reads and formats content of explicitly attached chat files, skipping files already embedded in message history.

**`_resolve_chat_file_path`**: Resolves full filesystem paths for chat-attached files, normalizing relative paths against the project directory.

### Context Building

**`_resolve_profiles_and_model`**: Derives active profiles, LLM model, tool list, and profile content string from query mentions and chat state. Profiles are sorted by name and their content is formatted for inclusion in the system prompt.

**`_evaluate_knowledge_flags`**: Determines whether knowledge search should be disabled based on multiple conditions (explicit disable, no search projects, project settings, user message flags).

### Search Operations

**`_run_pre_search`**: Executes AI-driven pre-search for vibe and search modes, combining conversation history with current query to build a richer search query.

**`_run_rag_knowledge_search`**: Performs standard RAG document search across configured search projects, handling errors and emitting events.

### Prompt Assembly

**`_build_ai_prompt_messages`**: Assembles the final list of LangChain messages for AI invocation, appending context, working files, and mode-specific prompts (refine/agent/standard).

**`_append_refine_message`**: Appends a task-refinement prompt when in task mode. If a previous AI document exists, it instructs the model to apply comments to it. Incorporates parent context if available.

**`_append_agent_message`**: Appends an agent-style prompt instructing the model to complete a task with iteration tracking. Incorporates parent context and iteration count.

### Response Processing

**`_extract_files_from_response`**: Parses markdown code blocks in the response content with the format `` ```language filename `` to extract files with language, path, and content.

**`_execute_ai_response`**: Invokes the appropriate AI or search handler and extracts response parts (thinking content, main content, extracted files). Handles both standard AI chat and knowledge search modes with streaming support.

**`_finalize_response_metadata`**: Stamps the response message with timing information, model metadata, and extracted files, preserving fields like `cancellation_token_id` that were set earlier.

### Chat Enhancement

**`_generate_chat_description`**: Generates a short AI-powered summary of the conversation, maintaining a timestamped history of descriptions as the chat evolves.

**`_auto_initialize_chat_metadata`**: For `auto_initialize` chats, uses AI to suggest values for `name`, `board`, and `column` based on conversation content.

**`_hide_non_answer_messages`**: In task mode, hides all prior messages not marked as answers.

### Analytics Recording

**`_record_chat_session_start`**: Records the start of a chat session with initial context including mode, profiles, files, iteration count, and model information.

**`_record_chat_session_end`**: Records the end of a chat session with final metrics including duration, message counts, cancellation state, and error information.

## Cancellation Methods

### cancel_chat

```python
def cancel_chat(self, chat_doc_id: str) -> bool
```

Cancels an in-flight chat request by chat document ID. Returns `True` if a token was found and cancelled, `False` otherwise.

### cancel_chat_by_token_id

```python
def cancel_chat_by_token_id(self, token_id: str) -> bool
```

Cancels an in-flight chat request by cancellation token ID. This is the preferred method when the client has the token ID from the response metadata.

## Project Management

### switch_project

```python
def switch_project(self, project_id: str) -> "ChatEngine"
```

Switches the engine to another project based on the provided project ID, re-initializing the `ChatKnowledge` component for the new project context.

### get_all_search_projects

```python
def get_all_search_projects(self) -> List[CODXJuniorSettings]
```

Returns all projects including the current project, child projects, and project dependencies for comprehensive search scope.

## AI Configuration

### get_ai

```python
def get_ai(self, llm_model: Optional[str] = None, system: str = None) -> AI
```

Creates an AI instance configured for a specific model with optional system prompt override.

### get_ai_code_generator_changes

```python
def get_ai_code_generator_changes(self, response: str) -> AICodeGenerator
```

Processes the AI response string to generate code generator changes, normalizing file paths to absolute project paths.

## Query Analysis

### get_query_mentions

```python
def get_query_mentions(self, chat: Chat, user_message: Message) -> QueryMentions
```

Extracts mentions of profiles and projects from the user query, including profiles associated with attached files.

### get_chat_analysis_parents

```python
def get_chat_analysis_parents(self, chat: Chat) -> str
```

Traverses all parent chats and returns concatenated non-hidden message content, providing context for child chat processing.

## Message Conversion

### convert_message

```python
@staticmethod
def convert_message(message: Message)
```

Converts a database Message object into a LangChain message type (`HumanMessage` or `AIMessage`), handling text-only messages, image messages, and role-based conversion.

## Knowledge Indexing

### index_chat

```python
def index_chat(self, chat: Chat) -> None
```

Indexes a chat as a Document in the knowledge system, converting valid chat messages into a single Document with appropriate metadata. Tool/lifecycle event messages are excluded.

## Context Manager

### chat_action

```python
@contextmanager
def chat_action(self, chat: Chat, event: str)
```

Context manager that emits start/done/error events around a chat action, providing consistent event lifecycle management and logging for debugging.

## Integration Points

The `ChatEngine` integrates with several core components:

- **Analytics**: Tracks chat sessions for comprehensive analytics
- **ChatEventBridge**: Surfaces tool and lifecycle events as persistent chat messages
- **AgentRunContext**: Manages agent runtime context and event listeners
- **ProfileManager**: Resolves active profiles and their configurations
- **ChatManager**: Manages chat persistence and retrieval
- **Knowledge system**: Performs document search and indexing

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/ai/cancellation.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/profiles/profile_manager.py, codx/junior/profiling/profiler.py, codx/junior/settings.py, codx/junior/utils/chat_utils.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/chat/chat_knowledge.py
**Imported by:** codx/junior/engine/chat_engine_actions.py, codx/junior/mentions/mention_manager.py, codx/junior/tools/code_writer.py, tests/chat/test_chat_manager.py