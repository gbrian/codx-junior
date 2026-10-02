# AI Development Agent Framework
## Overview

This module cluster constitutes a comprehensive **AI Development Agent Framework** designed to streamline and automate the entire software development lifecycle (SDLC). It functions as an advanced orchestrator, integrating multiple sophisticated Large Language Model (LLM) providers (such as OpenAI, Anthropic, Mistral, Ollama) within a unified Python structure.

The core capability resides in its ability to manage complex workflows by combining **Retrieval-Augmented Generation (RAG)** techniques with specialized tools and domain APIs. The framework allows internal agents—like `devops_agent` or `git_issues_agent`—to interact deeply with external systems, including GitHub, internal knowledge bases, live code files, and project management tools. By structuring communication through modular layers (agents, engines, utilities), it provides a highly flexible foundation for AI-powered coding assistants and development automation tooling.

---

## Files in Domain

The framework is structured into several key components:

### Core Structure & Utilities
*   `api/README.md`: Directory README.
*   `api/codx/junior/utils/****: General purpose helper modules (`utils.py`, `chat_utils.py`).
*   `api/codx/junior/*/*.py`: Central business logic and managers (e.g., `app.py`, `main.py`, `task_manager.py`).

### Agents & Orchestration Layer
These files define specialized agents that interact with the system's tools and APIs:
*   `api/codx/junior/agents/base_agent.py`: Base class for all custom agents.
*   `api/codx/junior/agents/devops_agent.py`: Agent focused on DevOps tasks (CI/CD, infrastructure).
*   `api/codx/junior/agents/git_issues_agent.py`: Agent specifically designed to interact with GitHub issues and git operations.

### AI Providers & Inference Layer
This section handles the connection and abstraction layer for various LLMs:
*   `api/codx/junior/ai/**`: Directory housing multiple provider implementations.
    *   `llmfactory.py`: Central hub for model management.
    *   `openai_ai.py`: Implementation for OpenAI models.
    *   `ollama.py`: Integration layer for local Ollama instances.
    *   *(Note: `anthropic.py.disabled` and `mistral_ai.py.disabled` indicate integrations that are currently disabled).*

### Knowledge Module (RAG/Vector Search)
The knowledge base management is highly sophisticated, supporting various ingestion and retrieval methods:
*   `api/codx/junior/knowledge/**`: Directory handling all RAG mechanics.
    *   `knowledge_loader.py`: Responsible for ingesting raw data.
    *   `knowledge_splitter.py`: Manages text chunking strategies.
    *   `knowledge_db.py`: Interaction with the underlying vector store (e.g., Milvus).
    *   `knowledge_milvus.py`: Specific implementation for Milvus database integration.
    *   `knowledge_qa_splitter.py`, `knowledge_code_to_dcouments.py`, etc.: Specialized splitting/processing scripts.

### API & Integrations Layer (Tools)
These components provide structured interaction with external services:
*   `api/codx/junior/api/**`: Directory containing wrappers and connection points.
    *   `github.py`: Dedicated integration for GitHub APIs.
    *   `wiki.py`, `user_management.py`, etc.: Modules for interacting with specific organizational data sources (Wiki, Users).

### Chat & Context Management
These modules manage the conversational flow and state:
*   `api/codx/junior/chat/**`: Handling chat history, engines, and exports (`chat_manager.py`, `chat_engine.py`).
*   `api/codx/junior/context.py`: Managing session context and memory.

### Project & Profile Management
Tools for understanding the development context:
*   `api/codx/junior/project/**`: Handling project structure, discovery (`project_manager.py`, `project_discover.py`).
*   `api/codx/junior/profiles/**`: Managing different professional roles or agent persona profiles (e.g., `software_developer.profile`, `analyst.profile`).

---

## Dependencies

*(No explicit dependencies are listed in the domain metadata.)*

The framework, however, relies heavily on:
1.  **External LLM API Keys:** Accounts and credentials for OpenAI, Anthropic, Mistral AI, etc.
2.  **Vector Database Services:** A running instance of a database like Milvus or Pinecone (as indicated by `knowledge_milvus.py`).
3.  **Version Control Systems:** GitHub access tokens/OAuth credentials.

## Used By

*(This domain currently appears to be the foundational layer, and no explicit files are listed as depending on it.)*

---

## Entry Points

These scripts serve as primary initialization points for running or testing core agent functionalities:

| File Path | Description |
| :--- | :--- |
| `api/README.md` | Top-level documentation entry point. |
| `api/codx/junior/agents/base_agent.py` | Base class used by custom agents for inheritance and standardized execution flow. |
| `api/codx/junior/agents/devops_agent.py` | Dedicated entry for executing DevOps automation tasks using AI reasoning. |
| `api/codx/junior/agents/git_issues_agent.py` | Entry point enforcing Git and issue management workflows powered by AI. |
| `api/codx/junior/ai/__init__.py` | Initialization module for accessing all LLM providers and AI utilities. |