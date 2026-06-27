# AI Code Development Platform

## Overview
This platform serves as a sophisticated, agentic backbone for AI software development assistance. It integrates multiple Large Language Models and specialized agents to execute complex tasks, supporting everything from code generation to DevOps workflows. The system utilizes robust knowledge retrieval (RAG) over project files, wikis, and issues to provide deeply contextual chat and automated tooling. Its structure allows it to manage complex state changes, analyze codebases, interact with external systems like GitHub, and maintain a comprehensive internal knowledge base for continuous improvement in development cycles.

## Files in Domain
The domain contains a wide variety of modules essential for agentic workflow management, knowledge retrieval, API handling, and various specialized utilities.

**Knowledge & Context:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/README.md` (Informational)
*   Scripts for data chunking and embedding: `knowledge_code_splitter.py`, `knowledge_qa_splitter.py`, `knowledge_splitter.py`.
*   Core database handling and interactions: `knowledge_db.py`, `knowledge_milvus.py`.
*   Processors: `knowledge_loader.py`, `knowledge_wiki.py`.
*   Prompting/Settings: `knowledge_prompts.py`, `settings.py`.

**Agents & Core Logic:**
*   `base_agent.py`: Provides the foundation for all specialized agents.
*   `devops_agent.py`: Handles DevOps-related tasks and workflows.
*   `git_issues_agent.py`: Manages interactions with GitHub issues and repositories.

**Architecture & APIs:**
*   `api/codx/junior/app.py`: Main application entry point.
*   `api/codx/junior/api/*`: Contains specialized API modules like `chatGPTLikeApi.py`, `db_router.py`, `file_finder.py`, `github.py`, and wrappers for user management (`users.py`) and wikis (`wiki.py`).

**Chat & Engine Components:**
*   `chat/chat_engine.py`: The central engine managing chat interactions.
*   `context.py`: Manages the contextual state during conversations.
*   `engine/**:*.py`: Specialized engines for knowledge retrieval, Git interactions, and session management (`knowledge_engine.py`, `git_engine.py`, etc.).

**Utilities & Advanced Features:**
*   File Management: `codx/junior/file_manager/__init__.py`, file change watchers (`watch_project_file_changes.py`).
*   Model Handling: `model/model.py`.
*   Profiling/Evaluation: `profiler.py`, metrics classes (e.g., `chat_heatmap.py`).
*   Project Management: `project_manager.py`.

**Configuration & Infrastructure:**
*   `pyproject.toml`: Dependency and configuration file.
*   `shared/codx-junior/scripts/*`: Deployment scripts (`docker-compose.yaml`, `traefik/traefik.yaml`).

## Dependencies
(No explicit dependencies were listed in the input.)

## Used By
(This module is highly interconnected within its own structure, managing core services like chat and agents. No external modules using this domain were specified.)

## Entry Points

The following files are designated as primary entry points for interacting with the platform's core functionality:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`