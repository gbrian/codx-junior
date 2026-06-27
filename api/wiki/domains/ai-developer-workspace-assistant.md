# AI Developer Workspace Assistant

## Overview
This domain provides a comprehensive API and execution environment designed for advanced AI agents to interact with complex coding tasks within a simulated developer workspace. It serves as a sophisticated orchestration layer, unifying various capabilities needed for end-to-end software development cycles.

The core functionality integrates several specialized modules to support intelligent agent workflows, including:

*   **Knowledge Retrieval (RAG):** Implementing advanced indexing and retrieval of project knowledge from diverse sources (documents, code, wikis).
*   **Project Management & Tracking:** Tools for task management, issue tracking (Git/GitHub), and understanding the overall structure of a codebase.
*   **Code Generation & Modification:** Utilizing dedicated agents and tools for writing, modifying, and reviewing code.
*   **Communication & Context:** Managing complex conversational state, history, logging, and context embedding.
*   **DevOps Integration:** Handling background tasks, file system monitoring, and deployment pipelines.

By providing structured APIs for chat interaction, Git operations, internal database lookups (`db.py`), and external services (like OpenAI/Mistral), this domain allows AI agents to act as full-stack developers within the specified project environment.

## Files in Domain
This module contains a vast array of files organized into logical subdirectories covering API definitions, agent implementations, knowledge retrieval mechanisms, core utilities, tools, and testing suites.

### Core Agents & Components (Agents/API)
*   `/api/README.md`
*   `/api/codx/junior/agents/base_agent.py`: Base class for custom AI agents.
*   `/api/codx/junior/agents/devops_agent.py`: Agent dedicated to managing development operations.
*   `/api/codx/junior/agents/git_issues_agent.py`: Agent specialized in interacting with Git and issue tracking.

### AI Integration & Model Handling (ai/)
*   `/api/codx/junior/ai/__init__.py`
*   `/api/codx/junior/ai/ai.py`: Primary interface for AI interactions.
*   `/api/codx/junior/ai/ai_logger.py`: Logging utilities specific to the AI module.
*   `/api/codx/junior/ai/llmfactory.py`: Factory pattern for managing different LLM connections.
*   `/api/codx/junior/ai/ollama.py`: Implementation for using local Ollama models.
*   `/api/codx/junior/ai/openai_ai.py`: Implementation utilizing the OpenAI API.
*   `/api/codx/junior/ai/utils.py`: Utility functions for AI data processing.

### Application Logic & Infrastructure (Root Level)
*   `auth/git_oauth.py`: Handles GitHub OAuth authentication flows.
*   `settings.py`: Configuration management for the entire application.
*   `codx/junior/api/chatGPTLikeApi.py`: API implementation mimicking popular chat services.
*   `/codx/junior/api/codx/junior/db_router.py`: Router for database interactions.
*   `/api/codx/junior/api/file_finder.py`: Utility to locate files within the project structure.
*   `/api/codx/junior/api/github.py`, `/api/codx/junior/api/global_settings.py`, etc.: Various specialized API wrappers (Users, Wiki, Global Settings).

### Knowledge & RAG System (knowledge/)
This complex subsystem manages the ingestion, splitting, and retrieval of project knowledge.
*   `README.md`: Documentation for the knowledge system.
*   `__init__.py`: Module initializer.
*   `knowledge_loader.py`, `knowledge_code_to_dcouments.py`, etc.: Specialized loaders/parsers.
*   `knowledge_db.py`: Core module for database interaction in RAG flows.
*   `knowledge_milvus.py`: Implementation for using Milvus as a vector store.
*   `/knowledge/settings.py`: Knowledge system specific configuration.

### State Management & Project Context (models/, context/)
*   `/codx/junior/context.py`: Manages the current conversational and project context state.
*   `/api/codx/junior/db.py`: Primary database interface layer.
*   `/codx/junior/sio/*`: Modules related to Socket.IO for real-time event handling.

### Tooling & Execution (tools/)
This directory houses the executable functions available to agents.
*   `__init__.py`: Module initializer.
*   `code_writer.py`: Tools specifically for generating and executing code snippets.
*   `fetch_webpage.py`: Tool for retrieving external web content.
*   `project_tools.py`: Broad tools for interacting with the project ecosystem.

### Workflow & Lifecycle (changes/, chat/, engine/)
These modules manage structured processes like development cycles, chats, and execution logic.
*   `/codx/junior/chat/*`: Modules managing conversation flow (`chat_manager.py`, `chat_engine.py`).
*   `/codx/junior/engine/*.py`: Various specialized engines for executing features (e.g., `git_engine.py`, `knowledge_engine.py`).
*   `/codx/junior/changes/*`: Logic handling file changes and version control monitoring (`change_manager.py`).

### Profiling, Documentation & Misc.
*   `prompts/__init__.py`: Directory for centralized prompt templates.
*   `profiles/*`: Files defining agent and user capabilities (e.g., `software_developer.profile`, `analyst.profile`).
*   `wikipedia/wiki_manager.py`: Dedicated module to interact with Wikipedia data (if required by the domain).

### Testing
A robust set of tests exists covering all critical components:
*   `tests/*`: Includes test suites for chat, change management, mention managers, and database interactions.

## Dependencies
No explicit dependencies were defined in the metadata. However, due to its scope, this module implicitly depends on fundamental infrastructure services like a database (via `db.py`), an LLM provider (OpenAI/Mistral via `ai/*.py`), and filesystem access for project management.

## Used By
No files consuming this domain were specified in the metadata. This suggests that components utilizing this domain are either outside of this repository's scope or have not yet been mapped.

## Entry Points
These files represent primary entry points, allowing other applications or scripts to bootstrap interaction with core agent functionality and API services:

*   `/api/README.md`: Documentation entry point.
*   `/api/codx/junior/agents/base_agent.py`: Core inheritance model for creating new agents.
*   `/api/codx/junior/agents/devops_agent.py`: Primary agent service for operational tasks.
*   `/api/codx/junior/agents/git_issues_agent.py`: Primary agent service for source control and issue management.
*   `/api/codx/junior/ai/__init__.py`: Entry point for handling all AI model connections and utilities.