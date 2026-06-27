# AI Developer Assistant

## Overview
The AI Developer Assistant is a comprehensive, intelligent co-pilot platform designed to streamline and automate various aspects of the software development lifecycle. It acts as an advanced orchestration layer that integrates multiple specialized agents and engines to provide context-aware assistance directly within the engineering workflow.

This system moves beyond simple querying by utilizing Retrieval Augmented Generation (RAG) and connecting to diverse internal and external data sources, including project codebases, GitHub issues, enterprise wikis, and internal knowledge bases. Core functionalities include deep context understanding, advanced task automation, natural language query handling across multiple departments of documentation/code, and persistent chat state management for complex development tasks.

**Key Feature Areas:**
*   **Intelligent Agents:** Specialized agents (e.g., `devops_agent`, `git_issues_agent`) handle targeted job flows like deployment status checks or issue tracking.
*   **Knowledge Management:** Robust ingestion pipelines (`knowledge_loader`, `knowledge_splitter`) allow the system to consume proprietary documentation and code, making it searchable via vectors (Milvus).
*   **Chat & Interaction:** Sophisticated chat engines manage conversational context, ensuring continuity across complex development discussions.
*   **Project Context:** Tools manage project structure, file changes, and historical data, grounding AI responses in real-time codebase information.

## Files in Domain

The domain is highly modular, organized into functional directories covering APIs, knowledge management, core agents, chat handling, and infrastructure tooling.

### Core Application & API Logic
*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py`: Main application entry point.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/main.py`: Core system runner file.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py`: Manages session and conversation context.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/db.py`: Database connectivity handling.

### Agents & Specialized Tools
The system utilizes modular agent classes for specific development tasks:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base class for all specialized agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Handles DevOps tasks and pipeline interactions.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Interacts with GitHub issue tracking systems.

### AI Backend & Service Logic
This section contains the LLM integration points and general utilities:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py`: Abstract factory for different LLM providers.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py`: Implementation for OpenAI services.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py`: Integration layer for local Ollama models.

### Knowledge Base (RAG) Module (`knowledge/`)
This dedicated module handles all data ingestion, splitting, embedding, and retrieval:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py`: Responsible for loading raw data from various sources (files, wikis).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py`: Handles chunking and splitting large documents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_db.py`: Manages interactions with the vector database (Milvus).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py`: Implementation layer for Milvus integration.
*   Utility scripts include: `knowledge_code_to_dcouments.py`, `knowledge_qa_splitter.py`, and environment setup files (`settings.py`).

### API Endpoints & Project Management
These files define the interfaces for interacting with external services or project data:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py`: Handles GitHub API interactions (issues, commits).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/users.py`: User and identity management.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py`: Dedicated API layer for wiki content access.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/project/project_manager.py`: Core logic for managing project context and discovery (`project_discover.py`).

### Messaging & State Management
These files handle real-time communication, chat history, and event listeners:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_manager.py`: Orchestrates the conversational flow.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/*`: Files related to Socket.IO for real-time, bidirectional communication (essential for co-pilot feel).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/events/event_manager.py`: Handles internal system events and state changes.

## Dependencies

The AI Developer Assistant relies on several conceptual service dependencies to fulfill its functions:

1.  **Large Language Models (LLMs):** Dependency on external providers (OpenAI, Mistral) or local models (Ollama) via the dedicated `ai/` package structure (`openai_ai.py`, `ollama.py`).
2.  **Vector Database:** Requires a highly scalable vector store (Milvus is used) for effective RAG implementations.
3.  **Source Control Systems:** Deep integration with GitHub APIs (`github.py`) for reading commit history, branch status, and issues.
4.  **Messaging & Event Bus:** Relies on Socket.IO (`sio/` files) for maintaining real-time communication between agents and the client.
5.  **Internal Knowledge Repositories:** Requires mechanisms to ingest structured (CRM data, user profiles) and unstructured (Wiki, Codebases) knowledge sources.

## Used By

This domain acts as a centralized intelligence service. While direct calling modules aren't listed, the outputs of this system are designed to be consumed by:

*   **Frontend/Client Application:** The main UI layer that interacts with `/app.py` and manages real-time chat via Sio.
*   **Worker Background Processes (`background.py`):** Routines responsible for periodic tasks such as project watching, change management, and scheduled knowledge ingestion.
*   **CLI Tooling / Orchestrator:** A shell or CLI interface that calls the central API to manage developer workflow (e.g., submitting a complex multi-step coding task).

## Entry Points

The following files serve as primary entry points, allowing developers or services to start utilizing the core features of the domain:

*   `/home/codx-junior-projects/codx-junior/api/README.md`: General documentation and introduction to the system.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: The foundational class for creating or initializing new specialized agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Direct entry point for interacting with deployment and infrastructure knowledge within the system.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Point of entry for querying developer workflow data from issue trackers.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: The core module that initializes and manages the selected Large Language Model backend.