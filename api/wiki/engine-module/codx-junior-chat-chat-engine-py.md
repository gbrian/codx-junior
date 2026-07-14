# ChatEngine — Developer Wiki

## Overview

`ChatEngine` is the core orchestration class responsible for managing AI-powered chat interactions within a project. It handles the full lifecycle of a chat turn: context gathering, knowledge search, prompt assembly, AI invocation, response streaming, and agent iteration. It is located in `codx/junior/chat/chat_engine.py`.

---

## Architecture

The engine follows a branching pipeline model, summarised by the main flowchart:

```
User Message → {Chat Mode?}
  vibe/search  → AI Search Context → Build Context → Standard Chat → AI Response
  task         → Refine Document → AI Response
  agent        → Agent Prompt → AI Response (→ recurse if not done)
  chat         → Standard Chat → AI Response
                                              ↓
                                   Return Chat + Documents
```

---

## Initialization

```python
ChatEngine(settings, event_manager, user=None)
```

| Parameter       | Type                    | Description                                      |
|----------------|-------------------------|--------------------------------------------------|
| `settings`      | `CODXJuniorSettings`    | Project settings for the current context         |
| `event_manager` | Any                     | Emits chat and message events to clients         |
| `user`          | `CodxUser` (optional)   | Authenticated user for the session               |

On construction the engine also instantiates:
- `Knowledge` — for RAG document indexing/search
- `ChatKnowledge` — for AI-driven context search

---

## Chat Modes

Defined as module-level constants:

| Constant           | Value      | Description                                                  |
|--------------------|------------|--------------------------------------------------------------|
| `CHAT_MODE_TASK`   | `"task"`   | Refines an existing document based on user comments          |
| `CHAT_MODE_AGENT`  | `"agent"`  | Iterative task completion with a done-word termination check |
| `CHAT_MODE_VIBE`   | `"vibe"`   | AI-driven pre-search for richer contextual responses         |
| `TASK_ITEM_SEARCH` | `"search"` | Pure knowledge search, bypasses normal AI chat               |
| `TASK_ITEM_ANALYSIS`| `"analysis"`| Used internally when task mode is active                  |

Flags are resolved by `_resolve_chat_mode_flags()`, which derives boolean values (`is_refine`, `is_agent`, `is_vibe`, `is_search`, `needs_pre_search`) from the resolved mode string.

---

## Main Entry Point

### `chat_with_project`

```python
async def chat_with_project(
    chat, disable_knowledge=False, callback=None,
    append_references=True, chat_mode=None, iteration=0, system=None
)
```

This is the public API for processing a chat turn. It:

1. Detects if the chat belongs to a different project and delegates via `switch_project()`.
2. Registers a `CancellationToken` in `CANCELLATION_REGISTRY` at iteration 0.
3. Delegates all logic to `_chat_with_project_inner()`.
4. Unregisters the cancellation token when the root iteration completes.

**Returns:** `Tuple[Chat, List[Document]]`

---

### `_chat_with_project_inner` — Processing Pipeline

This internal method executes the full 24-step pipeline:

| Step | Description |
|------|-------------|
| 1 | Collect timing information |
| 2 | Extract user message and visible message content |
| 3 | Resolve chat mode flags via `_resolve_chat_mode_flags()` |
| 4 | Account for agent iterations |
| 5 | Resolve parent chat if `chat.parent_id` is set |
| 6 | Initialise response message; stamp `cancellation_token_id` into `meta_data` |
| 7 | Resolve query mentions (profiles, files, projects) |
| 8 | Collect all files from visible messages and merge with parent/mention files |
| 9 | Resolve profiles, model, and tools via `_resolve_profiles_and_model()` |
| 10 | Resolve search projects from query mentions |
| 11 | Evaluate knowledge disable conditions |
| 12 | Build LangChain message history from prior turns |
| 13 | Load explicitly attached chat file contents |
| 14 | Prepare the AI instance |
| 15 | Build AI request headers and tags |
| 16 | Define streaming event emitter (`send_message_event`) |
| 17 | Initialise document accumulator |
| 18 | Run pre-search if `is_vibe` or `is_search` |
| 19 | Run standard RAG knowledge search |
| 20 | Assemble final prompt messages |
| 21 | Execute AI or search response |
| 22 | Extract files from response; finalize response metadata |
| 23 | Generate conversation summary; auto-initialize metadata if flagged |
| 24 | Recurse for agent iteration if not done |

---

## Cancellation

The engine integrates a cancellation system via `CANCELLATION_REGISTRY`.

- A `CancellationToken` is registered at the start of the root iteration and unregistered on completion.
- The `token_id` (UUID4) is stamped into `response_message.meta_data["cancellation_token_id"]` immediately so clients receive it in the first streaming event.
- Cancellation can be triggered by:
  - `cancel_chat(chat_doc_id)` — cancels by chat `doc_id`
  - `cancel_chat_by_token_id(token_id)` — cancels by the token UUID

On `CancelledError`, the response message receives a `"cancelled_at"` ISO-8601 timestamp in `meta_data`, and a default cancellation message is set if the content is empty.

---

## Knowledge Search

### Pre-search (`_run_pre_search`)

Used in `vibe` and `search` modes. Combines conversation history with the current query before delegating to `ChatKnowledge.ai_search_for_context()`. Returns `(documents, file_list, context_string)`.

### RAG Search (`_run_rag_knowledge_search`)

Standard retrieval-augmented generation search. Creates a knowledge search query from the message history and current query, then calls `ChatKnowledge.select_documents_from_knowledge()` across the resolved search projects. Returns `(documents, file_list, context_string)`.

Knowledge search is disabled when any of the following is true (evaluated by `_evaluate_knowledge_flags()`):
- `disable_knowledge=True` passed to `chat_with_project`
- No search projects are found
- `settings.use_knowledge` is `False`
- `user_message.disable_knowledge` is `True`

---

## Prompt Assembly

### `_build_ai_prompt_messages`

Assembles the final list of LangChain messages to send to the AI:

```
Start
  → Append context message (if context exists)
  → {Mode?}
      is_refine → _append_refine_message()
      is_agent  → _append_agent_message()
      else      → Append user message directly
  → Prepend working files header (if chat_files_content)
  → Append profile instructions (if chat_profiles_content)
  → Return messages
```

### Refine Mode (`_append_refine_message`)

If a previous AI document exists, the prompt instructs the model to apply the user's comments to that document. Otherwise, it uses the raw user message content. Parent document context is also included unless `chat.ignore_parent_knowledge` is set.

### Agent Mode (`_append_agent_message`)

Builds a task-oriented prompt including the chat name, parent context, user request, and the number of remaining iterations. Instructs the model to return `AGENT_DONE_WORD` when finished.

---

## File Handling

### `_collect_files_from_visible_messages`

Performs a set union of `chat.file_list` and the `.files` property of every non-hidden, non-improvement message. Returns a deduplicated, sorted list.

### `_load_chat_files_content`

Reads and formats files attached to the chat as code blocks using `document_to_code_block()`. Files already present as code block references in the message history (detected by scanning for lines starting with ` ``` `) are skipped to avoid duplication.

### `_resolve_chat_file_path`

Resolves a relative or absolute file path to a full filesystem path under `settings.abs_project_path`.

### `_extract_files_from_response`

Parses markdown code blocks from the AI response in the format:

```
```language filename
code content
```
```

Returns a list of dicts with keys `language`, `file_path`, and `content`. Extracted files are stored in `response_message.meta_data["files"]`.

---

## Profiles and Model Resolution

`_resolve_profiles_and_model()` derives:

| Output Key              | Description                                                              |
|-------------------------|--------------------------------------------------------------------------|
| `chat_profiles_content` | Concatenated profile instruction strings                                 |
| `chat_profile_names`    | Names of active profiles                                                 |
| `chat_model`            | LLM model name (from chat setting or first profile with a model defined) |
| `chat_tools`            | Deduplicated list of tools from all active profiles                      |
| `is_refine`             | May be set to `True` if any profile has `chat_mode == CHAT_MODE_TASK`    |

If no profiles are active but chat files are attached, a default instruction to preserve unchanged content is used.

---

## Response Metadata

`_finalize_response_metadata()` stamps the following keys into `response_message.meta_data`:

| Key                     | Description                                         |
|-------------------------|-----------------------------------------------------|
| `time_taken`            | Total elapsed seconds for the turn                  |
| `first_chunk_time_taken`| Seconds until first streaming chunk                 |
| `model`                 | Name of the model used                              |
| `files`                 | List of file dicts extracted from code blocks       |
| `cancellation_token_id` | Token UUID (set earlier, preserved by merge logic)  |

The merge strategy starts from `user_message.meta_data`, then overlays `response_message.meta_data` on top, ensuring fields stamped earlier (like `cancellation_token_id`) are not overwritten.

---

## Conversation Summarisation

### `_generate_chat_description`

After each non-search turn, the engine calls the AI with a 5-line summary prompt. The result is stored in `chat.description` and appended to `chat.history` as a `ChatHistoryEntry` with a UTC timestamp and the current message IDs.

### `_auto_initialize_chat_metadata`

If `chat.auto_initialize` is `True`, the engine calls the AI with `CHAT_INIT_PROMPT` to suggest values for `name`, `board`, and `column`. Only blank fields are overwritten. On success, `auto_initialize` is set to `False`.

The prompt instructs the AI to return a JSON object with up to three keys:
```json
{"name": "...", "board": "...", "column": "..."}
```

---

## Agent Iteration

When `is_agent=True` and the response does not contain `AGENT_DONE_WORD`, and iterations remain, the engine recurses via `_chat_with_project_inner()` with `iteration + 1`. The maximum number of iterations is controlled by `settings.get_agent_max_iterations()`. The cancellation token is reused across iterations.

---

## Project Switching

### `switch_project`

Replaces `self.settings` with the settings for the given `project_id` (resolved via `find_project_by_id`) and re-instantiates `ChatKnowledge`. If the project is not found, a warning is logged and the current settings are retained.

### `get_all_search_projects`

Returns a combined list of the current project, its child projects, and its dependency projects, used to scope knowledge searches.

---

## Utility Methods

| Method | Description |
|--------|-------------|
| `get_ai(llm_model, system)` | Creates a configured `AI` instance |
| `get_profile_manager()` | Returns a `ProfileManager` for the current settings |
| `get_chat_manager(project_id)` | Returns a `ChatManager`, optionally scoped to another project |
| `get_query_mentions(chat, user_message)` | Extracts `@profile`, `@project`, and file mentions from the query |
| `get_chat_analysis_parents(chat)` | Traverses ancestor chats and returns concatenated non-hidden message content |
| `get_ai_code_generator_changes(response)` | Parses AI response into an `AICodeGenerator` with file-path-resolved changes |
| `convert_message(message)` | Converts a DB `Message` to a LangChain `HumanMessage` or `AIMessage` |
| `index_chat(chat)` | Indexes all visible chat messages as a single `Document` in the knowledge system |

---

## Context Manager

### `chat_action`

```python
@contextmanager
def chat_action(self, chat, event):
```

Wraps a block of code with start, done, and error events emitted via `event_manager.chat_event()`. All exceptions are caught, logged, and surfaced as error events without re-raising.

---

## Task Mode Cleanup

`_hide_non_answer_messages()` is called in `task` and `vibe` modes after the response is appended. It iterates over all prior messages and sets `hide=True` on any message not marked as `is_answer`, keeping the chat view focused on the refined document.

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/ai/cancellation.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/profiles/profile_manager.py, codx/junior/profiling/profiler.py, codx/junior/settings.py, codx/junior/utils/chat_utils.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/chat/chat_knowledge.py
**Imported by:** codx/junior/engine/chat_engine_actions.py, codx/junior/mentions/mention_manager.py, codx/junior/tools/code_writer.py, tests/chat/test_chat_manager.py