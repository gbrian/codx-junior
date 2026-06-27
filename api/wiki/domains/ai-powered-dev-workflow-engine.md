# AI-Powered Dev Workflow Engine

## Overview

The AI-Powered Dev Workflow Engine is a sophisticated platform designed to revolutionize software development productivity by acting as an intelligent agent orchestrator. Its core function is bridging the gap between advanced Large Language Models (LLMs) and practical, domain-specific developer tools.

This engine goes beyond simple Q&A by indexing and synthesizing knowledge from diverse organizational sources, including internal documentation, live codebases, GitHub repositories, and dedicated wiki pages. This deep contextual understanding allows the system to execute complex, multi-step automated workflows—such as guided coding assistance, deep technical querying across the entire codebase (Repo Search), advanced issue tracking management, and holistic project lifecycle coordination—all within a coherent, intelligent chat interface.

The architecture is modular, containing specialized agents for different tasks (e.g., `DevOpsAgent`, `GitIssuesAgent`), robust knowledge retrieval components (`KnowledgeEngine`), and pluggable LLM integration layers (supporting OpenAI, Mistral AI, etc.). It aims to serve as the primary command center for development operations within an organization.

## Files in Domain

The structure of this domain is highly modular, organizing concerns into agents, knowledge management, API endpoints, and chat infrastructure.

**Configuration & Core Logic:**
*   `api/README.md`: Main entry point documentation.
*   `pyproject.toml`: Project dependency and configuration file.
*   `shared/codx-junior/scripts/docker-compose.yaml`: Deployment configuration for containerization.
*   `shared/codx-junior/scripts/traefik/traefik.yaml`: Service routing configuration.

**Agents & Specialized Workers:**
These files represent specialized AI agents capable of executing domain logic.
*   `api/codx/junior/agents/base_agent.py`: Base class for all custom agents.
*   `api/codx/junior/agents/devops_agent.py`: Agent focused on CI/CD, environment management, and DevOps tasks.
*   `api/codx/junior/agents/git_issues_agent.py`: Agent managing Git operations and issue lifecycle within repositories.

**AI Integration Layer:**
This directory manages the connection and abstraction of various LLM providers.
*   `api/codx/junior/ai/__init__.py`: Initializes the AI module.
*   `api/codx/junior/ai/anthropic.py.disabled`, `api/codx/junior/ai/mistral_ai.py.disabled`: Integration layers for specific LLM providers (currently disabled).
*   `api/codx/junior/ai/llmfactory.py`: Factory pattern for selecting and utilizing different LLMs.
*   `api/codx/junior/ai/openai_ai.py`: Integration layer for OpenAI models.
*   `api/codx/junior/api/chatGPTLikeApi.py`: API abstraction mimicking major chat model interfaces.

**API & Service Endpoints:**
These files handle high-level domain interactions and data access.
*   `api/codx/junior/api/global_settings.py`: Manages system-wide configuration variables.
*   `api/codx/junior/api/users.py`: Handles user profile and authentication details.
*   `api/codx/junior/api/wiki.py`: Dedicated API endpoint for Wiki content interaction.
*   `api/codx/junior/api/file_finder.py`, `api/codx/junior/api/github.py`, `api/codx/junior/api/users.py`, `api/codx/junior/api/wiki.py`: Dedicated internal APIs for structured data retrieval (File system, GitHub, etc.).
*   `api/codx/junior/api/db_router.py`: Routes database requests to appropriate storage mechanisms.

**Core Services & Managers:**
*   `api/codx/junior/app.py`, `api/codx/junior/main.py`: Main application startup and orchestrator files.
*   `api/codx/junior/context.py`: Manages the current context state of a conversation or task.
*   `api/codx/junior/engine.py`: Primary control loop executing complex workflows.
*   `api/codx/junior/task_manager.py`: Handles asynchronous and background job management.
*   `api/codx/junior/file_manager/__init__.py`, `pseudo-file_paths/*`: Tools related to file I/O and observation.

**Knowledge Retrieval System (`knowledge/`)**:
This module powers the context awareness of the engine, facilitating retrieval-augmented generation (RAG).
*   `api/codx/junior/knowledge/knowledge_loader.py`: Responsible for ingesting raw data from various sources.
*   `api/codx/junior/knowledge/knowledge_splitter.py`, `knowledge_code_splitter.py`, `knowledge_qa_splitter.py`: Handles the chunking and segmentation of large documents (Code, Text, Q\&A).
*   `api/codx/junior/knowledge/knowledge_db.py`, `knowledge_milvus.py`: Abstraction for interaction with Vector Databases (e.g., Milvus).
*   `api/codx/junior/knowledge/knowledge_loader.py`: Core knowledge retrieval utilities.
*   `api/codx/junior/knowledge/knowledge_wiki.py`, `pseudo-file_paths/*`: Specific tools for ingesting and querying Wiki data.

**Chat & Workflow Management:**
*   `api/codx/junior/chat_manager.py`: Manages the state and history of user conversations.
*   `api/codx/junior/chat/chat_engine.py`: The core engine that receives input, plans actions, and crafts responses.
*   `api/codx/junior/context.py`, `pseudo-file_paths/*`: Utilities for maintaining conversation context and history export.

**Profiles & Configuration:**
*   `api/codx/junior/profiles/profile_manager.py`: System managing different AI persona profiles (e.g., analyst, software developer).
*   `api/codx/junior/profiles/*.profile`, `*.profile.md`: Definition files defining agent roles and expected behavior.

**Tools & Utilities:**
*   `api/codx/junior/tools/*`: Collection of actionable tools the agents can call (e.g., `code_writer.py`, `fetch_webpage.py`).
*   `api/codx/junior/utils/*`: Generic helper functions for chat handling and utilities.

## Dependencies

This domain is heavily interconnected, requiring several core components to function:

1. **LLM Providers:** Relies on standardized interfaces (like OpenAI or Mistral) via `ai/llmfactory.py` to abstract model calls.
2. **Vector Databases:** Requires integration with specialized vector storage like Milvus (`knowledge_milvus.py`) for long-term contextual memory and fast semantic search.
3. **Data Sources:** Depends on external access methods for GitHub APIs, File System Watchers, and internal Wiki/Documentation systems.
4. **Database Persistence:** Uses a Database layer (`db.py`, `api/codx/junior/api/db_router.py`) to store conversation state, user data, and historical knowledge payloads.

## Used By

*(No files are listed as external dependents in the manifest. This domain appears to be a high-level module intended to be consumed by an overarching application or frontend service.)*

## Entry Points

The primary points of entry for this development workflow engine are:

*   `/home/codx-junior-projects/codx-junior/api/README.md`: General documentation and setup guide.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Used by developers building custom specialized agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Direct entry point for DevOps workflows.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Direct entry point for issue and repository management workflows.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Initializes the AI layer, making it available to all other modules.