# Intelligent Dev Agent Platform

## Overview

The Intelligent Dev Agent Platform is an advanced, AI-powered assistant designed specifically for professional software developers and engineering teams. This domain serves as a comprehensive operational layer that allows users to move beyond simple code suggestions by interacting directly with proprietary infrastructure data: living codebases, extensive project documentation (wikis), API specifications, and internal knowledge bases.

This platform's core functionality is built around specialized **agents**—modules capable of understanding complex development workflows. These agents retrieve, synthesize, and utilize information from multiple sources to automate tasks ranging from planning and design review to DevOps management, bug tracking integration (Git/Issues), and advanced Q&A based on internal knowledge retrieval.

In essence, the platform transforms unstructured data sources into actionable intelligence, providing a single interface for developers to manage the entire lifecycle of a technical project.

## Files in Domain

This domain encompasses a wide variety of modules and resources grouped by function:

**Core Infrastructure & API:**
*   `README.md` (API Root)
*   `app.py`: Main application entry point for the junior APIs.
*   `main.py`: Core execution or initialization script.
*   `settings.py`: Global configuration and environment settings.
*   `global_settings.py`: Domain-specific global configuration utility.
*   `db.py`: Database connection and interaction layer.

**Agent & Tooling Modules (The "Doing"):**
*   `/agents/base_agent.py`: Base class defining common agent functionality.
*   `/agents/devops_agent.py`: Agent specialized in CI/CD, deployment, and operations tasks.
*   `/agents/git_issues_agent.py`: Agent for interacting with Git version control and issue tracking systems.
*   `scripts/docker-compose.yaml`: Defines the container orchestration environment.
*   `scripts/traefik/traefik.yaml`: Traefik routing configuration file.

**AI & Model Handling:**
*   `ai/__init__.py`: Initialization for AI utilities.
*   `ai/utils.py`: General utility functions for AI interactions.
*   `ai/llmfactory.py`: Handles selection and management of various Large Language Models (LLMs).
*   `ai/openai_ai.py`: Implementation wrapper for OpenAI APIs.
*   `ai/ollama.py`: Integration module for running local models via Ollama.
*   `api/chatGPTLikeApi.py`: Specific API implementation simulating ChatGPT-like interactions.
*   `ai/anthropic.py.disabled`, `ai/mistral_ai.py.disabled`: Disabled wrappers for major LLM providers.

**Knowledge Management & Retrieval (RAG):**
*   `/knowledge/__init__.py`: Initialization for knowledge modules.
*   `knowledge_loader.py`: Handles ingesting and loading proprietary data sources.
*   `knowledge_splitter.py`: Utilities for chunking code or documents into optimal searchable chunks.
*   `knowledge_code_to_dcouments.py`: Specialized conversion tool for raw code files.
*   `knowledge_qa_splitter.py`, `knowledge_assets/prepromts/*.md`: Tools and prompts defining question-answer splitting strategies.
*   `knowledge_milvus.py`: Specific implementation for interacting with a Milvus vector database.
*   `knowledge_db.py`: Core logic for interacting with the document knowledge base.

**API Integration & Data Handling:**
*   `api/file_finder.py`: Mechanism to locate and index project files.
*   `api/github.py`: Wrapper for GitHub API interactions (e.g., reading commits, branches).
*   `api/users.py`: Utilities managing user data and authentication context.
*   `api/wiki.py`, `wiki_manager.py`: Logic to manage the internal wiki content.
*   `project_discover.py`: Module for discovering and mapping project structures.

**Chat & Interaction Layer:**
*   `chat/chat_engine.py`: Core engine responsible for processing natural language queries.
*   `chat_manager.py`: Manages chat history, context, and state transitions.
*   `context.py`: Stores and manages the temporary conversational context object.
*   `/utils/chat_utils.py`: Utilities specific to managing conversational inputs and outputs.

**Profile & Personalization:**
*   Definitions like `analyst.profile`, `software_developer.profile`, etc., allow agents to adopt specific roles, guiding output tone and structure based on the user's intended persona or project type.

## Dependencies

No explicit external dependencies were listed in the domain block. However, based on the file structure, this platform heavily relies on:

*   **Vector Databases:** Primarily utilizing **Milvus** (seen in `knowledge_milvus.py`) for efficient semantic search and Retrieval-Augmented Generation (RAG).
*   **LLM Providers:** Support for configurable APIs including OpenAI, Anthropic, Mistral AI, Ollama, etc., requiring corresponding SDK access/API keys.
*   **Version Control:** Requires robust integration with **GitHub** (via `github.py`) to fetch code and issue data.
*   **Caching/Session Management:** Tools like Redis or similar systems are implicitly required for handling session state (`sio/model.py`, `sio/session_channel.py`).

## Used By

No files explicitly listed utilizing this domain were provided in the input. The entire system within the `/codx-junior` structure serves as a cohesive whole, making its dependencies internal and cyclical (e.g., `chat_manager.py` depends on the results of `knowledge_engine.py`).

## Entry Points

The following files are designed to serve as the main public access points or module initializers for running components within this domain:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Used for initializing custom agent behavior.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Entry point for DevOps automation tasks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Entry point for project tracking agent workflows.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Used to initialize and manage the underlying AI backend connections.