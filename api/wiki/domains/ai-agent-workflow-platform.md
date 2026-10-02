# AI Agent Workflow Platform
## Overview
The AI Agent Workflow Platform provides a comprehensive, modular system for building and managing intelligent, automated workflows powered by multiple Large Language Models (LLMs). It is designed as a sophisticated orchestration layer that moves beyond simple chat interfaces.

This platform serves as a unified hub where specialized agents can interact with diverse external tools—including file systems, version control repositories (Git), proprietary knowledge bases, and web resources. This integration allows the system to automate complex, multi-step tasks such as advanced coding assistance, deep domain research, iterative debugging, and structured task execution.

The architecture is highly customizable, supporting sophisticated Retrieval-Augmented Generation (RAG) pipelines, prompt engineering within various `knowledge` components, and defining specific agent capabilities through custom profile files and agents. Its goal is to transform raw LLM calls into robust, predictable, and executable workflows.

## Files in Domain
This domain contains a highly modular codebase organized by functional area: API endpoints, AI model integrations, Knowledge Retrieval Systems, Agents/Tools, Chat Management, and internal Utilities.

*(Note: Due to the large number of files, they are listed below grouped by their logical directory structure.)*

### Root & Configuration
*   `api/README.md` | `pyproject.toml`
*   `shared/codx-junior/scripts/docker-compose.yaml`: Container orchestration definition.
*   `shared/codx-junior/scripts/traefik/traefik.yaml`: Reverse proxy configuration.

### Core API Endpoints & Logic
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py`: Main application entry point.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/*/*.py`: Various API modules (e.g., `users.py`, `wiki.py`, `github.py`).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/main.py`: Core execution entry point.

### Agent Definitions & Logic
This module houses specialized agents designed to perform specific professional tasks.
*   `agents/base_agent.py`: Base class for all custom agents.
*   `agents/devops_agent.py`: Agent focused on DevOps tasks and infrastructure.
*   `agents/git_issues_agent.py`: Agent specializing in interacting with Git issues tracking.

### AI Model Integration (`ai/`)
This area manages connections to various LLM providers, ensuring the platform is model-agnostic.
*   `llmfactory.py`: Central utility for connecting to different models.
*   `openai_ai.py`: Implementation for OpenAI API calls.
*   `ollama.py`: Implementation for local Ollama LLMs.
*   *(Disabled/Internal Modules: `anthropic.py`, `mistral_ai.py`)*

### Knowledge Retrieval System (`knowledge/`)
This is the core RAG framework, defining how documents and knowledge are ingested, processed, and retrieved.
*   `knowledge_loader.py`: Handles loading data sources.
*   `knowledge_splitter.py`: Manages document splitting strategies (e.g., `code_splitter`, `qa_splitter`).
*   `knowledge_milvus.py`: Integration layer for vector databases like Milvus.
*   Supporting scripts: `knowledge_training.py`, `knowledge_wiki.py`, etc.

### Agents & Tools (`tools/`)
This directory contains callable functions and APIs that agents can use to interact with the external world.
*   `code_writer.py`: Tool for writing or verifying code snippets.
*   `fetch_webpage.py`: Tool for general internet fetching.
*   `project_tools.py`: Tools specific to project management tasks.

### Chat & Interaction (`chat/`)
Handling the conversational flow, context tracking, and knowledge integration during chat sessions.
*   `chat_engine.py`: The primary logic component that drives multi-turn conversations.
*   `chat_knowledge.py`: Logic tying knowledge retrieval into chat responses.

### Profiling, Metrics, & Utilities
*   `profiles/profile_manager.py`: Manages the loading and switching of agent personas.
*   `context.py`, `globals.py`: State management and global variable holders.
*   `utils/*/*.py`: General purpose utility functions (e.g., `chat_utils.py`, `utils.py`).

### Wiki Documentation Site (`wiki/`)
Dedicated files for the documentation portal, including templates and configurations that make the platform itself documented.

## Dependencies
No explicit external dependencies on other internal modules have been listed in the metadata block. However, functional dependencies include:
*   **LLM APIs:** OpenAI, Ollama, Anthropic (via configuration).
*   **Vector Stores:** Milvus or comparable knowledge base service.
*   **Version Control:** Git capabilities are integral to the `git_issues_agent`.

## Used By
No usage records have been explicitly defined in the metadata block.

## Entry Points
The following files are recommended starting points for developers looking to initialize or define core functionalities within the platform:

*   `/home/codx-junior-projects/codx-junior/api/README.md`: General documentation entry point.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Used to create custom agent logic inheritance.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Example of an operational agent suite.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Operational example demonstrating Git interaction.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Initialization point for the AI service module.