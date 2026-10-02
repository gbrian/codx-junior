# AI Software Development Agent

## Overview
The AI Software Development Agent is an advanced intelligent agent suite designed to significantly enhance complex software development workflows. It functions as a comprehensive copilot for developers by integrating multiple specialized, interconnected AI agents and tools into a unified system.

This architecture automates various developer tasks—ranging from Git operations and project file watching to deep knowledge retrieval (RAG). By actively managing context, accessing external APIs (such as GitHub), processing structured data via knowledge graphs, and utilizing modular agent components, the system provides developers with a powerful, intelligent layer over traditional coding tools. It aims to bridge the gap between raw AI capability and practical development task execution.

## Files in Domain
This domain structure is highly modular, reflecting specialized agents, domain-specific APIs, core logic engines, and knowledge management layers. Key directories include:

*   **`api`**: Core API definitions and service handlers (e.g., `project_manager.py`, `users.py`).
*   **`agents`**: Contains the individual agent implementations responsible for specific tasks (e.g., `devops_agent.py`, `git_issues_agent.py`).
*   **`ai`**: Handles interactions with various Large Language Models (LLMs) and AI utilities (e.g., `openai_ai.py`, `ollama.py`).
*   **`knowledge`**: The core knowledge graph and retrieval system, managing document ingestion, chunking, embedding, and querying (RAG components). This includes files like `knowledge_db.py`, `knowledge_loader.py`, and various pre-prompts.
*   **`chat`**: Manages conversational state and interactions (`chat_engine.py`).
*   **`context` / `engine`**: Core logic for managing the session context, orchestrating chains of tools, and coordinating work across different specialized components (e.g., `file_engine.py`, `git_engine.py`).
*   **`tools`**: Collection of utility functions and external interactions used by agents (e.g., `code_writer.py`, `fetch_webpage.py`).
*   **`profiles`**: Defines various developer personas or project contexts, allowing the agent to adapt its behavior dynamically.

Relevant files include:

| File Path | Description |
| :--- | :--- |
| `/home/codx-junior-projects/codx-junior/api/README.md` | Domain documentation entry point. |
| `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` | Base class for all specialized agents. |
| `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` | Agent specialized in DevOps tasks and pipelines. |
| `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py` | Agent focused on Git operations and issue tracking. |
| `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/*` | Modules handling embedding, storage (Milvus), chunking, loading, and prompting for RAG system components. |
| `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/*.py` | Components responsible for executing logic chains (e.g., `git_engine.py`, `knowledge_engine.py`). |
| `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/*` | Utility tools that provide functional capabilities to the agents (e.g., interacting with files or web pages). |
| `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/*` | Definitions for specific developer roles and context profiles. |
| `/home/codx-junior-projects/codx-junior/api/codx/junior/main.py` | Primary application entry point or main execution script. |

## Dependencies
*(No explicit dependencies were provided in the input manifest, but based on file structure, the system relies heavily on:)**

*   **External APIs:** Libraries and SDKs for interacting with LLM providers (OpenAI, Mistral AI, Anthropic) and version control systems (Git/GitHub).
*   **Database Systems:** Requirements for vector stores (e.g., Milvus) and potentially relational databases to manage user data and structured knowledge graphs.
*   **Asynchronous Programming Tools:** Frameworks supporting background processing and real-time updates (implied by `sio` modules or event managers).

## Used By
*(No files were explicitly noted as using this domain in the input manifest.)*

## Entry Points
The following files serve as key initial points for implementing, testing, or leveraging agents within this service:

*   `/home/codx-junior-projects/codx-junior/api/README.md`: Primary documentation entry point.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: The abstract base class required to instantiate specialized agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Entry point for high-level DevOps automation tasks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Entry point for managing code history and resolving issues based on Git context.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Main import handler for AI utility functions, making the various LLM interactions accessible to the entire codebase.