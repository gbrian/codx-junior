# Code Automation Agents Platform

## Overview
The Code Automation Agents Platform is a sophisticated framework designed for deploying specialized AI agents capable of executing complex software development tasks autonomously. At its core, the platform functions as an intelligent orchestrator, coordinating various AI capabilities to manage the entire software development lifecycle within a project context.

It achieves high performance and accuracy by integrating multiple Large Language Model (LLM) APIs (OpenAI, Mistral, Ollama, Anthropic via wrappers), making it model-agnostic. A core feature is its advanced Knowledge Retrieval system, which significantly augments agent context using real-time project data such as proprietary wikis, GitHub historical records, and local codebase indexing.

The platform supports a wide array of specialized agents and workflows, including:
*   **Code Generation & Debugging:** Direct assistance in writing, refactoring, and fixing code segments.
*   **DevOps Orchestration:** Managing deployment pipelines, infrastructure tasks, and CI/CD workflows.
*   **Issue Tracking:** Integration with GitHub issues to contextualize development efforts.
*   **Contextual Retrieval (RAG):** Utilizing dedicated components for loading, chunking, querying, and storing knowledge from diverse sources (wikis, documentation).

The architecture is highly modular, featuring separate modules for API interaction, state management (DB routing), project discovery, change tracking, and user profiling.

## Files in Domain
This platform contains a complex set of files supporting networking, AI logic, utility services, agent definitions, knowledge bases, and UI components.

**Core Application & Entry Points:**
*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py` (Main application entry point)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/main.py`

**Agent Definitions:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` (Base class for agents)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` (Specialized agent for DevOps tasks)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py` (Agent interacting with GitHub issue tracking)

**AI Infrastructure & APIs (`api/artists/agents/...`):**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ai.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/anthropic.py.disabled` (Disabled API integration)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py` (LLM management factory)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py` (Ollama integration)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py` (OpenAI LLM integration)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py`

**API & Service Layers:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/chatGPTLikeApi.py` (Generic chat API wrapper)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/db_router.py` (Database routing logic)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/file_finder.py` (Project file search utility)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py` (GitHub interactions module)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/global_settings.py` (System configuration access)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/users.py` (User authentication and management)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py` (Wiki system interaction)

**Knowledge Retrieval & RAG System:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_splitter.py` (Code chunking)
*   `/home/codx-junior-projects/codx-junior/api/codx-junior/knowledge/knowledge_code_to_dcouments.py` (Code to documentation conversion)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_db.py` (Database management for knowledge base)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py` (DataLoader utility)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py` (Vector database integration point - Milvus)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py` (General text splitting utility)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_wiki.py` (Wiki-specific knowledge integration)

**Context, Session & State Management:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py` (Managing context state)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/db.py` (General database connectivity)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine.py` (The core execution engine)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/model.py` (Socket IO data models)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/session_channel.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/sio.py` (Socket IO handler)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/sio_background.py`

**Project, File & Change Management:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/changes/change_manager.py` (Managing file changes)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/changes/watch_project_file_changes.py` (File change watching service)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/project/project_manager.py` (Project lifecycle management)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py`, `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/utils.py`

**Profiling, Metrics & Specialized Components:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiling/profiler.py` (System performance profiling)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/chat_heatmap.py`, `/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/chat_wall.py` (Usage metrics visualization)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/task_manager.py` (Asynchronous task scheduling)

**Configuration & Assets:**
*   `pyproject.toml` (Project dependencies and configuration)
*   `/home/codx-junior-projects/codx-junior/api/shared/codx-junior/scripts/docker-compose.yaml` (Environment setup script)
*   `/home/codx-junior-projects/codx-junior/api/shared/codx-junior/scripts/traefik/traefik.yaml` (Service mesh configuration)

## Dependencies
(No specific external dependencies were listed in the metadata, but based on functionality, key internal integrations include: **LLM APIs** (OpenAI, Mistral, Ollama, Anthropic), **Vector Databases** (Milvus for advanced RAG), and **Real-time Communication** (SocketIO).)

## Used By
(No files explicitly listing usage were provided in the metadata.)

## Entry Points
The following modules are designated as primary entry points for initializing core functionality:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`