# AI Developer Agent System

## Overview
This sophisticated framework functions as an intelligent copilot, orchestrating specialized AI agents for complex software development tasks. It integrates multiple Large Language Models (LLMs) and deep knowledge bases to provide context-aware support across coding, DevOps, and project management lifecycles. Through advanced tools and structured APIs, it aims to accelerate the entire engineering workflow. The system is designed around modularity, separating concerns such as AI integration (`/ai`), agents (e.g., `devops_agent`, `git_issues_agent`), knowledge retrieval (`knowledge`), and various specialized tooling (API interactions, chat engines).

## Files in Domain
The codebase is highly structured within the `/codx-junior` directory, focusing on functional separation across APIs, core modules, knowledge management, and agents.

### Core Application & Entry Points
*   `/home/codx-junior-projects/codx-junior/api/README.md`: General API documentation.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py`: Main application entry point.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/main.py`: Core execution script or main CLI interface.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/background.py`: Handles background processes (e.g., long-running tasks, watchers).

### Agents and Specialized Components
This section contains specialized AI agents that perform distinct job roles:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base class for all custom agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Agent specialized in DevOps tasks (CI/CD, infrastructure).
*   `/home/codx-junior-projects/codx-junior/api/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Agent focused on interacting with Git and issue tracking systems.

### AI Infrastructure & LLM Integration (`ai/`)
This module handles the interaction, configuration, and orchestration of various external language models:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Package initialization.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py`: Factory pattern for creating various LLM connections.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py`: Implementation for OpenAI API calls.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py`: Implementation using the local Ollama LLM framework.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/anthropic.py.disabled`: Disabled integration for Anthropic models (Claude).

### Knowledge Management System (`knowledge/`)
The robust knowledge base handles retrieval augmented generation (RAG) features:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/__init__.py`: Package initialization.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py`: Responsible for loading external data sources (files, wikis).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py`: Utility to break down large documents into optimal chunks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py`: Implementation for vector store interaction (Milvus).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_db.py`: Database interaction and management layer.

### External APIs & Utility Services (`api/` and `tools/`)
A collection of tools for interacting with external services:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py`: Dedicated wrapper for GitHub API interactions.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py` / `knowledge/knowledge_wiki.py`: Module handling wiki management and content creation.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/code_writer.py`: Tool for generating, reviewing, or modifying code snippets.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/fetch_webpage.py`: Web scraping and content fetching capability.

### Workflow Management & Chat (`chat/` and `context/`)
Components managing the user interaction flow:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_engine.py`: Core logic for conversation management and prompt composition.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py`: Manages the conversational state and context history.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py`: Utility functions for chat formatting and output processing.

### Profiles & Configuration (`profiles/`)
Defines various user or operational roles that guide the agent's behavior:
*   `./profiles/coding_profiles.json`: Collection of coding-specific profile configurations.
*   `./profiles/software_developer.profile`: Blueprint for a software development role.
*   `./profiles/analyst.profile`: Blueprint for an analyst role, suggesting specific analytical capabilities.

## Dependencies
No explicit `depends_on_files` were provided in the source metadata. However, functional dependencies within the system are heavy and include:
*   **Vector Databases:** Milvus (for knowledge retrieval).
*   **LLM APIs:** Requires credentials/implementations for OpenAI, Mistral, or Ollama endpoints.
*   **External Services:** GitHub API access is required by `git_issues_agent` and related API modules.
*   **Communication Layer:** Utilizes Socket.IO (`sio`) for real-time communication (sessions).
*   **Data Storage:** An associated database or structured storage mechanism is implied by the presence of file management, user authentication, and activity logging.

## Used By
No specific usage relationships were provided in the source metadata. However, the system's primary function dictates its core dependencies:
*   The `main` module (`/codx/junior/main.py`) orchestrates all other services (API calls, chat engines, background watchers).
*   Project-level functionality typically relies on modules like `file_manager`, `project_manager`, and `task_manager`.

## Entry Points
These files serve as primary interfaces or initializers for the system's core components:

*   `/home/codx-junior-projects/codx-junior/api/README.md`: Initial documentation point.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base class for agent instantiation.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Entry point for DevOps functionality.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Entry point for Git and issue management tasks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Initialization package covering all LLM interaction logic.