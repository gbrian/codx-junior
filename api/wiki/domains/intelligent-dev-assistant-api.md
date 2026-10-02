# Intelligent Dev Assistant API

## Overview
The Intelligent Dev Assistant API is a comprehensive backend module suite designed to power autonomous developer agents. This system integrates advanced Large Language Model (LLM) capabilities, enabling sophisticated chat interactions, deep project analysis, and complex task automation across diverse tools such as Git version control and local file systems.

This domain aims to build knowledge-aware assistants that function as intelligent partners, helping developers understand massive codebases, diagnose issues, generate complex features, and complete intricate coding tasks with minimal manual intervention. Key areas include state management (chat history, context), knowledge graph building from code/documentation, and specialized agents for infrastructure or issue tracking.

## Files in Domain
The codebase is extensive, reflecting multiple functional layers: core API logic, agent definitions, LLM integration, documentation handling, and specific tool connectors.

**Core Application & Routing:**
*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py` (Main entry point)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/settings.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/db_router.py` (Database routing)

**Agents & Specialized Logic:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` (Base agent class)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`

**Language Model (LLM) Integration (`ai/`):**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/anthropic.py.disabled`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py` (Universal LLM interface)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py` (Local model support)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py` (OpenAI integration)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py`

**Context Management & Memory:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py` (Manages session state)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/components/utils.py`

**Knowledge Retrieval & Embedding (`knowledge/`):**
This is the core self-improvement and memory system.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py` (Ingestion entry point)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_db.py` (Database interaction)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py` (Vector store specific implementation)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_to_dcouments.py` (Code chunking)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_wiki.py` (Wiki content handling)
*   *Supporting Prompts:* (`prepromts/*.md`)

**Tools & External Interaction:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/code_writer.py` (Code modification tool)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/fetch_webpage.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/project_tools.py`

**Data Persistence & Utility:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/db.py` (Database connection)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/utils.py`

**Profiling, Metrics & Profiles:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/profile_manager.py` (Handles user roles/personas)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiling/profiler.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/*.py` (Various metric trackers)

**Workflow & Project Management:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/project/project_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/project/project_discover.py`

## Dependencies
No formal dependencies were specified in the provided metadata block (`<depends_on_files>`). The system is designed to rely on internal modules and external APIs (e.g., OpenAI, Anthropic) configured via environment variables or initialization files (`codx/junior/settings.py`).

## Used By
No usage indicators were provided in the provided metadata block (`<used_by_files>`). This module suite represents a foundational backend service used throughout the larger platform ecosystem.

## Entry Points
These files contain core logic that initiates primary services or agent functionalities, making them critical starting points for system interaction and API calls.

*   `/home/codx-junior-projects/codx-junior/api/README.md`: General documentation entry point.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Defines the blueprint for all developer agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Specific agent for infrastructure and operations tasks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Specialized agent for GitHub workflow management (issues, pull requests).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: The primary module entry point for abstracting and initializing various LLM backends.