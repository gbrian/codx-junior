# AI Developer Co-Pilot System

## Overview
The AI Developer Co-Pilot System is an advanced platform designed to serve as a comprehensive co-pilot for software development workflows. This domain acts as an intelligent layer, enabling specialized AI agents to interact with complex institutional knowledge and operational tools. It aggregates various functionalities—such as code generation, project analysis, Git interaction, web scraping (via `fetch_webpage` tool), and expert chat assistance—into a unified system. All agent responses are grounded in retrieved organizational context, maximizing accuracy and utility within development teams.

The core components include:
*   **Knowledge Management:** Secure ingestion, splitting, and retrieval of proprietary code bases and documents using advanced vector database techniques (Milvus).
*   **Agentic Workflow:** Specialized agents (`DevOpsAgent`, `GitIssuesAgent`) handle complex, high-level tasks beyond simple chat completion.
*   **Architecture:** A modular API structure allowing integration with multiple Large Language Models (LLMs) like OpenAI, Mistral, and local LLM implementations (Ollama).

---

## Files in Domain

The domain encompasses a highly modular codebase spread across agents, knowledge processing, utility APIs, and chat components.

### Core Application & Agents
*   `codx-junior/api/app.py`: Main application entry point.
*   `codx-junior/api/README.md`: Project documentation.
*   `codx-junior/api/codx/junior/api/global_settings.py`: Central configuration settings.
*   `codx-junior/api/codx/junior/main.py`: Primary execution logic.
*   **Agents:**
    *   `codx-junior/api/codx/junior/agents/base_agent.py`: Base class for custom agents.
    *   `codx-junior/api/codx/junior/agents/devops_agent.py`: Agent specialized in DevOps tasks.
    *   `codx-junior/api/codx/junior/agents/git_issues_agent.py`: Agent focused on Git and issue tracking.

### AI & Model Integration (`codx/junior/ai`)
*   `codx-junior/api/codx/junior/ai/**`: Handles various LLM interfaces (OpenAI, Mistral, Ollama) and utilities.
    *   `openai_ai.py`: Integration module for OpenAI APIs.
    *   `ollama.py`: Interface for running local models via Ollama.
    *   `llmfactory.py`: Abstract layer or factory pattern for managing LLM accessors.
    *   `ai_logger.py`: Dedicated logging utilities for AI interactions.

### Knowledge Retrieval & RAG (`codx/junior/knowledge`)
This section manages the ingestion and utilization of proprietary data, including code and documentation.
*   `knowledge_loader.py`: Handles initial loading of documents.
*   `knowledge_splitter.py`: Manages strategies for splitting large texts into manageable chunks.
*   `knowledge_db.py`: Abstraction layer for database interaction (likely vector store).
*   `knowledge_milvus.py`: Specific implementation using Milvus vector database.
*   `knowledge_qa_splitter.py`/`knowledge_code_splitter.py`: Specialized splitters for Q&A and code artifacts.
*   `knowledge_wiki.py`: Functions related to structuring wiki content knowledge.

### APIs & Tooling (`codx/junior/api`)
*   `codx-junior/api/codx/junior/api/**`: Contains various API wrappers:
    *   `github.py`/`misc/github.py`: Integrations with GitHub services.
    *   `wiki.py`/`README.md`: APIs dedicated to wiki content management (and its templating directory).
    *   `file_finder.py`: Tool for locating and managing files within the project structure.
    *   `users.py`: API layer for user data interactions.
    *   `db_router.py`: Directory router for database operations.

### Chat & Context Management (`codx/junior/chat`, `codx/junior/context`)
*   `chat_manager.py`/`chat_engine.py`: Core logic for managing conversation states and chat responses.
*   `context.py`: Manages the context window provided to the active LLM call.

### Tools & Utilities (`codx/junior/tools`, `codx/junior/utils`)
*   `tools/__init__.py`: Tool definitions container.
*   `code_writer.py`: Specialized tool for generating or modifying code segments.
*   `fetch_webpage.py`: Tool utilized for external web content retrieval (scraping).
*   `project_tools.py`: Tools related to the overall project structure and metadata.

### Profiles & System Logic
*   **Profiles:** Directory containing profile definitions (`coding_profiles.json`, `software_developer.profile`, etc.) used to define agent personas and capabilities.
*   **Project Management:** Scripts for discovering, managing, and working with coding projects (`project_discover.py`, `project_manager.py`).

---

## Dependencies
No explicit file dependencies were listed in the configuration metadata. However, functionally, this domain depends heavily on:
1.  LLM API Clients (OpenAI, Mistral, etc.).
2.  Vector Database clients (Milvus).
3.  Version Control System protocols (Git/GitHub APIs).

---

## Used By
No dependent files were listed in the configuration metadata.

---

## Entry Points
*   `/home/codx-junior-projects/codx-junior/api/README.md` (Documentation entry)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`