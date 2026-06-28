# AI Developer Agent Framework

## Overview
The AI Developer Agent Framework is a comprehensive platform designed to function as an autonomous developer agent. It provides robust, context-aware development support by enabling complex understanding of coding tasks and executing multi-step workflows autonomously. The framework achieves high capability through the integration of diverse LLM models (including OpenAI and Mistral) and specialized engines. These specialization modules cover crucial development aspects such as knowledge retrieval (vector stores), GitHub interaction, system administration (DevOps), file manipulation, and deep project context analysis. Essentially, it aims to act as an advanced co-pilot managing entire coding lifecycles.

## Files in Domain
The domain encompasses a large modular codebase structured to support various functionalities:

**Core/API Structure:**
* `/home/codx-junior-projects/codx-junior/README.md`: Main documentation for the project.
* Various files under `api/codx/junior/` (e.g., `main.py`, `app.py`, `settings.py`): Contain core API logic and setup.

**LLM Integration & Utilities:**
* `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/*`: Handles connections and wrappers for different Large Language Models (e.g., `openai_ai.py`, `llmfactory.py`).
* `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/*`: General utility functions (`chat_utils.py`, `utils.py`).

**Agents:**
* `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/*`: Implement specialized agent types for specific tasks, such as `base_agent.py` (core structure), `devops_agent.py`, and `git_issues_agent.py`.

**Knowledge Retrieval & Context:**
* `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/*`: The Knowledge Base modules, handling indexing, retrieval, splitting, and augmenting context (e.g., `knowledge_loader.py`, `knowledge_milvus.py`, `knowledge_splitter.py`).
* `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_knowledge.py`: Integrates knowledge retrieval directly into the chat workflow.

**Engines & Tools:**
* `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/*`: Modules that encapsulate core capabilities like `git_engine.py`, `file_engine.py`, and specialized process managers (`knowledge_engine.py`).
* `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/*`: Implement callable actions the agent can perform (e.g., `code_writer.py`, `fetch_webpage.py`).

**Projects, Profiles & Managers:**
* `/home/codx-junior-projects/codx-junior/api/codx/junior/project/*`: Handles project discovery and management (`project_manager.py`).
* `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/*`: Stores logic for defining agent roles (e.g., `software_developer.profile`, `agent-coding-task.md`).

**Communication & State:**
* `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/*`: Implements real-time communication using Socket.IO (`sio.py`, `session_channel.py`).

## Dependencies
There are no explicit file dependencies listed in the metadata, but functionally the system relies on:

* **Multiple LLM APIs:** Integration with external services like OpenAI and Mistral (via specialized wrapper files).
* **Vector Databases:** Use of modules like `knowledge_milvus.py` suggests dependency on vector database infrastructure for knowledge retrieval.
* **Version Control Systems:** Deep integration points pointing to GitHub functionality (`api/codx/junior/api/github.py`, git engines) are critical.
* **Real-time Communication:** Dependencies on Socket.IO (Sio) suggest frontend or real-time backend components are needed for the interactive agent experience.

## Used By
There are no modules explicitly listed as using this domain, suggesting that this framework is a highly modular and self-contained API layer used by various frontends or consumer applications to provide development services.

## Entry Points
These files represent primary entry points into the system's core functionalities:

* **`/home/codx-junior-projects/codx-junior/api/README.md`**: Main documentation access point.
* **/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py**: The foundational class or utility for developing custom agents.
* **/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py**: Specialized agent logic for managing deployment and DevOps tasks.
* **`/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`**: Dedicated agent functionality for interacting with and resolving issues within a Git repository.
* **`/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`**: Entry point for model abstraction and AI service initialization.