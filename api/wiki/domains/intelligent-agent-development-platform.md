# Intelligent Agent Development Platform

## Overview

The Intelligent Agent Development Platform is a comprehensive backend framework designed for developing advanced AI agents, sophisticated conversational experiences, and complex automation workflows. Its core purpose is to provide structured tools and abstractions necessary to build scalable, context-aware, and multi-functional AI applications.

**Key Features and Capabilities:**

*   **Multi-LLM Integration:** The platform offers flexible integration with leading LLM providers, including OpenAI (GPT), Mistral, and local deployments via Ollama. This allows developers to select the best model for specific tasks or implement failover strategies.
*   **Knowledge Retrieval Augmented Generation (RAG):** It incorporates advanced mechanisms for grounding AI responses in proprietary information. Knowledge management is handled through Milvus, enabling highly accurate retrieval of context from custom databases and documentation.
*   **Agent Orchestration:** The system supports specialized task-based agents (e.g., `DevOpsAgent`, `GitIssuesAgent`), which can be orchestrated to perform multi-step tasks by interacting with external services.
*   **Tool Calling/External Interactions:** Agents are equipped to interact seamlessly with vital corporate systems and APIs, including GitHub, wikis, file systems, and user management databases.
*   **Structured Architecture:** The design includes dedicated modules for profile management (defining agent personas), session handling (`sio` module), event management, and detailed metrics tracking.

This platform serves as the operational backbone for large-scale AI applications, moving beyond simple chat interfaces to complex, autonomous digital workers.

## Files in Domain

The project structure is highly granular, organizing components into logical domains such as `api`, `ai`, `knowledge`, `chat`, `agents`, and `utils`.

### API & Core Logic
*   `/home/codx-junior-projects/codx-junior/README.md` (API documentation)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py`: Main application entry point.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/main.py`: Primary execution script for the application.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/utils.py`: General utility functions.

### AI Providers & Utilities (`ai`/)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Package initialization.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py`: Factory for initializing and managing different LLM connections.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py`: Interface for OpenAI models.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py`: Interface for local Ollama deployments.
*   *(Other disabled AI files: `anthropic.py`, `mistral_ai.py`)*

### Agents & Profiles (`agents`/`profiles`)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Abstract base class for all custom agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Agent specialized in DevOps tasks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Agent specialized in handling GitHub issues.
*   *Numerous profile files defining agent personas:* (`analyst.profile`, `software_developer.profile`, etc.)

### Knowledge & RAG System (`knowledge`/)
This directory is crucial for the platform's memory and context extension abilities.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py`: Handles loading source data (PDFs, text).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py`: Manages chunking strategies for LLM context windows.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py`: Integration layer with the Milvus vector database.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_wiki.py`: Specific handling for Wiki content ingestion (Source: `wiki` module).

### APIs & External Interactions (`api`/)
These files manage communication with internal and external systems.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py`: Integration layer for GitHub API access.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/users.py`: User profile and management APIs.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py`: Interface for managing wiki content.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/file_finder.py`: Mechanism to find and locate files within a codebase or repo.

### Chat, Session, & Engineering (`chat`, `engine`, `sio`)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_manager.py`: Oversees the lifecycle of conversations.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/file_engine.py`: Module responsible for file system interactions and processing.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/sio.py`: Implementation of SocketIO for real-time communication.

### Security & Infrastructure (DevOps)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/security/github_oauth.py`: Handles GitHub OAuth flows.
*   `/home/codx-junior-projects/codx-junior/api/shared/codx-junior/scripts/docker-compose.yaml`: Defines the overall service containerization blueprint.

## Dependencies

*(No specific file dependencies are listed in the input metadata.)*

## Used By

*(No specific files utilizing this domain are listed in the input metadata, suggesting that all internal components rely on direct imports rather than explicit usage tracking being configured.)*

## Entry Points

The following files serve as primary entry points for interaction with or loading of the Agent Development Platform modules:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`