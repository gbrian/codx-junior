# Intelligent Development Agent Framework
## Overview
The Intelligent Development Agent Framework is an advanced AI copilot platform designed to automate and manage complex software development workflows. At its core, it operates by deploying specialized autonomous **agents** that tackle diverse engineering tasks—from writing code and executing DevOps operations to managing technical queries and consulting institutional knowledge.

This system significantly differentiates itself through its robust integration of knowledge retrieval systems (RAG). It is specifically engineered to ground the agents' responses and decisions not only in general LLM capabilities but critically, in internal corporate documentation, proprietary wikis, and active codebases. The framework enables autonomous task execution across multiple development phases, ensuring consistency and high fidelity when interacting with an organization's unique technical landscape.

**Key Capabilities:**
*   **Autonomous Agents:** Specialized agents for distinct workflows (e.g., `DevOpsAgent`, `GitIssuesAgent`, coding tasks).
*   **Knowledge Grounding:** Retrieval of information from internal wikis, documents, and codebases to provide contextually accurate answers.
*   **Workflow Management:** Handling complex development loops, including file management, chat history persistence, project discovery, and metric tracking.
*   **Multi-Modal Support:** Includes utilities for handling audio input (via Whisper integration).

## Files in Domain
The framework exhibits a highly modular structure across several key directories: `api`, `ai`, `agents`, `knowledge`, `chat`, `engine`, `tools`, etc.

### Core Modules (`/codx-junior`)
*   `/home/codx-junior-projects/codx-junior/README.md`
*   `/home/codx-junior-projects/codx-junior/api/pyproject.toml`
*   `/home/codx-junior-projects/codx-junior/api/shared/codx-junior/scripts/docker-compose.yaml`
*   `/home/codx-junior-projects/codx-junior/api/shared/codx-junior/scripts/traefik/traefik.yaml`

### API Handlers & Main Logic (`api`)
The core entry points and public facing components.
*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/app.py` (Main application routing)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/global_settings.py`
*   Other API utility files: `db_router.py`, `file_finder.py`, `git.py`, `users.py`, `api/knowledge.py`, etc.

### Agents (`agents`)
Specialized agent classes defining capabilities.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` (Base class definition)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`

### AI Communication (`ai`)
Classes responsible for interfacing with various Large Language Models (LLMs).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py`
*   Specific LLM adapters: `openai_ai.py`, `ollama.py`, etc., plus disabled files (`anthropic.py.disabled`, `mistral_ai.py.disabled`).

### Knowledge Retrieval System (`knowledge`)
Manages the ingestion, storage, and retrieval of organizational knowledge.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/__init__.py`
*   Knowledge storage implementations: `knowledge_db.py`, `knowledge_milvus.py`.
*   Preprocessing and Chunking: `knowledge_code_splitter.py`, `knowledge_qa_splitter.py`, `knowledge_splitter.py`.
*   Loading & Indexing: `knowledge_loader.py`, `knowledge_training.py`.

### Engines (`engine`)
The core processing logic that orchestrates agent actions and resource lookups.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/__init__.py`
*   File handling: `file_engine.py`, `project_manager.py` (via `tools`)
*   System interactions: `git_engine.py`, `wiki_engine.py`.

### Chat & Context Management (`chat`, `context`)
Handling conversation state, history, and user interaction.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_engine.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py`

### Tools & Utilities (`tools`, `utils`)
Reusable functions and external integrations.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/code_writer.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/fetch_webpage.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py`

### Profile and Metadata (`profiles`, `metrics`)
Defines user roles, agent personas, and tracking data.
*   Profiles: `analyst.profile`, `software_developer.profile`, etc.
*   Monitoring: `metrics/codx_junior_metrics.py`, `metrics/chat_heatmap.py`

### Wiki Documentation (Static Site)
Contains the static files for the internal documentation wiki built with VitePress.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_template/*/*`

## Dependencies
The framework depends heavily on internal libraries and external services, including:

1.  **LLM Providers:** OpenAI, Mistral AI, and Ollama (internal abstractions to various LLMs).
2.  **Database/Vector Store:** Integration points for persistence (`knowledge_db.py`) and vector search (`knowledge_milvus.py`).
3.  **Collaboration APIs:** GitHub API integration (`api/codx/junior/api/github.py`, `security/github_oauth.py`).
4.  **Messaging Service:** Socket.IO setup for real-time communication (`sio/*` files).

## Used By
(No specific external modules were listed in `<used_by_files>`. The system functions as a comprehensive domain.)

## Entry Points
These files provide the primary, functional starting points for implementing or utilizing components of the framework.

*   `/home/codx-junior-projects/codx-junior/api/README.md` (Documentation entry point)
*   **Agents:**
    *   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
    *   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
    *   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
*   **Initialization:**
    *   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`