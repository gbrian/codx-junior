# Knowledge-Driven Agent System

## Overview

The Knowledge-Driven Agent System is a sophisticated and highly modular framework designed to operate as an intelligent development agent. Its core purpose is to autonomously coordinate complex, multi-step workflows across disparate software components. The system acts as a centralized orchestration layer, managing interaction with various Large Language Models (LLMs) while ensuring that all outputs are rigorously grounded in established knowledge sources.

Key functionalities include:
*   **Knowledge Grounding:** Integrating and querying a comprehensive internal knowledge base (Vector DB/Milvus simulation), allowing agents to reference proprietary company or project data.
*   **Multi-Modal Retrieval:** Accessing and interpreting information from multiple external repositories, including Git (for version control and issue tracking) and Wikis.
*   **Workflow Automation:** Utilizing specialized engines (`agent-coding-task`, `analyst`, etc.) and profiles to execute complex tasks without manual intervention.

The architecture is built upon modularity, featuring dedicated services for context management, file interaction, chat handling, and process execution (Engine layer).

## Files in Domain

### Core Application & Execution
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py`: Main application entry point.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/main.py`: Core execution logic startup.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/global_settings.py` (Multiple locations): Central configuration and shared settings across modules.

### Agents & Profiles
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Abstract base class for all specialized agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Agent handling infrastructure and DevOps tasks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Specialized agent for interacting with Git issues and tickets.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/profile_manager.py`: Manages loading and switching between operational profiles.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/*`: Directory containing various job profiles (`analyst`, `software_developer`, etc.) that define agent behavior roles.

### AI & LLM Management
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py`: Factory for managing and abstracting various LLM connections.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/*`: Files handling specific LLMs (e.g., `openai_ai.py`, `ollama.py`) and utilities (`utils.py`).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/*.py`: Modules dedicated to knowledge ingestion, splitting, and retrieval logic (e.g., `knowledge_splitter.py`, `knowledge_milvus.py`).

### Knowledge Management System
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/*.py`: Core implementation files for managing knowledge sources (loading, chunking, querying).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_db.py`: Handles persistent storage and interaction with the knowledge database.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/*.py` / `/home/codx-junior-projects/codx-junior/.../wiki/wiki_manager.py`: Components for interacting with and structuring data from Wiki sources.

### API Integration & Services
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/*`: Modules handling external system interactions (e.g., `github.py`, `wiki.py`, `users.py`).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/project/*`: Project discovery and management utilities (`project_discover.py`, `project_manager.py`).

### State, Context, & Events
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py`: Manages the current operational context for agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/db.py`: Database interaction layer.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/events/event_manager.py`: System for handling and dispatching events during workflow execution.

### Engines & Tools (Execution Layer)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/*.py`: Core engines governing domain capabilities (e.g., `knowledge_engine.py`, `git_engine.py`).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/*.py`: Collection of callable, defined tools the agents can use (e.g., `code_writer.py`, `fetch_webpage.py`).

## Dependencies

No explicit cross-domain dependencies were listed in the manifest. The system is designed to be highly cohesive within its functional modules, communicating primarily through a centralized **Context** model and an **Event Manager**.

*Inferred Operational Dependency:* Requires reliable external API connections for LLM providers (OpenAI, Anthropic, Mistral, Ollama), GitHub APIs, and Wiki/Knowledge Base endpoints.

## Used By

No usage dependencies were listed in the manifest. This domain serves as a foundational, highly integrated service layer that is expected to be utilized by various front-end clients or core application loops (such as chat engines and job routers) depending on the required agent functionality. 
*(Note: The `codx/junior` directories themselves serve as consumers of this system.)*

## Entry Points

The following files act as primary initializers or starting points for the specialized agents within the Knowledge-Driven Agent System, enabling immediate execution of complex workflows:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` (Base structure)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` (DevOps task execution agent)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py` (Git/Issue management agent)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py` (AI module initialization)