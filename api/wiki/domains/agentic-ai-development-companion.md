# Agentic AI Development Companion

## Overview

The Agentic AI Development Companion is an advanced, comprehensive framework designed to automate and accelerate the software development lifecycle through sophisticated multi-agent orchestration. It moves beyond simple conversational chatbots by constructing a highly integrated platform where specialized agents can collaborate on complex tasks such as debugging, feature implementation, project analysis, and API interaction.

**Core Functionality:**
The system's defining strength is its ability to ground all LLM responses in real-time project context. This is achieved through an advanced Knowledge Retrieval Augmentation (RAG) pipeline that ingests codebases, documentation (Wiki), GitHub issues, local file structures, and historical chat data.

**Architectural Components:**
1.  **Multi-Agent System:** Specialized agents (e.g., `DevOpsAgent`, `GitIssuesAgent`) utilize a common base agent structure to execute complex workflows autonomously.
2.  **Knowledge Backbone:** A robust knowledge graph/database component (`knowledge_db.py`, `milvus`) handles code chunking, document embedding, and semantic similarity search across vast amounts of project data.
3.  **Tool Utilization:** Agents are equipped with defined tools/APIs—such as calling external web pages, running Git commands, or writing code segments—enabling demonstrable action rather than just suggestion.
4.  **Context Management:** Detailed context modules ensure that conversational state is maintained across interactions, project stages, and knowledge retrieval cycles.

This companion serves as a central intelligence layer for developers, enabling deep project introspection and actionable development assistance.

## Files in Domain

Given the sheer volume of files, they have been categorized by functional area:

### 🛠️ Agents and Core Logic
*   **`agents/base_agent.py`**: The structural foundation for all specialized agents.
*   **`devops_agent.py`**: Specialized agent likely handling deployment, CI/CD tasks, and system-level management.
*   **`git_issues_agent.py`**: Agent dedicated to interacting with version control systems (Git) and issue trackers (GitHub).
*   **`context.py`, `globals.py`**: Core modules managing the state and environment for running agents.
*   **`app.py`, `main.py`**: Main entry points and application initialization logic.

### 🧠 Knowledge Retrieval (RAG) System
This suite powers the system's ability to "know" the project it is working on.
*   **`knowledge/knowledge_loader.py`**: Handles initial ingestion and loading of diverse data sources (code, doc, wiki).
*   **`knowledge/knowledge_splitter.*`**: Modules responsible for breaking down large documents (splitting code, QA splitting, general chunking) before embedding.
*   **`knowledge/knowledge_db.py`, `knowledge/knowledge_milvus.py`**: Implementations for interacting with the knowledge vector database and managing embeddings.
*   **`api/knowledge.py`, `chat/chat_knowledge.py`**: Public-facing APIs for utilizing the retrieved knowledge during chat interactions.

### ⚙️ Services, Utilities, and Tools
*   **`tools/*`**: Contains modular function libraries that agents can execute (e.g., `code_writer.py`, `project_tools.py`).
*   **`api/github.py`**: Dedicated module for interfacing with GitHub APIs (issues, commits).
*   **`api/file_finder.py`, `api/wiki.py`**: Tools for searching and retrieving information from the underlying file system and Wiki structure.
*   **`chat_manager.py`, `chat_engine.py`**: Core modules managing chat state, history, and orchestrating responses between agents and LLMs.

### 👤 Profiles and Personalization
The framework supports various user profiles to tailor agent behavior:
*   **`profiles/*.profile`**: Defines roles (e.g., Software Developer, Analyst, Browser) that dictate the agent's persona, priorities, and available tools.
*   **`ProfileManager`**: Manages switching and loading these tailored behaviors.

### 📊 Monitoring and Infrastructure
*   **`metrics/*`, `log_parser.py`**: Components for tracking usage, performance, and analyzing chat interactions (Heatmaps, Wall Charts).
*   **`security/user_management.py`, `github_oauth.py`**: Handling authentication and access control.
*   **`sio/`**: Modules related to real-time communication and session management (Simple Internet Objects).

### 📜 Auxiliary & Readme
*   A large set of Markdown files (`README.md`) provides documentation for various modules, APIs, and overall usage guidelines.

## Dependencies

The framework relies on several critical external systems and libraries to function effectively:

1.  **Large Language Models (LLMs):** OpenAI, Anthropic, Mistral, etc. (via modular SDK wrappers).
2.  **Vector Database:** Specialized integration with specialized vector stores like Milvus or Pinecone for advanced RAG operations.
3.  **Version Control System:** Git must be available and accessible via authenticated APIs/tools.
4.  **Web Integration:** Libraries to perform web scraping (e.g., requests, BeautifulSoup) for `fetch_webpage` functionality.
5.  **Database Backend:** A persistent database backend (implied by `db.py`) for storing history, user settings, and conversation state.

## Used By

This highly functional domain is intended to be core infrastructure for a larger operational application or platform layer. It acts as the intelligence back-end providing capabilities used by:

*   **Frontend UI/Platform:** Any client viewing chat interfaces or dashboards that requires smart suggestions or actionable tasks.
*   **Internal DevOps Tools:** Automation pipelines needing code analysis, threat detection queries, or dependency checks.
*   **Project Management Tools:** Systems seeking AI-driven summarization of Jira/GitHub tickets and relating them to codebase changes.

## Entry Points

These files represent the primary modules designed for initializing and executing agent workflows:

*   `/home/codx-junior-projects/codx-junior/api/README.md` (General API documentation entry)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: The foundational class used to create all custom agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Initialized for system and deployment tasks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Initialized for tracking code changes and issues.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Main container for the AI provider integration logic.