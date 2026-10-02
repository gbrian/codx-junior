# AI Agent & Knowledge Engine

## Overview
The AI Agent & Knowledge Engine is the central intelligence core for the autonomous workspace platform. This module cluster provides sophisticated orchestration capabilities, enabling specialized agents—such as DevOps or Git Issue managers—to execute complex, context-aware tasks independently.

At its heart, this domain implements a powerful Retrieval Augmented Generation (RAG) pipeline, allowing the system to ground all generated responses and actions in proprietary corporate data, project documentation, or raw codebases rather than relying solely on general pre-trained LLM knowledge.

**Key Functionalities:**
*   **Agent Orchestration:** Manages specialized agents (`devops_agent`, `git_issues_agent`) that encapsulate specific professional workflows (e.g., managing CI/CD processes, interacting with Git APIs).
*   **Knowledge Retrieval:** Features a robust set of knowledge modules (e.g., `knowledge_loader`, `knowledge_milvus`). It ingests diverse data types—wikis, code snippets, documents—splits them into manageable chunks, and stores/retrieves context for LLM prompts.
*   **Workflow Management:** Provides the framework (`base_agent.py`, `engine.py`) to manage multi-step processes, session state, global settings, and contextual awareness throughout a user interaction or automated task.
*   **LLM Integration:** Acts as an abstraction layer over various Large Language Models (LlamaFactory, OpenAI AI, Ollama), ensuring flexibility in model choice while maintaining a consistent API interface.

## Files in Domain

The codebase is highly structured into functional units:

### 🧩 Agent Infrastructure & Core Logic
These files define the foundational logic for intelligence and workflow execution.
*   `/api/codx/junior/agents/*`: Definitions for specialized robotic agents (e.g., `base_agent`, `devops_agent`, `git_issues_agent`).
*   `/api/codx/junior/engine/*.py`: Core orchestration logic (`engine.py` manages the overall process; `knowledge_engine.py` directs data flow).
*   `/api/codx/junior/context.py`, `/api/codx/junior/globals.py`: State management and global configuration storage.

### 🧠 Knowledge and RAG Pipeline
The entire knowledge subdirectory is dedicated to ingesting, indexing, retrieving, and utilizing proprietary information.
*   `knowledge_loader.py`, `knowledge_code_to_dcouments.py`: Responsible for data ingestion from various sources (files, wikis).
*   `knowledge_splitter.*`: Utilities for chunking documents effectively (`knowledge_qa_splitter`, `knowledge_code_splitter`).
*   `knowledge_milvus.py`, `knowledge_db.py`: Handlers connecting the system to vector/search databases.
*   `knowledge_ai_search.py`: Manages the entire search workflow against proprietary data.

### 🗣️ LLM Interaction & Chat Management
Components responsible for handling conversational interfaces and model communications.
*   `/api/codx/junior/chat/*`: Logic for managing conversation history, state (`chat_manager.py`, `chat_engine.py`).
*   `/api/codx/junior/ai/*.py`: Model wrapper scripts (e.g., `openai_ai.py`, `ollama.py`) providing model abstract interface compatibility.

### 🛠️ Tools and Services
Utility modules that connect the AI core to external services or internal data sources.
*   `/api/codx/junior/tools/*.py`: External tool interfaces (e.g., `code_writer.py`, `fetch_webpage.py` for browsing).
*   `/api/codx/junior/wiki/*`: Dedicated modules for interacting with and managing wiki content (`wiki_manager.py`).
*   `/api/codx/junior/project/*.py`: Modules for project discovery and management, linking AI actions to structured organizational boundaries.

## Dependencies

This domain relies heavily on several interconnected systems and internal services:

1.  **External LLM APIs:** It maintains abstract interfaces for major models (OpenAI, Ollama, Mistral) but critically depends on their respective API keys and operational status (`api/codx/junior/ai/*`).
2.  **Database Layers:** Requires read/write access to a persistence layer (e.g., `db.py`) and specialized vector stores for efficient knowledge retrieval (Milvus is explicitly used in the `/knowledge` pipeline).
3.  **Version Control System (Git):** Direct interaction with Git APIs and file changes are fundamental, supporting agents like `git_issues_agent`.
4.  **File System/Project Structure:** Dependency on reading local filesystems to ingest code and documents (`file_finder.py`, core file managers).

## Used By

This module is a foundational layer that underpins the entire product experience. While specific higher-level entry points are not listed, functionally, this domain is used by:

*   **High-Level Application Services:** Any script or application responsible for initiating an intelligence task (e.g., responding to a user request coming through `api/codx/junior/app.py`).
*   **Monitoring and Metric Systems:** The chat and metric files suggest integration with external dashboards that consume the output of the agents (`metrics/*.py`).

## Entry Points

These files represent the primary starting points for invoking core AI functionalities within the codebase:

*   `/api/codx/junior/agents/base_agent.py`: Provides the fundamental abstract class or structure that all specialized agents must follow, defining the standard method for execution and communication.
*   `/api/codx/junior/agents/devops_agent.py`: The functional entry point for automating DevOps-related tasks (e.g., deployment workflow management).
*   `/api/codx/junior/agents/git_issues_agent.py`: The entry point for agents dedicated to interacting with and resolving issues within a Git repository context.
*   `/api/codx/junior/ai/__init__.py`: Initializes the AI services, making the core LLM communication utilities available throughout the project.