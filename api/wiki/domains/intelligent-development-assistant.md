# Intelligent Development Assistant

## Overview
This platform provides a sophisticated AI agent system designed to automate complex software engineering workflows. It combines advanced LLM capabilities with context-aware knowledge bases, allowing agents to read project files, access internal documentation (Wiki/Knowledge), and interact with external systems like GitHub. Through diverse, specialized developer profiles, the assistant functions as an intelligent copilot that orchestrates tasks—from debugging logic errors to implementing new features—making complex development processes streamlined and highly automated.

## Files in Domain
The domain is structured into several functional areas: API endpoints, Agent definitions, AI tooling, Knowledge Management, Chat/Interaction services, Profiling, and Utilities.

**Agent Definitions & Core Logic:**
*   `codx-junior/api/README.md` (API Documentation)
*   `codx-junior/api/codx/junior/agents/base_agent.py`: Base class for all specialized agents.
*   `codx-junior/api/codx/junior/agents/devops_agent.py`: Agent specialized in DevOps tasks (deployment, infrastructure).
*   `codx-junior/api/codx/junior/agents/git_issues_agent.py`: Agent for managing GitHub issues and repository interactions.

**AI Interface & Core Services (`/api/codx/junior/ai/`):**
*   `codx-junior/api/codx/junior/ai/__init__.py`
*   `codx-junior/api/codx/junior/ai/utils.py`: General utility functions for AI interactions.
*   `codx-junior/api/codx/junior/ai/llmfactory.py`: Factory pattern for handling various LLM connections.
*   `codx-junior/api/codx/junior/ai/openai_ai.py`: Implementation for OpenAI interactions.
*   `codx-junior/api/codx/junior/ai/ollama.py`: Integration layer for running models via Ollama.
*   `codx-junior/api/codx/junior/api/chatGPTLikeApi.py`: Abstracted API wrapper simulating chat model calls.

**Core APIs and Managers (`/api/codx/junior/api/`):**
*   `codx-junior/api/codx/junior/app.py`: Main application entry point or core service orchestrator.
*   `codx-junior/api/codx/junior/api/global_settings.py`: Handles global system configurations.
*   `codx-junior/api/codx/junior/api/users.py`: User profile and entitlement management.
*   `codx-junior/api/codx/junior/api/wiki.py`: API interface for managing wiki data (reading/writing).
*   `codx-junior/api/codx/junior/api/github.py`: API wrapper for GitHub interactions (e.g., pull requests, issues).
*   `codx-junior/api/codx/junior/api/file_finder.py`: Service to locate project files efficiently.
*   `codx-junior/api/codx/junior/api/db_router.py`: Handles dynamic routing and interaction with the database layer.
*   `codx-junior/api/codx/junior/api/project_search.py`: Logic for searching project metadata.
*   `codx-junior/api/codx/junior/api/knowledge.py`: Entry point for general knowledge retrieval services.

**Knowledge Base & Indexing (`/api/codx/junior/knowledge/`):**
*   `codx-junior/api/codx/junior/knowledge_loader.py`: Responsible for ingesting raw data sources (e.g., markdown, code).
*   `codx-junior/api/codx/junior/knowledge/knowledge_splitter.py`: Manages chunking and splitting of large documents or code blocks.
*   `codx-junior/api/codx/junior/knowledge/knowledge_db.py`: Handles interaction and querying against the structured knowledge database (e.g., Milvus).
*   `codx-junior/api/codx/junior/knowledge/knowledge_milvus.py`: Specific implementation for vector store operations using Milvus.
*   `codx-junior/api/codx/junior/knowledge/knowledge_qa_splitter.py`: Specialized splitter optimized for Question Answering context.
*   `codx-junior/api/codx/junior/knowledge/__init__.py`: Module root for knowledge management functions.

**Workflow Engines & Context Handling:**
*   `codx-junior/api/codx/junior/context.py`: Manages the active context window and session state for LLMs.
*   `codx-junior/api/codx/junior/engine/__init__.py`: Module root for various engine components.
*   `codx-junior/api/codx/junior/engine/file_engine.py`: Engine dedicated to reading, analyzing, and synthesizing project code files.
*   `codx-junior/api/codx/junior/engine/git_engine.py`: Engine interacting with Git history and diffs for context.
*   `codx-junior/api/codx/junior/engine/knowledge_engine.py`: Core engine leveraging the internal knowledge base.
*   `codx-junior/api/codx/junior/engine/wiki_engine.py`: Engine dedicated to retrieving and synthesizing content from the Wiki.

**Chat, Messaging, and History:**
*   `codx-junior/api/codx/junior/chat_manager.py`: Centralized manager for chat session states.
*   `codx-junior/api/codx/junior/chat/chat_engine.py`: Core logic for generating responses and managing conversational flow.
*   `codx-junior/api/codx/junior/chat/chat_knowledge.py`: Integration point to fuse chat inputs with knowledge results (RAG).
*   `codx-junior/api/codx/junior/utils/chat_utils.py`: Utility methods for structured chat data handling.

**Profiles and Agent Customization:**
*   `codx-junior/api/codx/junior/profiles/profile_manager.py`: Central system for loading, managing, and switching developer profiles.
*   `codx-junior/api/codx/junior/agents/*agent.py`: (See above) Specialized agents.
*   `codx-junior/api/codx/junior/profiles/*.profile*`: Various profile configurations (`coding_profiles.json`, `analyst.profile`, etc.).

**Tools and External Interactions:**
*   `codx-junior/api/codx/junior/tools/__init__.py`: Module root for callable functions (Tools).
*   `codx-junior/api/codx/junior/tools/code_writer.py`: Tool simulating code generation or writing tasks.
*   `codx-junior/api/codx/junior/tools/fetch_webpage.py`: Tool for gathering external, web-based information (RAG enhancement).
*   `codx-junior/api/codx/junior/utils/utils.py`: General utility functions.

**Backend Infrastructure & Management:**
*   `codx-junior/api/codx/junior/db.py`: Database connector and session management.
*   `codx-junior/api/codx/junior/settings.py`: General system settings file.
*   `codx-junior/api/codx/junior/sio/*sio*.py`: Files dealing with Socket.IO for real-time communication (e.g., `sio_background.py`).

## Dependencies
The domain relies heavily on several core technological components:
1. **Large Language Model Providers:** Requires integration capabilities for OpenAI, Anthropic (though disabled/marked out), and Ollama/Mistral AI.
2. **Vector Databases:** Depends on a specialized vector store capable of handling dense representations of knowledge chunks (e.g., Milvus is explicitly used).
3. **Version Control Systems:** Requires robust interaction layers with Git and GitHub APIs for codebase introspection, commit history, and issue management.
4. **Authentication/Networking:** Relies on secure OAuth mechanisms (GitHub OAuth) and real-time communication protocols (Socket.IO).

## Used By
(No specific consuming modules were provided in the file structure, but conceptually, this domain is used by a main client application or CLI tool that orchestrates interactions between the various agents and engines.)

## Entry Points
The primary entry points for utilizing the core functionalities of the Development Assistant are:

*   `/home/codx-junior-projects/codx-junior/api/README.md`: General API documentation start.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Starting point for creating new specialized agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Initiates workflow automation for DevOps tasks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Starts the process of managing and resolving issues via Git integration.