# Autonomous AI Agent System

## Overview

The Autonomous AI Agent System is a sophisticated, multi-faceted software framework designed to power autonomous cognitive agents capable of executing complex, multi-step workflows. This system moves beyond simple prompt-response interactions by integrating advanced components such as diverse Large Language Models (LLMs), Retrieval-Augmented Generation (RAG) for knowledge retrieval, and specialized tool orchestration.

The core capability lies in its modular architecture, which allows different agents (e.g., `devops_agent`, `git_issues_agent`) to collaborate on a task. The system manages context persistence across sessions, supports role-playing through configurable profiles, and facilitates continuous learning by indexing extensive internal corporate knowledge repositories (wiki content, codebases, documents).

Key functionalities include:
*   **Orchestration:** Handling multi-tool use, state management, and sequential task execution.
*   **Knowledge Integration:** Implementing robust RAG pipelines using specialized splitters (`knowledge_code_splitter`, `knowledge_qa_splitter`) and vector storage (Milvus) to ground LLM responses in corporate knowledge.
*   **Tooling:** Providing predefined tools for interaction with external systems like GitHub, file management, web searching (`fetch_webpage`), and code writing (`code_writer`).
*   **AI Model Abstraction:** Offering a unified interface layer (`anthropic`, `openai_ai`, `ollama`) to support various LLM providers interchangeably.

In essence, this system serves as the operational brain for sophisticated automation, enabling agents to act like virtual employees by reading documentation, writing code, interacting with APIs, and making decisions based on current context and persistent knowledge.

## Files in Domain

The project structure is highly organized into functional modules, covering API endpoints, agent logic, core services, knowledge management, and utilities.

### Core API & System Components
*   `/home/codx-junior-projects/codx-junior/api/README.md`: General project documentation.
*   `/home/codx-junior-projects/codx-junior/api/pyproject.toml`: Project dependency and configuration file.
*   `/home/codx-junior-projects/codx-junior/api/shared/codx-junior/scripts/docker-compose.yaml`: Docker setup for the entire system environment (services, databases).
*   `/home/codx-junior-projects/codx-junior/api/shared/codx-junior/scripts/traefik/traefik.yaml`: Traefik routing configuration.

### Agents (`agents/`)
This module houses specialized agents responsible for specific operational domains:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base class for all functional agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Agent focused on DevOps tasks, infrastructure, and deployment.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Agent specialized in interacting with and resolving Git issues (e.g., Jira/GitHub).

### AI Services & LLM Integration (`ai/`)
This module abstracts interactions with various LLMs:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py`: Factory/router for selecting and initializing different LLM clients.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py`: Implementation for OpenAI API calls.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py`: Implementation wrapper for local Ollama model deployment.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py`: General utility functions related to AI communication and formatting.

### Context, State & Engine (`core/`)
These files manage the state, conversation flow, and primary execution loops:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py`: Manages the session's context window and memory retention.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine.py`: Core execution engine responsible for task delegation and routing.
*   `/codx/junior/task_manager.py`: Handles the queuing and tracking of multi-step tasks.

### Knowledge Management & RAG (`knowledge/`)
This comprehensive module powers the Retrieval-Augmented Generation (RAG) system, allowing agents to access proprietary data:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py`: Loads and ingests various document types into the system.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py`: General splitter for text chunks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_splitter.py` / `knowledge_qa_splitter.py`: Specialized splitters for code and Q&A formats, ensuring semantic continuity.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py`: Interaction layer with the Milvus vector database.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_ai_search.py`: Logic for executing intelligent knowledge searches using LLMs.

### Tools & External Integration (`tools/`, `api/`)
This section defines the agents' capabilities:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/code_writer.py`: Tool for writing and suggesting code snippets, adhering to provided context.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/fetch_webpage.py`: Tool wrapper for web search functionality.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py`: API integration layer for GitHub interactions (e.g., listing repos, managing issues).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py` / `knowledge_wiki.py`: APIs dedicated to interacting with the internal wiki structure and content.

### Profiling & Messaging (`profiles/`, `mentions/`)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/profile_manager.py`: Manages agent personas, allowing dynamic adjustment of behavior (e.g., Analyst, Software Developer).

## Dependencies

The domain relies heavily on the following conceptual components and services:
*   **LLM Providers:** OpenAI, Anthropic, local Ollama endpoints.
*   **Vector Database:** Milvus (for storing and querying embedded knowledge chunks).
*   **Knowledge Bases:** Internal Wiki structures and code repositories (via Git/File Watchers).
*   **Communication:** Session management via SocketIO (`sio`).
*   **External APIs:** GitHub API, Web Search Engine.
*   **Context Management:** Persistent state storage for long-form conversational context.

## Used By

This module serves as a primary foundation used across almost every operational part of the system, specifically:
*   `base_agent.py`: All specialized agents inherit necessary logic from here.
*   `engine.py`: Executes all high-level workflows and calls services like `knowledge_engine`, `git_engine`, etc.
*   `app.py` / `main.py`: The entry points for the primary API interfaces that coordinate agent actions.

## Entry Points

The system exposes several defined entry points, allowing external clients or schedulers to interact with specific high-level functionalities:

| File Path | Purpose | Description |
| :--- | :--- | :--- |
| `/home/codx-junior-projects/codx-junior/api/README.md` | General Documentation | Primary entry for system setup and use instructions. |
| `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` | Base Agent Implementation | Used by all other agents as their foundational abstract class. |
| `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` | DevOps Automation | Endpoint for task execution related to system infrastructure and deployment pipelines. |
| `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py` | Issue Triaging Agent | Endpoint used to manage, track, and potentially resolve issues found on Git platforms. |
| `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py` | AI Services Initialization | Initializes the LLM layer for selecting and managing different model providers. |