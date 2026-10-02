# AI-Powered Developer Assistant

## Overview
This platform is a comprehensive, intelligent assistant designed specifically for developers. It acts as an orchestration layer that integrates multiple real-world tools and knowledge sources within a unified system. Its core capability lies in utilizing various Large Language Models (LLMs) to process complex organizational knowledge—including project structure, Git repositories, Wiki content, user data, and historical interactions—to enable specialized AI agents.

The architecture supports advanced functionalities ranging from code generation and analysis to DevOps management and task automation. It utilizes a modular agent framework (`BaseAgent`) and is highly structured around various APIs for interaction (e.g., `git`, `wiki`, `project`, `user`).

**Key Features & Functionalities:**
*   **Agent System:** Dedicated agents for specialized tasks like Git issue tracking, DevOps operations, and general project interactions.
*   **Knowledge Management:** Advanced modules (`knowledge/`) designed to ingest diverse data types (code, text documents, wiki pages) and store them in vector databases (e.g., Milvus) for Retrieval-Augmented Generation (RAG).
*   **LLM Integration:** Supports multiple LLM providers (OpenAI, Mistral, Ollama, Anthropic, etc.) via a unified factory pattern (`llmfactory.py`).
*   **Workflow/Process Tools:** Includes mechanisms for change tracking, file watching, project discovery, and session management.

## Files in Domain

The codebase is extensive and highly organized into functional domains, including `agents`, `api`, `chat`, `knowledge`, `model`, and various `tools`.

### Core Infrastructure & Utilities
*   `api/README.md`: General API documentation.
*   `api/codx/junior/ai/*`: Modules handling LLM interactions, logging, and utilities (e.g., `openai_ai.py`, `ollama.py`, `llmfactory.py`).
*   `api/codx/junior/context.py`: Global state management for the current session context.
*   `api/codx/junior/utils/*`: General purpose helper functions and utilities (`chat_utils.py`, `utils.py`).
*   `api/codx/junior/global_settings.*`: Files for centralized configuration and global states.

### Agents (Specialized LLM Workers)
*   `agents/base_agent.py`: Abstract base class defining the structure for all specialized agents.
*   `agents/devops_agent.py`: Agent responsible for DevOps-related operations and maintenance tasks.
*   `agents/git_issues_agent.py`: Agent dedicated to interacting with and managing Git issues.

### APIs & Integrations (Tooling)
The platform contains numerous granular API modules providing structured access to external or internal services:
*   **Workflow:** `api/codx/junior/changes/*`, `api/codx/junior/project/*`, `api/codx/junior/workspace/*` (Handling file/code changes, project discovery).
*   **Data Sources:** `api/codx/junior/api/github.py`, `api/codx/junior/api/wiki.py`, `api/codx/junior/api/users.py`, `api/codx/junior/api/global_settings.py`.
*   **Core Services:** `api/codx/junior/db_router.py` (Database access abstraction).
*   **User Experience:** Modules for chat history, mentions, and metrics (`chat_manager.py`, `mention_manager.py`).

### Knowledge Management System (KMS)
This section is critical for the AI's ability to recall and utilize deep domain knowledge:
*   `knowledge/knowledge_db.py`: Handles database operations for stored knowledge chunks.
*   `knowledge/knowledge_loader.py`: Responsible for loading raw data into the system.
*   `knowledge/knowledge_splitter.py`: Logic for chunking large documents (code, text) before embedding.
*   `knowledge/knowledge_milvus.py`: Integration layer for the vector database Milvus.
*   `knowledge/knowledge_training.py`: Utility for improving or training knowledge models.
*   Various `prepromts/*.md`: Files containing prompt engineering templates for document enrichment and query splitting, guiding how context is prepared for the LLM.

### Chat and Orchestration
*   `chat/chat_engine.py`: The core logic managing the conversation flow and calling agents/tools.
*   `engine/*`: Modules that define the execution pipeline (e.g., `file_engine.py`, `git_engine.py`, `knowledge_engine.py`).
*   `main.py`/`app.py`: Entry points for running the application lifecycle.

## Dependencies
The domain relies heavily on internal structures for modularity and robust operation:

1.  **Tooling/Execution Dependency:** The entire structure relies on having defined tools (e.g., `code_writer.py`, `fetch_webpage.py`) that agents can call and execute actions through structured functions within the API layer.
2.  **Database Layer:** A consistent dependency on a database mechanism (`db.py`, `db_router.py`, potentially Milvus) is necessary for persistent storage of context, user profiles, and retrieved knowledge chunks.
3.  **LLM Providers:** Dependence on external SDKs or APIs for various LLMs (OpenAI, Mistral, etc.). The use of `llmfactory.py` abstracts these dependencies but assumes connectivity and proper API keys/credentials.
4.  **Web Framework:** Use of a session management system (`sio/`) suggests dependency on WebSocket communication structures.

## Used By
(No files explicitly declared as using this domain's entry points or primary classes in the provided list, suggesting it is likely the root application module itself.)

## Entry Points
These are the files designed to be executed directly to start the system:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Used for initializing and managing agent execution logic.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Triggering DevOps automation workflows.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Starting a dedicated Git issue resolution or investigation task.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Initializing the core AI services and LLM handlers.