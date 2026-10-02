# AI Developer Intelligence Platform

## Overview
The AI Developer Intelligence Platform is an advanced, comprehensive system designed to deeply integrate and interact with large-scale codebases and complex development projects. Its core mission is to automate developer workflows by providing a unified conversational interface that understands project context, version control history (Git), organizational documentation (Wiki/Knowledge Base), and current operational statuses (DevOps).

The platform leverages specialized LLM agents for specific tasks—such as coding, DevOps operations, or Git management—and utilizes robust Retrieval-Augmented Generation (RAG) techniques. By combining conversational chat with deep project context and multimodal LLM integrations, it transforms the development cycle from scattered manual processes into a coherent, AI-powered interaction layer.

**Key Capabilities:**
* **Contextual Chat:** Conversational chat that is always grounded in the specific project's code, documentation, and history.
* **Agentic Workflow Automation:** Dedicated agents (e.g., `devops_agent`, `git_issues_agent`, specialized coding agents) handle complex tasks autonomously.
* **Knowledge Retrieval:** Advanced mechanisms for ingesting, chunking, and querying internal knowledge bases (code, wikis, documents).
* **API Integration:** Seamless connection to external tools like GitHub, version control systems, and web pages.

## Files in Domain

The codebase is organized into logical modules covering agents, artificial intelligence backend, project management, knowledge retrieval, and API services.

### 🚀 Core Logic & Application Entry Points
* `codx-junior/app.py`: Main application entry point.
* `codx-junior/main.py`: Primary execution logic file.
* `codx-junior/api/README.md` (Root API README)
* `codx-junior/global_settings.py`: Global runtime configuration settings.

### 🧑‍💻 Agents and Tools
These modules define specialized roles and capabilities for the platform's intelligent agents.
* **Specialized Agents:**
    * `agents/base_agent.py`: Base class for all custom agents.
    * `agents/devops_agent.py`: Agent focused on DevOps tasks (deployments, monitoring).
    * `agents/git_issues_agent.py`: Agent managing interactions with Git and issue tracking systems.
* **Tools Library:**
    * `tools/code_writer.py`: Tool for generating or extending code snippets.
    * `tools/fetch_webpage.py`: Utility to retrieve content from a URL.
    * `tools/project_tools.py`: General tools related to project structure and metadata.

### 🧠 AI Backend and Language Model Integration (AI)
This directory manages the connections and logic for various LLMs.
* `ai/__init__.py`: Initializes AI components.
* `ai/llmfactory.py`: Factory pattern for selecting or initializing different LLM providers.
* `ai/openai_ai.py`: Wrapper for interactions with OpenAI models.
* `ai/ollama.py`: Integration layer for local Ollama models.
* `ai/anthropic.py.disabled`, `ai/mistral_ai.py.disabled`: Disabled wrappers for other LLM providers.
* `utils.py`: General utility functions for AI processing (e.g., formatting, parsing).

### 📚 Knowledge Retrieval & RAG System
This is the core memory system, allowing the platform to reason over vast amounts of company and code knowledge.
* **Knowledge Management:**
    * `knowledge_loader.py`: Handles ingesting raw data sources.
    * `knowledge_splitter.py`: Determines optimal document chunking strategies (text, code).
    * `knowledge_code_to_dcouments.py`, `knowledge_wiki.py`: Specific logic for handling structured/semi-structured content like code files and wiki pages.
    * `knowledge_db.py`: Manages interaction with the vector database (Milvus/other backend).
    * `knowledge_milvus.py`: Implementation details for Milvus vector store interaction.
    * `knowledge_ai_search.py`, `knowledge_ai_search_message.py`: Logic layers that perform sophisticated AI-driven searches and query refinement.
    * `utils`: Contains various specialized splitters, keyword extractors, and prompt templates.

### 💬 Chat, Context, and Communication
Handles the conversational flow and state management.
* `chat/chat_engine.py`: The core engine responsible for processing prompts and generating responses using context and agents.
* `chat/chat_manager.py`: Manages chat session history and state persistence.
* `context.py`: Captures and manages current conversation and project context (e.g., files being viewed, recent commands).

### 🌐 APIs and Services
Defines the external interfaces for interacting with corporate systems.
* **API Endpoints:**
    * `api/codx/junior/utils/chat_utils.py`: Shared chat utility functions.
    * `api/codx/junior/api/github.py`: Handles integration, authentication, and reads data from GitHub.
    * `api/codx/junior/api/wiki.py` / `wiki/wiki_manager.py`: Manages Wiki interactions (read/write).
    * `api/codx/junior/api/users.py`, `api/codx/junior/api/global_settings.py`: Utilities for user data and configuration retrieval.

### 📁 Profiles, Project Management & State
Handles user roles, project structure awareness, and runtime state.
* `profiles/profile_manager.py`: Manages various professional profiles (Analyst, Developer, etc.).
* `project/project_manager.py`, `project_discover.py`: Tools for identifying and managing target projects within the codebase.
* `settings.py`: Module for persistent application settings.

### 🛠️ Utilities, Events & Metrics
* `utils/chat_utils.py`: Chat utility helpers.
* `events/event_manager.py`: Handles internal system events (e.g., file changes, session lifecycle).
* **Metrics:** Modules tracking usage and quality of interactions (e.g., `chat_heatmap.py`, `codx_junior_metrics.py`).

## Dependencies

This domain is highly integrated with various technologies and services:
* **Vector Databases:** Milvus (`knowledge/knowledge_milvus.py`) for RAG memory storage.
* **LLM Providers:** OpenAI, Ollama, Anthropic, Mistral (via wrappers).
* **Version Control Systems:** Git (implicitly through `git_issues_agent.py` and project file tracking).
* **GitHub APIs:** For issue tracking, codebase access, and OAuth (`api/codx/junior/api/github.py`).
* **Messaging Frameworks:** Socket.io (Sio) for real-time communication handling in the client layer.
* **Database:** Internal database handling via `db.py`.

## Used By

This domain is designed to be a central intelligence hub and serves as the primary backend service utilized by:
* **Frontend Application/Client:** The user interface that consumes chat commands, displays retrieved context, and sends prompts.
* **Client Processors:** Internal background processes (e.g., file watchers, webhook handlers) that feed real-time change events into the system.

## Entry Points

The main programmatic entry points for this platform are:
* `/home/codx-junior-projects/codx-junior/api/README.md` (High-level documentation access)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base class for deploying custom agents.
* `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Entry point for DevOps workflow automation.
* `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Entry point for Git and issue management workflows.
* `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Initialization container for the entire AI services layer.