# AI Agent Orchestration System

## Overview

The AI Agent Orchestration System is a sophisticated, advanced AI agent framework engineered specifically to assist in complex software development workflows. It serves as a central platform that integrates multiple Large Language Models (LLMs) with specialized agents, enabling deep interaction with project files, live codebases, and external version control systems such as Git.

This system significantly enhances developer productivity by moving beyond simple query-response interactions. Key functionalities include:

*   **Multi-Agent Coordination:** It orchestrates specialized agents (e.g., `devops_agent`, `git_issues_agent`) to work together on complex, multi-step development tasks.
*   **Deep Knowledge Retrieval (RAG):** It provides advanced RAG capabilities, allowing the system to index and retrieve deep knowledge from internal corporate documents, project specifications, and wiki pages.
*   **Full Lifecycle Support:** The framework supports execution of tasks across the entire software development lifecycle, including coding, testing, deployment preparation, and issue tracking integration.

By unifying LLM access, version control management, file system interaction, and internal knowledge retrieval, this platform transforms raw LLM power into highly structured, operational developer assistance.

## Files in Domain

The following files make up the codebase for the AI Agent Orchestration System:

**Configuration & Root Assets:**
*   `README.md` (Root Project)
*   `api/pyproject.toml`
*   `api/shared/codx-junior/scripts/docker-compose.yaml`
*   `api/shared/codx-junior/scripts/traefik/traefik.yaml`

**API and Core Modules (`api/codx/junior/api`)**:
*   `README.md` (Api)
*   `api/codx/junior/global_settings.py` (Duplicated usage, but listed once: `api/codx/junior/profiles/global_settings.py` is also present)

**Agents (`api/codx/junior/agents`)**:
*   `base_agent.py`
*   `devops_agent.py`
*   `git_issues_agent.py`

**AI Model Integration & Utilities (`api/codx/junior/ai`)**:
*   `utils.py`
*   `anthropic.py.disabled`
*   `llmfactory.py`
*   `openai_ai.py`
*   `ollama.py`

**API Endpoints & Managers (`api/codx/junior/api`)**:
*   `chatGPTLikeApi.py`
*   `db_router.py`
*   `file_finder.py`
*   `github.py` (Multiple instances detected: `api/codx/junior/api/github.py` and `api/codx/junior/misc/github.py`)
*   `global_settings.py`

**User & Context Management:**
*   `users.py`
*   `app.py` (Main API entry point)
*   `context.py`

**Knowledge Base / RAG (`api/codx/junior/knowledge`)**:
*   `README.md`
*   `__init__.py`
*   `knowledge_loader.py`
*   `knowledge_milvus.py` (Vector DB integration)
*   `knowledge_splitter.py`
*   `knowledge_code_to_dcouments.py`
*   `knowledge_keywords.py`
*   `knowledge_qa_splitter.py`
*   `knowledge_settings.py`

**Messaging and Utilities:**
*   `chat/chat_engine.py`
*   `chat/chat_export.py`
*   `chat_manager.py`
*   `utils/chat_utils.py`
*   `utils/utils.py`
*   `log_parser.py`

**Project Management and Change Detection:**
*   `changes/watch_project_file_changes.py`
*   `model/wallet.py` (Potential persistence layer component)
*   `api/codx/junior/project/project_discover.py`
*   `api/codx/junior/project/project_manager.py`

**Advanced Engines (`api/codx/junior/engine`)**:
*   `file_engine.py`
*   `git_engine.py`
*   `knowledge_engine.py`
*   `session.py`
*   `wiki_engine.py`

**Chat & Conversation Flow (`api/codx/junior/chat`)**:
*   `chat_knowledge.py` (Integration of knowledge retrieval into chat flow)

**Profiling and Metrics:**
*   `metrics/chat_heatmap.py`
*   `metrics/chat_wall.py`
*   `metrics/codx_junior_metrics.py`
*   `profiling/profiler.py`

**Profiles & Identity (`api/codx/junior/profiles`)**:
*   `agent-coding-task.md`
*   `analyst.profile` / `.md`
*   `browser.profile`
*   `coding_profiles.json`
*   `profile_manager.py`
*   `project.profile`
*   `software_developer.profile`
*   `wiki.profile`

**Tools & Tooling (`api/codx/junior/tools`)**:
*   `__init__.py`
*   `code_writer.py`
*   `fetch_webpage.py`
*   `project_tools.py`

**Wiki Module:**
*   `wiki/README.md`
*   `wiki/model.py`
*   `wiki/wiki_manager.py`
*   *(Includes nested `wiki_template` files for development setup)*

**Session Integration (SignalR Core):**
*   `sio/model.py`
*   `sio/session_channel.py`
*   `sio/sio.py`
*   `sio/sio_background.py`

**Testing Files (`api/tests`)**:
*   (Multiple test files referencing components like `test_chat_manager.py`, `project_file_watcher.py`, etc.)

## Dependencies

*Note: The input provided no specific dependency file list (`depends_on_files`). This section represents the conceptual dependencies based on domain structure.*

**Conceptual Dependencies:**

The system is highly interconnected, relying on several core components:

1.  **AI Backend:** Relies on multiple LLM interfaces (OpenAI/Anthropic/Ollama) combined via `llmfactory.py`.
2.  **Database & State Management:** Uses structured databases (implied by `db_router.py`, and possibly Milvus for vector storage).
3.  **Networking & Real-time:** Heavily dependent on SignalR (`sio/*` files) for real-time communication (e.g., chat, file changes).
4.  **Knowledge Retrieval:** Core functionality relies on knowledge splitting, loading, and semantic search strategies defined in the `knowledge/` folder.
5.  **Version Control Integration:** Explicit dependency on Git logic housed in `git_engine.py` and `agents/git_issues_agent.py`.

## Used By

*Note: The input provided no list of files using this domain (`used_by_files`). This section represents key files that utilize the core services.*

**Core Utilization Points:**

Any major user interaction point or orchestration layer uses these services heavily:

1.  `app.py`: Likely the main ASGI/API entry point, orchestrating calls to multiple agents and engines.
2.  `chat_manager.py` & `chat_engine.py`: Manage state flow and invoke knowledge retrieval and agent actions during conversations.
3.  `main.py`: The primary execution wrapper for the entire system logic.
4.  `task_manager.py`: Orchestrates background, asynchronous tasks (e.g., watching file changes, indexing documents).

## Entry Points

The following files serve as key entry points and initialization modules defining how external systems interact with or start components within the domain:

*   `/home/codx-junior-projects/codx-junior/api/README.md` (Root documentation)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Defines the core agent structure.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Entry point for DevOps operations capabilities (e.g., deployment, infrastructure checks).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Specialized agent for interacting with Git and issue tracking systems.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Initialization point for the various LLM integration layers (`openai`, `ollama`, etc.).