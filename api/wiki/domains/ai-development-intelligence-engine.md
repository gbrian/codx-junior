# AI Development Intelligence Engine
## Overview
This domain represents a sophisticated artificial intelligence platform designed specifically for complex software engineering tasks. It acts as an intelligent hub, integrating multiple components like comprehensive knowledge management (via RAG), specialized agents (e.g., DevOps, Git Issue), and external system connectors.

The core functionality includes:
*   **Codebase Analysis:** Analyzing project structures and dedicated codebases.
*   **Context-Aware Interaction:** Providing context-aware conversational chat and managing the entire project lifecycle.
*   **External Integration:** Interacting with critical development tools such as GitHub, Wikis (internal knowledge bases), and databases.
*   **Advanced Workflows:** Performing advanced automation workflows through specialized agents and tools to assist developers across various stages of the SDLC.

This engine aims to provide a single interface for highly automated software development intelligence.

## Files in Domain
The domain contains an extensive collection of modules dedicated to AI functionality, project management, knowledge retrieval, task execution, chat interaction, and system utilities. Key functional areas include:

**Core & API:**
*   `/home/codx-junior-projects/codx-junior/api/*`: Root README and top-level components.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py`: Main application entry point.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/README.md`: General documentation.

**Agents & Tools:**
*   Directory `/agents/`: Contains specialized agents like `base_agent.py`, `devops_agent.py`, and `git_issues_agent.py`.
*   `tools/`: Houses utility modules such as `code_writer.py`, `fetch_webpage.py`, and file structure tools (`project_tools.py`).

**AI & Initialization:**
*   Directory `/ai/`: Manages interfaces for various LLM providers (e.g., `openai_ai.py`, `ollama.py`, `llmfactory.py`) and utility scripts.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/settings.py`: Global system configuration.

**Knowledge Management (RAG):**
*   Directory `/knowledge/`: Manages the Retrieval-Augmented Generation processes. Files include `knowledge_loader.py`, `knowledge_milvus.py` (vector store interaction), `knowledge_splitter.py`, and various prompt files (`prepromts/*`).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/`: Dedicated module for internal Wiki integration and management.

**Chat & Interaction:**
*   Directory `/chat/`: Contains logic for conversation flow, state maintenance (`chat_manager.py`), and knowledge integration into chat responses (`chat_knowledge.py`).
*   `context.py`: Manages conversational context and history.

**Project & User Management:**
*   `/api/codx/junior/project/*`: Modules related to project discovery and management (`project_discover.py`, `project_manager.py`).
*   `/api/codx/junior/users.py` / `/global_settings.py`: Handles user and global system settings.

## Dependencies
The domain currently has no explicitly defined file dependencies (depends_on_files) against other modules within the source tree, suggesting modularity or that external dependencies are managed via environment configuration not reflected in this metadata structure.

## Used By
This domain does not appear to be used by any other tracked files within the current project scope (used_by_files).

## Entry Points
The primary access points and initialization modules for this system are:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base agent class for extending AI capabilities.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Specialized agent for DevOps tasks and workflows.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Agent focused on interacting with Git issue trackers.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Initialization point for AI language model connectors and utilities.