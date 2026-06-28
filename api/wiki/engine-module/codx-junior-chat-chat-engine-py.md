# Chat Engine Module

The `ChatEngine` is the central component responsible for managing AI-driven interactions within the CODX Junior project. It orchestrates context building, knowledge retrieval, message processing, and AI response generation.

## Overview
The engine serves as a bridge between user queries and AI models, supporting various interaction modes such as `task` (refinement), `agent` (iterative execution), `vibe` (AI-driven context search), and standard `chat`.

### Core Flowchart
The process follows a modular execution path:
1. **Resolution**: Determine chat mode, profiles, and project context.
2. **Pre-processing**: Execute optional `vibe` or `search` pre-searches to enrich the query.
3. **Knowledge Retrieval**: Perform RAG (Retrieval-Augmented Generation) document search across project dependencies.
4. **Context Building**: Assemble history, project files, and profile instructions into a prompt.
5. **Execution**: Invoke the AI model and process the response.
6. **Post-processing**: Extract file changes, generate summaries, and perform agent iterations if required.

## Key Functionalities

### Message Handling
- **Message Conversion**: Transforms database `Message` objects into `LangChain` compatible formats (`AIMessage`, `HumanMessage`), supporting both text and image content.
- **History Assembly**: Filters hidden or improvement-related messages to construct the conversation history for context (`_build_message_history`).
- **File Extraction**: Parses markdown code blocks containing filenames from AI responses to track generated code updates (`_extract_files_from_response`).

### Chat Modes
- **Task/Refine Mode**: Used for document refinement. It manages parent-child task contexts and allows the model to apply comments to existing documents without modifying untouched sections (`_append_refine_message`).
- **Agent Mode**: Executes iterative tasks where the AI attempts to solve a request until the `AGENT_DONE_WORD` is returned. It tracks iteration counts to prevent infinite loops (`_append_agent_message`).
- **Vibe/Search Mode**: Triggers AI-driven pre-search to gather context before formulating the final response (`_run_pre_search`).

### Knowledge and Search
- **RAG Integration**: Leverages `ChatKnowledge` to select documents based on the current query.
- **Constraint Management**: Knowledge searches can be dynamically disabled via the `_evaluate_knowledge_flags` method based on project settings, user message flags, or the absence of search projects.

### Lifecycle and Session Management
- **Cancellation**: Implements a `CancellationToken` system registered in a `CANCELLATION_REGISTRY`. This allows external processes to abort long-running requests by `chat.doc_id` or a specific `token_id`.
- **Project Switching**: The engine can dynamically switch context to another project if the `chat.project_id` differs from the current instance's settings via `switch_project`.
- **Auto-Initialization**: For chats flagged as `auto_initialize`, the engine invokes the AI to suggest metadata (name, board, column) based on conversation content, cleaning up the flag upon success.

## Helper Utilities
- **`chat_action`**: A context manager that ensures chat events (start, done, error) are properly emitted and logged.
- **`get_query_mentions`**: Resolves `@mentions` (profiles, projects, files) from user input to determine the scope of the interaction.
- **`get_chat_analysis_parents`**: Traverses ancestor chats to aggregate background context for complex task-oriented workflows.

## Configuration and Logging
- **Logging**: Extensive logging captures the lifecycle of every chat request, including resolved mode flags, profile usage, and error states.
- **Events**: Utilizes an `event_manager` to notify clients of real-time status updates, including search results, partial AI responses, and task completions.

---
*Reference: `codx/junior/chat/chat_engine.py`*

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/ai/cancellation.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/profiles/profile_manager.py, codx/junior/profiling/profiler.py, codx/junior/settings.py, codx/junior/utils/chat_utils.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/chat/chat_knowledge.py
**Imported by:** codx/junior/engine/chat_engine_actions.py, codx/junior/mentions/mention_manager.py, codx/junior/tools/code_writer.py, tests/chat/test_chat_manager.py