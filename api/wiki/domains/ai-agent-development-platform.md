# AI Agent Development Platform

## Overview
The AI Agent Development Platform is an intelligent orchestration layer designed to enable autonomous agents to handle complex, multi-step tasks within a specified software codebase or knowledge domain. It moves beyond simple chat interfaces by integrating specialized tools and engines that allow agents to interact with external systems like GitHub APIs, local file systems, Wikis, and databases (RAG).

The platform acts as the central nervous system, coordinating multiple Large Language Models (LLMs) via dedicated wrappers (OpenAI, Mistral, Ollama, Anthropic). It manages state (`Context`), handles process flow (`Engine`, `TaskManager`), stores persistent data (`DB`), and leverages modular agents to perform domain-specific actions.

### Key Capabilities:
*   **Intelligent Orchestration:** Coordinates different AI components (e.g., deciding whether to use a `git_issues_agent` or the `file_manager` based on the user request).
*   **Modular Agents:** Houses specialized agents (e.g., `devops_agent`, `git_issues_agent`) that encapsulate complex workflows and tool usage.
*   **Knowledge Retrieval (RAG):** Provides extensive knowledge management capabilities, allowing ingestion and querying of codebases, documents, wikis, and structured data using engines like `knowledge_engine`.
*   **Tooling/APIs:** Features dedicated APIs for interacting with external services, including project search, user management, file operations, and web scraping.

## Files in Domain

The codebase is highly modular, organized into API endpoints, specialized agents, knowledge base components, utility functions, and core logic engines.

### 📁 Core Logic & Engine
*   `/api/codx/junior/app.py`: The main application entry point for the API.
*   `/api/codx/junior/api/db_router.py`: Manages routing for database interactions.
*   `/api/codx/junior/context.py`: Tracks and maintains the state and memory of an active session.
*   `/api/codx/junior/engine.py`: The core execution engine responsible for orchestrating agent actions and tool calls.
*   `/api/codx/junior/task_manager.py`: Manages background or complex, multi-step tasks executed by agents.
*   `/api/codx/junior/global_settings.py`: Holds application-wide configuration variables.

### 🧑‍💻 Agents and Profiles
This directory defines the specialized autonomous workers of the platform.
*   `/api/codx/junior/agents/base_agent.py`: Abstract base class for all agents, implementing common agent patterns.
*   `/api/codx/junior/agents/devops_agent.py`: Agent focused on DevOps tasks (e.g., deployment, infrastructure).
*   `/api/codx/junior/agents/git_issues_agent.py`: Specialized agent for interacting with GitHub issues and pull requests.

### 💬 Chat and Interaction Layer
Handles user interactions, chat history, and context management.
*   `/api/codx/junior/chat/chat_engine.py`: The engine responsible for processing conversational turns and generating responses.
*   `/api/codx/junior/chat_manager.py`: Manages chat sessions, history, and retrieval.
*   `/api/codx/junior/utils/chat_utils.py`: Utility functions specifically related to chat logic.

### 🧠 Knowledge Management (RAG)
This collection of files supports ingesting, processing, storing, and retrieving knowledge from disparate sources.
*   `/api/codx/junior/knowledge/knowledge_loader.py`: Handles loading raw documents into the system.
*   `/api/codx/junior/knowledge/knowledge_code_to_dcouments.py`, `knowledge_qa_splitter.py`, `knowledge_splitter.py`: Tools for chunking and splitting structured data (code, Q&A).
*   `/api/codx/junior/knowledge/knowledge_db.py`: Manages interactions with the knowledge database backend.
*   `/api/codx/junior/knowledge/knowledge_milvus.py`: Specific implementation for using Milvus as a vector store.
*   `/api/codx/junior/knowledge/knowledge_wiki.py`: Handles integration and indexing of Wiki content.
*   `README.md`, `settings.py`, *and other model/prompt files*: Define structural documentation, configuration, and internal prompts for RAG tasks.

### ⚙️ APIs and Tools
Dedicated modules for interacting with external services and system components.
*   `/api/codx/junior/api/github.py`: Comprehensive API wrapper for GitHub interactions (repos, commits, etc.).
*   `/api/codx/junior/api/wiki.py`, `wikipedia/*`: Modules managing Wiki-related APIs and templates.
*   `/api/codx/junior/api/file_finder.py`: Utility for searching files within the codebase context.
*   `/api/codx/junior/tools/code_writer.py`: Tool used by agents to generate or modify code snippets.
*   `/api/codx/junior/tools/fetch_webpage.py`: Web scraping tool capability.
*   `/api/codx/junior/wiki/*` (templates): Frontend-facing structures for the wiki content.

### 🤖 AI Model Integration
Handles the connection and communication with various LLM providers.
*   `/api/codx/junior/ai/llmfactory.py`: Factory pattern to initialize different LLM clients.
*   `/api/codx/junior/ai/openai_ai.py`, `/api/codx/junior/ai/ollama.py`: Specific implementations for OpenAI and Ollama model providers.
*   `/api/codx/junior/ai/utils.py`: General helper functions for AI communication (prompt formatting, structured JSON output).

### 🛠 Utilities & Management
Backend services designed to manage the platform's lifecycle and maintain state.
*   `/api/codx/junior/file_manager/__init__.py`: Logic for interacting with the local file system.
*   `/api/codx/junior/changes/change_manager.py`, `watch_project_file_changes.py`: Tools for detecting and managing codebase modifications over time.
*   `message/mention_manager.py`: Handles sophisticated conversational mentions and notifications.

## Dependencies

While explicit dependency lists are not provided, the architectural dependencies suggest reliance on several core modules:

*   **Core Logic:** `api/codx/junior/context.py`, `api/codx/junior/engine.py` depend heavily on all utility libraries (`ai/*`) and tool sets (`tools/*.py`).
*   **API Integration:** Multiple APIs (e.g., `/api/codx/junior/api/github.py`, `/api/codx/junior/api/wiki.py`) rely on system configuration found in the main `settings.py` files.
*   **Knowledge Graphing:** The Knowledge module (`knowledge/*`) is heavily dependent on internal data structures, vector database clients (Milvus), and file processing utilities.

## Used By
This platform serves as a foundational API gateway. Its components are designed to be used by external consumers via the core API entry points (`app.py`, `main.py`), or integrated by other business services that require advanced AI orchestration capabilities (e.g., CI/CD systems monitoring code changes).

## Entry Points
The following files serve as primary access points for initializing and utilizing the platform's functionality:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`