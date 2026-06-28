# AI Agent Copiloting Platform

## Overview
This project implements a sophisticated, enterprise-grade platform built around specialized autonomous AI agents. Its core purpose is to equip these agents with multimodal capabilities to interact deeply with various proprietary and external corporate resources. It represents a comprehensive orchestrator for advanced LLM applications, moving far beyond simple chat interfaces.

The architecture incorporates several critical components:

1.  **Agent Framework:** Provides customizable agent bases (`base_agent.py`) and specialized worker agents (e.g., `devops_agent`, `git_issues_agent`). These agents execute multi-step tasks autonomously using defined tools and decision-making processes.
2.  **Knowledge Retrieval Augmented Generation (RAG):** Implements robust systems for turning unstructured data (codebases, wikis, documents) into retrievable knowledge chunks. It handles sophisticated process flow like code chunking (`knowledge_code_splitter`), document enrichment, and storing/querying vectors via dedicated modules (e.g., `knowledge_milvus.py`).
3.  **Enterprise Integration:** Features dedicated API layers for interacting with major development tools and data sources, including GitHub APIs (`api/github.py`), internal databases (`db_router.py`, `db.py`), and Wiki systems.
4.  **Function Calling & Tooling:** Provides a rich set of reusable functions (tools) that agents can decide to call to perform actions in the real world, such as writing code (`code_writer.py`) or fetching external web content (`fetch_webpage.py`).
5.  **User Experience Flow:** Manages conversational state (`context.py`), chat lifecycle (`chat_manager.py`, `chat_engine.py`), and persistence of interactions.

In essence, this platform functions as an intelligent middleware layer that abstracts complex development tasks into natural language prompts, allowing end-users to automate workflow processes directly through targeted AI agents.

## Files in Domain

The domain is highly modular, dividing functionality into specialized directories:

### 🏛 Core API & Agents
This directory contains the main application entry points and definitions for agent behavior.
*   `codx/junior/app.py`: Primary application startup logic.
*   `codx/junior/api/README.md`: API documentation stub.
*   `codx/junior/agents/base_agent.py`: Base class for all custom agents.
*   `codx/junior/agents/devops_agent.py`: Specialized agent for DevOps tasks (e.g., pipeline management).
*   `codx/junior/agents/git_issues_agent.py`: Agent focused on interacting with GitHub issues.

### 🧠 Knowledge & RAG Engine (`knowledge/`)
This section is the heart of the long-term memory and knowledge ingestion capability.
*   `knowledge_loader.py`: Handles loading data from various sources (documents, code).
*   `knowledge_splitter.py`: Manages chunking strategies for different data types (text, code).
*   `knowledge_milvus.py`: Implementation layer connecting to a vector database like Milvus.
*   `api/codx/junior/chat/chat_knowledge.py`: Logic specific to incorporating knowledge into chat response generation.
*   *Pre-prompts:* (`prepromts/`) Contains structured instructions for optimizing embedding and retrieval quality (e.g., `extract_document_tags.md`).

### 🌐 API Connectors & Services (`api/codx/junior/api/`)
Dedicated modules handling external service communication.
*   `github.py`: Manages all interactions with the GitHub platform (issues, commits).
*   `db_router.py`, `db.py`: Handles routing and interaction with internal database connections.
*   `wiki.py`, `users.py`: Specific interfaces for organizational knowledge bases and user management.

### 💬 Chat Management & Context (`chat/`)
Focuses on the conversational state machine and history persistence.
*   `chat_manager.py`: Controls the lifecycle of a chat session.
*   `chat_engine.py`: Executes the core logic loop of processing a query against memory, context, and agents.
*   `context.py`: Manages the persistent conversation thread and state data sent to the LLM.

### 🛠 Tools & Utilities (`tools/`, `utils/`)
Reusable functions that grant the agents their capabilities (tool-calling).
*   `code_writer.py`: Tool for generating, editing, or executing code snippets.
*   `fetch_webpage.py`: Utility to retrieve content from external URLs.
*   `utils.py`, `chat_utils.py`: General helper functions and utility classes (`ai/utils.py`).

### 👤 Profiles & Contextualization (`profiles/`)
Defines standardized roles or operational contexts for the agents.
*   Các file như `analyst.profile`, `software_developer.profile`...: Files used to inject persona, constraints, and goals into the agent's prompt structure.

## Dependencies
*(Note: This section reflects external library dependencies not explicitly listed in a dedicated dependency block.)*
The platform is heavily dependent on several established industry practices and libraries required for state-of-the-art AI functionality, including:

*   **LLM Frameworks:** Likely depends on `openai` or similar SDKs (`anthropic`, `ollama`) to interact with various large language model providers.
*   **Vector Databases:** Requires interaction with external vector stores like Milvus for advanced RAG implementation.
*   **Asynchronous Programming:** Uses libraries suitable for concurrent, long-running background tasks (implied by files like `sio_background.py`).
*   **Webhooks/System Messaging:** Implies dependency on internal messaging or pub/sub systems for component communication (`event_manager.py`, `sio`).

## Used By
*(This section would list other major microservices or applications that rely on the core APIs provided by this domain. No external usage was detected.)*

## Entry Points
These files represent the main starting points for initializing and running specialized components of the platform:

*   `/home/codx-junior-projects/codx-junior/api/README.md` (Documentation entry point)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`