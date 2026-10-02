# AI Development Assistant

## Overview
The AI Development Assistant domain serves as a comprehensive, highly integrated backend framework designed for automated software development assistance. It embodies a modular architecture, combining state-of-the-art capabilities to interact with and analyze large, complex codebases.

At its core, the system integrates multiple advanced components:
1. **Advanced Agents:** Specialized intelligent agents (e.g., `devops_agent`, `git_issues_agent`) that automate complex tasks across various development lifecycles.
2. **Multi-LLM Compatibility:** Support for integrating and routing requests to heterogeneous Large Language Model providers (OpenAI, Mistral, Anthropic/Ollama), allowing developers to choose the optimal model based on task requirements or cost constraints.
3. **Knowledge Retrieval System (RAG):** A robust system implemented across multiple modules (`knowledge/*`) that ingests organizational data—including code artifacts, wikis, project documentation, and internal documents—to provide deep context for LLM reasoning.

Users can leverage this framework to perform sophisticated operations, including analyzing project metrics, interacting directly with Git version control systems, executing complex DevOps workflows, and generating contextualized advice based on the entire codebase's history and structure. It acts as a unified intelligence layer over traditional development tools.

## Files in Domain
The domain is structured into several major modules responsible for specialized functionality:

### 🌐 Core API & Utilities (`api/codx/junior`)
*   `main.py`: The primary application entry point/orchestrator.
*   `app.py`: Core application logic handling global routing and lifecycle management.
*   `globals.py`/`global_settings.py`: Global constants, environment settings, and configuration defaults.
*   `db.py`: Database interaction layer instantiation.

### 🤖 Specialized Agents (`agents/`)
These files house dedicated agent classes providing specialized capabilities:
*   `base_agent.py`: Abstract base class for all custom agents.
*   `devops_agent.py`: Tools and logic for handling CI/CD, deployment, and infrastructure tasks.
*   `git_issues_agent.py`: Agent focused on interacting with Git repositories and issue trackers (e.g., finding related issues to a code change).

### 🧠 AI Providers & LLM Management (`ai/`)
This directory manages connectivity and abstract implementation for various models:
*   `llmfactory.py`: Central hub for creating or initializing connections to different LLM providers.
*   `openai_ai.py`: Wrapper class for interacting with OpenAI's API.
*   `ollama.py`: Wrapper/implementation tailored for using local Ollama instances.
*   `anthropic.py.disabled`, `mistral_ai.py.disabled`: Placeholder or disabled modules for other major LLMs.
*   `utils.py`/`chat_utils.py`: Utility functions specific to AI interaction setup and data format conversion.

### 📚 Knowledge Retrieval (RAG) System (`knowledge/`)
This is the core context acquisition engine, handling chunking, indexing, and retrieval:
*   `knowledge_loader.py`: Manages loading structured and unstructured external knowledge sources.
*   `knowledge_splitter.py`/`knowledge_code_splitter.py`: Logic for intelligently splitting documents and code into effective chunks.
*   `knowledge_db.py`: Abstraction layer for interacting with the Vector Database (e.g., Milvus).
*   `knowledge_milvus.py`: Specific implementation for utilizing the Milvus vector database.
*   `knowledge_qa_splitter.py`/`knowledge_keywords.py`: Utilities for specialized chunking (Q&A pairs, keywords) and enhancing context.
*   `knowledge_training.py`: Tools for fine-tuning models or updating the knowledge index.

### 🔄 APIs & Integrations (`api/codx/junior/api`)
Handles external resource integration:
*   `github.py`/`misc/github.py`: Client wrappers for GitHub API interactions (issues, PRs, repos).
*   `users.py`: Management of user profiles and authentication logic.
*   `wiki.py`/`wiki_manager.py`: Dedicated API for interacting with internal wiki content systems.
*   `file_finder.py`/`project_tools.py`: Tools for traversing and summarizing the local file system structure defined by a project.

### 💬 Chat & Context Management (`chat/`, `context.py`)
Modules dedicated to improving conversational memory and response quality:
*   `chat_manager.py`: Central state machine controlling conversation flow and history management.
*   `chat_engine.py`: Orchestrates the final call to the LLM after context gathering has occurred.
*   `context.py`: Manages session-level context, keeping track of current project scope and user focus.

### 📈 Metrics & Monitoring (`metrics/`)
Responsible for tracking usage patterns:
*   `codx_junior_metrics.py`: Aggregated metrics collection point.
*   `chat_heatmap.py`/`chat_wall.py`: Tools for visualizing chat usage and engagement data.

## Dependencies

*(Note: The domain configuration files do not explicitly list internal component dependencies, but based on the file structure, the system is highly interdependent.)*

The architecture relies heavily on the following types of external libraries/dependencies to function:
1. **LLM SDKs:** Libraries corresponding to OpenAI, Mistral, and Ollama endpoints.
2. **Vector Databases:** Libraries for interacting with vector stores (e.g., Milvus).
3. **Version Control APIs:** GitHub API clients or similar Git library integrations.
4. **Database ORMs/Clients:** Connection handlers for the underlying database used for state management and metrics.

## Used By

*(Note: The domain configuration files do not explicitly list external consumers.)*

This module is designed to be the core backend intelligence layer, acting as a dependency for any client-side application or peripheral service wishing to utilize automated development assistance—including potential UI frontends (React/Vue) and background worker services.

## Entry Points

These modules are designated as primary functional starting points for external consumption:

*   `/home/codx-junior-projects/codx-junior/api/README.md`: General Domain Documentation Guide.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base Agent Initialization.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Dedicated DevOps Automation Entry Point.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Git and Issue Tracking Interaction Entry Point.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: AI Provider Initialization Context.