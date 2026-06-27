# Autonomous Development Agent

## Overview
The Autonomous Development Agent module implements a sophisticated, multi-faceted framework designed to power AI agents for complex software development tasks. It acts as an orchestration layer, integrating multiple Large Language Models (LLMs) like OpenAI, Mistral, and Ollama, enabling advanced capabilities far beyond simple chat interfaces.

This domain's core function is built upon **deep knowledge ingestion**, allowing it to process, index, and query contextual information from entire codebases, structured wikis, project documentation (Markdown), and external resources (like GitHub Issues).

The framework supports a comprehensive technical lifecycle, enabling:
*   **Automated Bug Fixing:** Analyzing code context and reproducing bugs for suggested patches.
*   **Comprehensive Technical Support:** Answering complex developer queries by referencing the full corpus of internal knowledge.
*   **Lifecycle Management:** Guiding tasks from planning through development (coding) and deployment/monitoring (DevOps).

Through its structured API layers, it provides specialized agents—such as `devops_agent` and `git_issues_agent`—that can interact directly with version control systems and project management tools.

## Files in Domain
The domain is highly modular, segmented into distinct functional areas: Core Utilities, Agents, AI Interfacing, Knowledge Management (RAG), APIs, and Service Workers.

### 📂 Core Framework & Context
*   `codx_junior/context.py`: Manages session state and contextual variables across agent interactions.
*   `codx_junior/api/*.py` & `codx_junior/utils/*.py`: General application settings, configuration loading, and common utility functions (e.g., `global_settings.py`, `utils.py`).
*   `codx_junior/engine/*`: Core logic controllers responsible for orchestrating specialized tasks:
    *   `file_engine.py`: Handles file system operations and code retrieval.
    *   `git_engine.py`: Manages version control interactions (commits, diffs).
    *   `knowledge_engine.py`: Coordinates knowledge retrieval and grounding steps.
    *   `session.py`: Manages the overall conversation/work session state.
    *   `wiki_engine.py`: Specializes in interacting with the internal Wiki structure.

### 🤖 Agents & Automation Agents
These modules represent specialized AI personas capable of executing complex workflow chains:
*   `codx_junior/agents/base_agent.py`: The foundation class for custom AI agent development.
*   `codx_junior/agents/devops_agent.py`: Specialized agent focused on deployment, CI/CD, and infrastructure tasks.
*   `codx_junior/agents/git_issues_agent.py`: Dedicated agent for interacting with GitHub issues and pull requests.

### 🧠 AI Core & LLM Interfacing
These files manage the connection and interaction with various external LLMs:
*   `codx_junior/ai/*.py`: Abstraction layers for connecting to different LLM providers (e.g., `openai_ai.py`, `ollama.py`, `anthropic.py`).
*   `codx_junior/model/*`: Structures defining custom input, output, and system persona states (`user.py`, `wallet.py`).

### 📚 Knowledge Management & Retrieval-Augmented Generation (RAG)
This is the heart of the domain's intelligence layer:
*   `codx_junior/knowledge/*`: Contains utilities for processing and querying proprietary data sources.
    *   `knowledge_loader.py`: Handles initial ingestion pipelines from various file types.
    *   `knowledge_splitter.py`: Manages chunking strategies (code, documents, QA).
    *   `knowledge_db.py`/`knowledge_milvus.py`: Interfaces with vector databases for accurate retrieval.
    *   `knowledge_wiki.py`: Specific handlers for extracting and ingesting Wiki content.

### 🌐 Infrastructure & API Services
Components handling external integrations and persistence:
*   `codx_junior/api/*`: Exposes core domain functions via robust APIs. Includes modules for `github.py`, `users.py`, `wiki.py`, file searching, etc.
*   `codx_junior/sio/*`: WebSocket communication handlers (`sio.py`, `session_channel.py`) for real-time agent updates.
*   `codx_junior/task_manager.py`: Manages asynchronous and long-running tasks (e.g., repository analysis).

### ⚙️ System & Utility Modules
Includes non-core logic files:
*   `codx_junior/changes/*`: Handles tracking file and project changes over time (`change_manager.py`).
*   `codx_junior/log_parser.py`: Dedicated tool for analyzing runtime logs to diagnose errors.
*   `codx_junior/profile_manager.py`: Manages character configurations and role personas for agents.

## Dependencies
No external module dependencies are explicitly listed in the domain definition metadata.

## Used By
No other components or domains explicitly use this module based on the provided usage data.

## Entry Points
These files serve as primary access points, allowing users or calling services to immediately initialize and utilize specific functionalities:

*   **`codx_junior/api/README.md`**: General entry point documentation for the API structure.
*   **`codx_junior/agents/base_agent.py`**: The foundational class used when building new custom autonomous agents.
*   **`codx_junior/agents/devops_agent.py`**: Used to initiate deployment, infrastructure audits, and CI/CD workflow tasks.
*   **`codx_junior/agents/git_issues_agent.py`**: Entry point for managing project issues directly via GitHub integration.
*   **`codx_junior/ai/__init__.py`**: General initialization point for the core AI interfacing logic.