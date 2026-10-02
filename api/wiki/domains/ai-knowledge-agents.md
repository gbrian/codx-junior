# AI Knowledge Agents

## Overview
This framework provides an advanced API for developing autonomous AI agents capable of complex reasoning and task execution. It acts as a unified system, integrating multiple Large Language Models (LLMs) while implementing sophisticated Retrieval-Augmented Generation (RAG) pipelines using structured knowledge bases.

These autonomous agents are designed to perform powerful actions relevant in professional development environments, such as interacting with Git for version control, managing project files, or utilizing specialized tools and external APIs to solve complex, project-related problems. It serves as the backbone for an AI system that moves beyond simple query answering toward proactive decision-making and execution.

## Files in Domain
The domain is highly modular and covers agent logic, various LLM integrations, knowledge management, API endpoints, and supporting utilities.

### 🤖 Agent Logic & Profiles
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` (Base class for all agents)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` (Specialized agent for DevOps tasks)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py` (Agent focused on Git and issue tracking)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/*` (Various profile definitions like `analyst`, `developer`, etc.)

### 🧠 AI & Model Integration
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py` (Utility for managing multiple LLM backends)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py`, `/home/codx-junior-projects/codx-junior/api/codx-junior/api/codx/junior/ai/ollama.py` (Specific integrations for major AI providers)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py`, `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ai_logger.py` (Supporting utilities for AI components)

### 📚 Knowledge & RAG Pipeline
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/*` (The entire `knowledge` directory contains core RAG logic.)
    *   **Core Classes:** `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py`, `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_db.py`.
    *   **Chunking/Splitting:** `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py`, `.../knowledge/knowledge_qa_splitter.py`.
    *   **Advanced Functionality:** Files dealing with structuring and retrieval (`knowledge_code_to_dcouments.py`, `knowledge_milvus.py`).

### 🛠 Core API & Business Logic
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/*` (Engine classes handling specific domain interactions, e.g., `git_engine.py`, `wiki_engine.py`).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/*` (High-level API wrappers for different services: `users.py`, `github.py`, `wiki.py`).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/*` (General utilities, e.g., `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py`).

### 📦 Testing & Utilities
*   `/home/codx-junior-projects/codx-junior/api/tests/...` (Comprehensive test suite for the domain functionalities).
*   `/home/codx-junior-projects/codx-junior/README.md`, `/home/codx-junior-projects/codx-junior/api/README.md` (Documentation artifacts).

## Dependencies
This section indicates files or modules that are programmatically required by the agents or core components of this domain.

*No explicit external dependencies were provided in the meta data.*

## Used By
This section details other domains or modules that utilize the functionality provided by AI Knowledge Agents.

*No usage relationships were provided in the meta data.*

## Entry Points
These files represent primary entry points into specific agent capabilities, allowing them to be instantiated and run within the system runtime environment.

*   `/home/codx-junior-projects/codx-junior/api/README.md` (General Documentation Entry)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` (Base Agent Implementation)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` (DevOps Action Entry)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py` (Git Workflow Entry)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py` (AI Core Initialization)