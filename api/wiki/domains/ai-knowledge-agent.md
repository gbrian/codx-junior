# AI Knowledge Agent

## Overview
The AI Knowledge Agent module cluster serves as an intelligent, sophisticated platform designed to automate complex workflows within professional and technical environments. Its core function is processing highly varied and unstructured information derived from multiple sources, including internal codebases, project wikis, documentation (RAG), internal ticket systems, and general knowledge bases.

By leveraging a combination of specialized agents (e.g., DevOps Agent, Git Issues Agent), advanced Large Language Model (LLM) integrations (supporting OpenAI, Mistral, Ollama, etc.), and robust Retrieval-Augmented Generation (RAG) techniques, the system aims to act as an all-encompassing assistant for both software development acceleration and comprehensive organizational knowledge management.

## Files in Domain
The domain encompasses a rich structure of modules covering agents, various AI integrations, knowledge processing pipelines, API services, and utility functions.

### 📂 Agents & Execution Logic
These files define the specialized actors that perform tasks.
*   `/codx/junior/agents/base_agent.py`: The foundational class for all custom agents.
*   `/codx/junior/agents/devops_agent.py`: Agent focused on DevOps workflows and operational tasks.
*   `/codx/junior/agents/git_issues_agent.py`: Agent dedicated to interacting with and reasoning about Git issues.

### 🧠 AI & LLM Integrations (`./ai` directory)
This section handles the plumbing for communicating with various external or contained language models.
*   `/codx/junior/ai/llmfactory.py`: Centralized factory for LLM connections.
*   `/codx/junior/ai/openai_ai.py`: Integration module for OpenAI services.
*   `/codx/junior/ai/ollama.py`: Integration module for running local Ollama models.
*   `/codx/junior/api/codx/junior/chatGPTLikeApi.py`: A potentially abstract or generalized API wrapper.
*   `/codx/junior/ai/utils.py`, `alice/codx/junior/ai/ai_logger.py`: Utility and logging functions for AI processes.

### 📚 Knowledge Retrieval & RAG Pipeline (`./knowledge` directory)
This critical section handles the ingestion, chunking, indexing, and retrieval of proprietary data (code, wikis).
*   `/codx/junior/knowledge/knowledge_loader.py`: Handles loading raw data from various sources.
*   `/codx/junior/knowledge/knowledge_splitter.py`: Core logic for splitting documents into meaningful chunks.
*   `/codx/junior/knowledge/knowledge_milvus.py`: Implementation for advanced vector database storage (Milvus).
*   `/codx/junior/knowledge/knowledge_wiki.py`: Dedicated handlers for wiki content integration and retrieval.
*   `prepromts/*`: Directories containing specialized prompt templates (`code_to_chunks.md`, `enrich_document.md`, etc.) guiding the RAG process.

### ⚙️ APIs & Utilities
Core modules providing access points to internal or external services.
*   `/codx/junior/api/github.py`: Handles GitHub API interactions (e.g., fetching repos, issues).
*   `/codx/junior/api/wiki.py`, `/codx/junior/wiki/wiki_manager.py`: Modules governing wiki interaction and management.
*   `/codx/junior/api/file_finder.py`: Manages structured search within filesystems.
*   `/codx/junior/api/db_router.py`, `/codx/junior/api/utils.py`: Database routing and general utility functions.

### 💻 Core Business Logic & Engine Components
These modules govern the execution workflow, state management, and interaction with systems.
*   `/codx/junior/engine/*.py`: Files like `git_engine.py`, `knowledge_engine.py`, and `wiki_engine.py` encapsulate complex domain-specific operations.
*   `/codx/junior/context.py`: Manages the chat or conversation state context.
*   `/codx/junior/utils/chat_utils.py`, `/codx/junior/api/README.md`: General utilities and documentation starting points.

### 🎭 Profiles & Settings
Modules defining user roles, system configurations, and behavioral constraints.
*   `profiles/*`: Directory containing various specialized profiles (e.g., `software_developer.profile`, `analyst.profile`).
*   `/codx/junior/settings.py`: Handles global application settings.

## Dependencies
The domain relies on several architectural assumptions rather than explicit external dependencies listed in the metadata structure. Functionally, it manages complex integrations with multiple services:

1.  **External APIs:** GitHub (for repositories and issues), Wiki platforms, and various LLM providers (OpenAI, Mistral, Ollama).
2.  **Databases:** Specialized knowledge retrieval requires vector databases (Milvus) alongside general database routing (`db_router.py`).
3.  **Asynchronous Communication:** The presence of `sio/` files indicates dependency on Socket.IO for real-time background updates and communication streams.

## Used By
This module acts as a core foundation layer, meaning it is heavily utilized by top-level entry points or other service layers that require specialized intelligence. It is intended to be the underlying mechanism called by:

*   Main application loop (`app.py`, `main.py`).
*   User/Frontend Interfaces (which interact with APIs like `/codx/junior/api/README.md` for presentation).
*   High-level orchestration processes that combine multiple capabilities (e.g., "Find code base knowledge" $\rightarrow$ Use **Knowledge Engine** + **File Finder**; or "Fix a git bug" $\rightarrow$ Use **DevOps Agent** + **Git Issues Agent**).

## Entry Points
The following files are primary entry points used to initiate workflows, test functionality, or run the application.

*   `/home/codx-junior-projects/codx-junior/api/README.md`: General documentation and entry point overview.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: The base class for initializing custom agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Entry point for DevOps workflow execution.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Entry point for Git Issue management workflows.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Initialization package for all LLM integration services.