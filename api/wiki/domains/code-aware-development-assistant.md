# Code-Aware Development Assistant

## Overview
This domain integrates powerful LLMs with structured codebases, documentation, and project history to build a comprehensive intelligence layer. It enables sophisticated conversational agents for developer support, handling tasks such as coding assistance, Git operations, and knowledge retrieval from internal sources. Essentially, it acts as an intelligent copilot infrastructure that leverages all facets of the development process (code, wiki, tickets, global context) to provide context-aware help.

## Files in Domain
The domain structure is highly modular, covering core agent logic, AI integrations, operational APIs (Git, Wiki, Users), knowledge management components, and chat/communication services.

### Core Application & Architecture
*   `api/codx/junior/app.py`: Main entry point for the application.
*   `api/codx/junior/main.py`: Primary execution script.
*   `api/codx/junior/README.md`: Top-level documentation.
*   `api/codx/junior/settings.py`: Global configuration settings loading.
*   `api/codx/junior/global_settings.py`: Project/context-specific general settings.

### Agents and Logic Layers
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base class for all specialized agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Agent specialized in DevOps tasks (e.g., deployment, infrastructure).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Agent focused on interacting with Git and issue tracking platforms.

### AI/Language Model Integration (`/ai`)
*   `api/codx/junior/ai/llmfactory.py`: Factory for managing and instantiating various LLM clients.
*   `api/codx/junior/ai/openai_ai.py`: Client implementation for OpenAI models.
*   `api/codx/junior/ai/ollama.py`: Client implementation for Ollama local deployments.
*   `api/codx/junior/ai/utils.py`: Utility functions specific to AI interactions.
*   `api/codx/junior/ai/anthropic.py.disabled`: Disabled client for Anthropic models.
*   `api/codx/junior/ai/mistral_ai.py.disabled`: Disabled client for Mistral models.

### Knowledge Management and Retrieval (`/knowledge`)
This area is responsible for ingesting, splitting, storing, and retrieving context from various sources (code, documents, wikis).
*   `api/codx/junior/knowledge/loader.py`: Handles loading raw data into the knowledge system.
*   `api/codx/junior/knowledge/knowledge_splitter.py`: Core class for document chunking and splitting strategies.
*   `api/codx/junior/knowledge/knowledge_code_to_dcouments.py`: Converts code files into storable documentation format.
*   `api/codx/junior/knowledge/knowledge_milvus.py`: Implementation of the Milvus Vector Database connection and search logic.
*   `api/codx/junior/knowledge/knowledge_db.py`: Abstraction layer for database interactions (e.g., metadata storage).
*   **Pre-Prompts:** Contains specialized prompts for enrichment, tagging, and splitting:
    *   `prepromts/code_to_chunks.md`
    *   `prepromts/enrich_document.md`
    *   `prepromts/extract_document_tags.md`
    *   `prepromts/extract_query_tags.md`

### APIs and Integrations (`/api`)
These files act as service wrappers for external systems or project metadata.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py`: Integration layer for GitHub interactions (actions, issues).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py`: API wrapper for the internal wiki system.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/users.py`: Management of user profiles and authentication data.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/file_finder.py`: Tool for locating files within the codebase based on criteria.

### Chat and Conversation (`/chat`)
*   `api/codx/junior/chat/chat_manager.py`: Manages conversation state, history, and session context.
*   `api/codx/junior/chat/chat_engine.py`: The core engine that orchestrates response generation using agents and knowledge retrievers.
*   `api/codx/junior/chat/chat_knowledge.py`: Specific module for running RAG-based chat queries.

### Context, State, and Utilities (`context`, `utils`)
*   `api/codx/junior/context.py`: Manages the current context window (user input, session history, project files).
*   `api/codx/junior/db.py`: Database connection and CRUD operations utility.
*   `api/codx/junior/tools/*`: Collection of actionable tools callable by agents. Examples include:
    *   `code_writer.py`: Tool for generating, modifying, or reviewing code snippets.
    *   `fetch_webpage.py`: Tool to perform web searches and extract content.
    *   `project_tools.py`: Generic project-level utility functions.

### Project Structure & Workspaces
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/*`: Components related to the wiki feature, including specialized managers and templates.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/project/*`: Modules dedicated to project discovery and management (`project_manager.py`, `project_discover.py`).
*   `api/codx/junior/workspace/workspace_manager.py`: Manages the definition and scope of the current working context or project.

## Dependencies
This domain heavily relies on several types of dependencies:

1.  **Large Language Models (LLMs):** Integration with external AI services (OpenAI, Anthropic) and local models (Ollama).
2.  **Vector Databases:** Requires a vector store system (e.g., Milvus is explicitly used) for efficient knowledge retrieval (RAG).
3.  **Communication/Messaging:** Depends on SocketIO (sio) for real-time chat updates, and internal event management (`event_manager.py`).
4.  **Code Management:** Deep integration with Git protocols (GitHub API access via `github.py`) to understand project history and issue context.
5.  **Database:** Requires a persistence layer (`db.py`) for storing state, conversation history, and indexed metadata.

## Used By
*   **Frontend/User Interface:** Any frontend component requiring natural language interaction or code generation relies on the core chat loop exposed by `api/codx/junior/app.py` or `main.py`.
*   **Internal Developer Tools:** Automated build pipelines that interact with ticketing systems (JIRA, GitHub Issues) and need specialized action handling often call agents like `devops_agent.py` or `git_issues_agent.py`.

## Entry Points
The following files serve as primary public entry points for interacting with the domain's core functionality:

*   `/home/codx-junior-projects/codx-junior/api/README.md`: Overall project documentation access.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: The foundational class for developing all specialized agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Starting point for system administration and deployment workflows.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Starting point for deep Git interaction and issue tracking resolution via LLMs.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Initialization module to configure and select AI backends.