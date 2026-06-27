# AI Code and Project Copilot

## Overview
The AI Code and Project Copilot is an advanced, centralized platform designed to significantly augment software development workflows. It functions as a sophisticated copilot that goes beyond simple code completion by acting as an orchestrator of specialized AI agents and multiple Large Language Models (LLMs).

This architecture ingests and manages comprehensive organizational knowledge from diverse sources, including codebases, internal wikis, and task tracking systems like GitHub/JIRA. By unifying these data streams, the copilot empowers users to execute complex automated tasks—such as cross-project analysis or deployment planning—and participate in deep, context-aware technical conversations through various chat interfaces.

Key functionalities handled by this platform include:
*   **Knowledge Retrieval:** Semantic search across code and documentation.
*   **Agentic Workflow:** Execution of tasks using specialized agents (e.g., DevOps Agent, Git Issues Agent).
*   **Contextual Chat:** Maintaining deep state and referring to relevant project history, wiki articles, and PR discussions.
*   **Model Agnosticism:** Support for various LLMs (OpenAI, Mistral, Ollama, Anthropic placeholders).

## Files in Domain

The platform is organized into several modular packages facilitating specialized functionality:

### API & Core Logic (`api/codx-junior/`):
*   **Agents:** Defines dedicated AI agents to handle specific domain tasks (e.g., `devops_agent`, `git_issues_agent`).
    *   `base_agent.py`: Abstract base class for all specialized agents.
*   **AI Core (`ai/`):** Handles LLM integration and utilities.
    *   `llmfactory.py`: Manages connections and instances across different AI providers.
    *   `openai_ai.py`, `ollama.py`, `anthropic.py.disabled`, etc.: Wrappers for interacting with specific LLMs.
*   **API Endpoints:** Houses logic for integrating various services (GitHub, Wiki, Users).
    *   `github.py`: Handles interactions and data fetching from GitHub APIs.
    *   `wiki.py`: Manages interaction with internal knowledge bases (Wiki).
    *   `users.py`: Handles user authentication and profile management.
*   **Chat & Engine:** Core business logic for conversational flow and execution.
    *   `chat_engine.py`: The primary engine responsible for processing user input, orchestrating agents, and generating responses.
    *   `knowledge_engine.py`, `git_engine.py`, `wiki_engine.py`: Specialized engines that abstract retrieval methods specific to knowledge bases or project management tools.
    *   `context.py`: Manages the conversational context and history.

### Knowledge & Retrieval (`codx/junior/knowledge/`):
This module is responsible for ingesting, splitting, indexing, and querying organizational data to make it retrievable by the LLMs (RAG implementation).
*   **Preprocessing:** `knowledge_loader.py`, `knowledge_code_to_dcouments.py`: Logic for converting raw source material into structured chunks.
*   **Segmentation:** `knowledge_splitter.py`, `knowledge_qa_splitter.py`: Implement various strategies (code-based, question-answer based) to optimize chunk size and context density.
*   **Vector Storage & Querying:** `knowledge_db.py`, `knowledge_milvus.py`: Interfaces with vector databases for efficient similarity search.

### Profiles & Modeling:
*   **Contextual Personas:** `profiles/` directory contains profile definitions (`coding_profiles.json`, `.profile`) that allow the AI to adopt specific personas (Analyst, Software Developer) when interacting with a user or executing a task, tailoring tone and domain knowledge depth accordingly.

## Dependencies

*No explicit dependencies listed in the provided metadata.*

The platform relies heavily on external APIs for functionality:
*   **LLM Providers:** Compatibility layers for OpenAI, Mistral AI, Anthropic, Ollama.
*   **Version Control:** GitHub API for code and issue tracking data.
*   **Internal Documentation:** Wiki Management system (e.g., utilizing Markdown/Vitepress structure).
*   **Database:** Vector store dependencies (e.g., Milvus) and relational database connections (`db.py`).

## Used By

*No files explicitly listed as consuming this domain in the provided metadata.*

The `api/codx-junior/app.py` file serves as the main entry point, coordinating functionality from all other modules, making it essentially the primary consumer of the entire codebase structure.

## Entry Points
These are the primary components designed to be initialized, run, or exposed externally by the system or calling service:

*   `/home/codx-junior-projects/codx-junior/api/README.md`: The main directory entry point, providing project context and setup instructions.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Used to instantiate and manage specialized AI agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: The dedicated agent for infrastructure, deployment, and operational tasks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: The specialized agent for managing code changes, branches, and issue resolution using GitHub context.