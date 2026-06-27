# Autonomous Knowledge Agents

## Overview
This module provides a sophisticated, integrated framework for managing and deploying autonomous AI agents. Designed to tackle complex developmental tasks and deep knowledge research, it allows agents to interact intelligently across multiple heterogeneous sources: large corporate codebase repositories, structured GitHub issue trackers, proprietary wiki systems, and external web pages.

The architecture combines advanced Large Language Model (LLM) management techniques—specifically Retrieval-Augmented Generation (RAG)—with specialized tools and orchestration layers. This capability transforms the system into an intelligent collaborative partner, capable of receiving a high-level goal and executing multi-step plans involving coding, documentation search, project analysis, and issue tracking across diverse corporate knowledge silos.

**Key Features:**
*   **Multi-Source Retrieval (RAG):** Integrates knowledge from code, wikis, markdown documents, and databases (Milvus).
*   **Agent Specialization:** Supports various specialized agents (e.g., `devops_agent`, `git_issues_agent`).
*   **Orchestration & State Management:** Manages complex multi-step workflows across different system interfaces.
*   **Scalable LLM Support:** Designed to support multiple AI backends (OpenAI, Mistral, Ollama).

## Files in Domain
The module organizes its functionality into several key areas: Agents, AI Models/Utilities, APIs, Knowledge Management, and Specialized Workflows.

### Core Logic & Architecture (`codx_junior`)
*   `api/README.md`: Module documentation.
*   `app.py`: Main application entry point (suggested).
*   `main.py`: Primary execution file for the module.
*   `engine.py`: Central engine responsible for orchestrating tasks and workflows.
*   `context.py`, `globals.py`, `settings.py`: Configuration, state management, and overall environmental context handling.

### Agents & Specialized Tools
These files define specialized AI agents that interact with specific systems:
*   `agents/base_agent.py`: Abstract base class for all agents.
*   `agents/devops_agent.py`: Agent focused on DevOps tasks (e.g., deployment, system setup).
*   `agents/git_issues_agent.py`: Agent specialized in interacting with Git and issue trackers.
*   `tools/code_writer.py`: Utility for code generation and writing tasks.
*   `tools/fetch_webpage.py`: Tooling for extracting information from external URLs.

### AI Backend & Utilities (`ai`)
This directory handles the interaction with various LLM providers:
*   `llmfactory.py`: A factory pattern for initializing different LLM clients.
*   `openai_ai.py`, `ollama.py`: Specific implementations for major AI backends (OpenAI, Ollama).
*   `utils.py`, `anthropic.py.*`, etc.: General utility and specific provider wrappers.
*   `chat_engine.py`, `chat_manager.py`: Components dedicated to managing conversational state and interaction flows.

### Knowledge Management (`knowledge`)
The core system for ingesting, storing, and retrieving corporate knowledge:
*   `knowledge_loader.py`: Handles loading data from various sources (files, databases).
*   `knowledge_splitter.py`, `knowledge_qa_splitter.py`: Tools for chunking raw documents into LLM-digestible chunks optimized for Q&A or context embedding.
*   `knowledge_db.py`, `knowledge_milvus.py`: Interactions with vector and document databases (e.g., Milvus).
*   `knowledge_wiki.py`: Specific logic for extracting knowledge from wiki platforms.
*   `knowledge_code_to_dcouments.py`, `knowledge_code_splitter.py`: Utilities dedicated to processing codebases into documents suitable for RAG.

### API Interfaces & Services
These files provide structured methods to connect with external systems:
*   `api/file_finder.py`: Service layer for searching file contents and structure within the codebase.
*   `api/wiki.py`, `api/github.py`: Dedicated services for interacting with Wiki and GitHub APIs.
*   `api/users.py`, `api/global_settings.py`: Management of user profiles and system settings.

### Profiles & Testing
*   `profiles/profile_manager.py`: Logic for managing agent or task context profiles (e.g., `analyst.profile`).
*   `tests/*/*.py`: Comprehensive suite of unit, integration, and end-to-end tests covering agents, DB interactions, and file watching.

## Dependencies
The domain relies heavily on several architectural components and external services:

*   **LLM APIs:** OpenAI, Mistral AI, Ollama (via wrappers in the `ai` directory).
*   **Vector Databases:** Milvus (`knowledge_milvus.py`) for advanced semantic search capabilities.
*   **Communication Protocols:** SessionIO/WebSockets (`sio/*`) for real-time communication and event handling.
*   **External Services:** GitHub API, Wiki APIs (e.g., Confluence, or custom implementations).
*   **Data Stores:** Standard databases (SQLite/SQLAlchemy likely used via `db.py`).

## Used By
*(No specific consuming files were listed in `<used_by_files>`, suggesting this module is a foundational library designed to be imported and integrated by a primary application layer, such as an external worker process or front-end chat interface.)*

## Entry Points
The primary entry points for utilizing the core functionality of this domain are:
*   `/home/codx-junior-projects/codx-junior/api/README.md`: Module documentation guide.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Starting point for defining specialized agent behaviors.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Example entry point for a DevOps-focused workflow.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Entry point for automated issue tracking and resolution workflows.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Package structure entry, guiding initialization of AI services (e.g., selecting the LLM provider).