# AI Agent Development Platform

## Overview

The AI Agent Development Platform is a comprehensive, modular framework designed for building, testing, and orchestrating specialized Artificial Intelligence agents. It serves as a sophisticated environment for integrating advanced Large Language Models (LLMs) and multiple organizational knowledge sources into cohesive automated workflows.

At its core, the platform enables developers to create dedicated "agents" that can perform complex tasks ranging from automating coding routines and managing project lifecycles to executing nuanced conversational interactions.

**Key Features:**

*   **Multi-LLM Compatibility:** Supports integration with leading LLMs, including OpenAI, Anthropic, Ollama, and other custom backends via a unified AI factory system (`llmfactory`).
*   **Deep Context Retrieval (RAG):** Provides robust context retrieval by integrating diverse source types. Knowledge sources include:
    *   Local File Systems
    *   Git Repositories and issue tracking
    *   Wikis (structured documentation)
    *   Custom knowledge bases (Milvus integration suggested for advanced vector storage).
*   **Modular Agent Architecture:** Features specialized agents (`devops_agent`, `git_issues_agent`) built upon a robust base agent structure, allowing fine-grained control and extension.
*   **Development Capabilities:** Supports automated coding tasks, project discovery, file management, and change tracking within development environments.
*   **Conversational IQ:** Manages stateful interactions through sophisticated chat engines (`chat_manager`, `chat_engine`), supporting knowledge injection and session persistence.

## Files in Domain

The platform structure is highly organized across various modules for AI integration, agent logic, data management, and domain tools.

### Core API & Application Logic
*   `/home/codx-junior-projects/codx-junior/api/README.md` (Root Documentation)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py`: Main application entry point.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/main.py`: Primary execution logic.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/settings.py`: Global configuration management.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/globals.py`: Global utility settings.

### Agent Implementations (Agents)
Defines specialized agent behaviors:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base class for all custom agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Agent focused on DevOps tasks and infrastructure management.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Agent specialized in interacting with Git issues and repositories.

### AI Integration Layer (ai/)
Manages interaction with various LLM providers:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py`: Factory for selecting and initializing LLM clients.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py`: OpenAI API wrapper.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py`: Ollama local model integration.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/anthropic.py.disabled` (Disabled integration file for Anthropic).

### Knowledge Base and Retrieval System (knowledge/)
Handles context ingestion, splitting, and retrieval:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/__init__.py`: Knowledge module initialization.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py`: Handles ingesting documents from various sources.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py`: Splits large documents into optimal chunks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_db.py`: Interface for database interactions (e.g., similarity search).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py`: Specific integration with Milvus vector store.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_wiki.py`: Logic for parsing and utilizing wiki content.

### Tools & Utilities (tools/, utils/)
Implements callable functions and utility classes:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/code_writer.py`: Tool for writing, refactoring, or reviewing code blocks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/fetch_webpage.py`: Tool for retrieving external web content.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py`, `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/utils.py`: Common utility functions for chat and general use.

### Specialized Modules
*   **Chat/Interaction:** Handles conversational flow, memory, and context injection (`chat_engine.py`, `chat_manager.py`, `context.py`).
*   **Project Management:** Tools for discovering and managing code projects (`project_discover.py`, `project_manager.py`).
*   **Wiki:** Dedicated module for documentation management (including templates and managers).

## Dependencies

The current domain structure does not list explicit inter-module dependencies in a `<depends_on_files>` tag, suggesting that dependencies are managed either by runtime environment setup or standard Python imports across the codebase.

Common architectural dependencies include:
*   `python-dotenv` or similar mechanism for API key handling (OpenAI, Anthropic).
*   Vector databases clients (e.g., Milvus library).
*   Async framework libraries supporting concurrent operations (e.g., `asyncio`).

## Used By

The current domain structure does not specify files that explicitly use this entire module as a dependency in a `<used_by_files>` tag. The platform is designed to be foundational, with almost every specialized application or test file within the repository potentially using components from its various submodules (e.g., `utils/` or `knowledge/`).

## Entry Points

These files serve as primary starting points for initializing and executing core functionalities of the AI Agent Platform:
*   `/home/codx-junior-projects/codx-junior/api/README.md`: Main entry point documentation.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Used to initialize custom agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Entry for DevOps automation tasks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Entry for Git workflow interactions.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Initializer and entry point for AI service wrappers.