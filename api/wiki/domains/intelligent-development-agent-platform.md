# Intelligent Development Agent Platform

## Overview
The Intelligent Development Agent Platform is a sophisticated framework designed to build and manage AI-powered development assistants. At its core, it acts as an orchestration layer, bringing together multiple specialized functional agents (such as DevOps or GitHub agent capabilities).

This platform achieves advanced automation by integrating powerful components:
*   **Large Language Models (LLMs):** Support for various models like OpenAI and Mistral, accessed through dedicated wrapper classes.
*   **Knowledge Retrieval Systems:** Advanced mechanisms to ingest, chunk, index, and query large volumes of codebase documentation and internal knowledge bases (e.g., Wiki).
*   **Custom Tooling:** A robust collection of tools enabling interaction with external services (GitHub, web scraping) and internal system functions (file management, project analysis).

The primary goal is to automate complex coding workflows, perform deep project analysis, and manage data throughout development lifecycles, minimizing manual developer intervention. The architecture supports modularity and future expansion into new agent functionalities.

## Files in Domain
This domain comprises a wide array of files covering core components like Agents, AI Model Integrations, Knowledge Management, API endpoints, Processors (Engines), and Utility functions.

### Core Structure & Utilities
*   `api/README.md`: Documentation for the API.
*   `setup_scripts/docker-compose.yaml`, `api/shared/codx-junior/scripts/traefik/traefik.yaml`: Deployment and infrastructure configuration files.
*   `utils/chat_utils.py`: Helper functions for chat operations.
*   `utils/utils.py`: General utility helper methods.

### Agents & Models
These components define specialized agents responsible for specific domain tasks (e.g., system operation, code review, project management).
*   `/codx/junior/agents/base_agent.py`: Base class defining the structure for all custom agents.
*   `/codx/junior/agents/devops_agent.py`: Agent specialized in DevOps tasks (CI/CD, deployment).
*   `/codx/junior/agents/git_issues_agent.py`: Agent focused on handling GitHub issues and Git operations.

### AI Model Integration (`ai/`)
Dedicated modules for connecting to various LLM providers.
*   `openai_ai.py`: Implementation methods for OpenAI models.
*   `ollama.py`: Interface for using self-hosted Ollama models.
*   `llmfactory.py`: Tool to manage and select different LLM instances.
*   `utils.py`, `anthropic.py.disabled`, `mistral_ai.py.disabled` (Disabled): Various wrappers/utilities for LLM providers.

### API Endpoints & Backend Logic (`api/codx/junior/`)
Defines the external and internal interfaces of the platform.
*   `api/chatGPTLikeApi.py`: Interface mimicking large chat APIs.
*   `api/db_router.py`: Routes database requests.
*   `api/file_finder.py`: Logic for searching local or remote files.
*   `api/github.py`, `api/users.py`, `api/wiki.py`, `api/global_settings.py`, `api/analytics.py`, `api/knowledge.py`: API managers for external services and core data domains (GitHub, Users, Wiki, etc.).
*   `api/project_search.py` / `search/project_search_manager.py`: Logic dedicated to project search features.

### Knowledge Management (`knowledge/`)
The system responsible for ingesting, processing, and retrieving domain-specific knowledge from codebases, wikis, and documents.
*   `knowledge_loader.py`: Handles the initial ingestion of raw data.
*   `knowledge_code_splitter.py`, `knowledge_qa_splitter.py`: Code and question-answer splitting strategies for optimal chunking.
*   `knowledge_db.py`: Manages persistence and interaction with vector databases (e.g., Milvus).
*   `knowledge_milvus.py`: Specific implementation for using the Milvus vector database.
*   `knowledge_training.py`, `knowledge_wiki.py`: Functions related to training/indexing knowledge from wikis.
*   `prepromts/*.md`: Files containing standardized prompts for different knowledge extraction tasks (e.g., enriching documents, extracting tags).

### Engines & Middleware (`engine/`)
Controls the execution flow of specific feature sets.
*   `file_engine.py`: Engine for file-based operations and analysis.
*   `git_engine.py`: Dedicated engine for complex Git interaction workflows.
*   `knowledge_engine.py`: Orchestrates the RAG pipeline using stored knowledge.
*   `session.py`, `wiki_engine.py`: Engines managing user sessions and Wiki content retrieval, respectively.

### Profiles & Context Management (`profiles/`)
Defines operational contexts and roles for agents (e.g., Analyst, Software Developer).
*   Various profile files (.profile, .md, json): Define persona-based instructions and constraints for the AI models operating within the platform.
*   `profile_manager.py`: Handles loading and switching between defined profiles.

### Tools (`tools/`)
A modular set of callable functions that agents can use to interact with the real world or system environment.
*   `code_writer.py`: Tool for generating and modifying code snippets.
*   `fetch_webpage.py`: Tool for external web scraping and data retrieval.
*   `project_tools.py`: Utilities for project-level operations (e.g., dependency checking).

## Dependencies
(No explicit dependencies listed in the source metadata.)

## Used By
(The provided domain structure does not define files dependent on this module, suggesting it is a foundational core service.)

## Entry Points
These files are designated as primary entry points for running specialized agents or initializing core services within the platform.
*   `/home/codx-junior-projects/codx-junior/api/README.md` (General API documentation)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: The base framework for defining new agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Entry point for DevOps automation workflows.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Entry point for GitHub/Git issue resolution agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Initialization point for all LLM wrappers and utilities within the API.