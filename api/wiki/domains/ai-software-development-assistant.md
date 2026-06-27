# AI Software Development Assistant

## Overview

This framework acts as an intelligent coding assistant, integrating multiple Large Language Models (LLMs) with deep project context knowledge and proprietary organizational data. It provides robust tooling for autonomous agents to perform complex tasks such as code generation, debugging, documentation updating, and workflow automation through specialized modules like Knowledge Retrieval and DevOps integration. The system is designed to mimic a sophisticated pair-programming experience, combining advanced AI capabilities (OpenAI, Mistral, Ollama) with structured project management tools (Git, Wiki, Project Tracking).

## Files in Domain

The domain structure can be broadly categorized by functionality: Agents, Core APIs, Knowledge Retrieval, Chat/Context Management, Models, and Utilities.

### 📂 Main Application & Core Logic
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py` (Main application entry point)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/main.py`
*   `/home/codx-junior-projects/codx-junior/README.md`

### 🤖 Agents & Automation
These modules house specialized agents capable of executing complex developer workflows:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` (Base class for agents)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` (Agent for DevOps tasks)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py` (Agent for Git and Issue management)

### 🧠 LLM & AI Integration
These files handle the connection and abstraction of various Large Language Models:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ai.py` (Main AI wrapper)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py` (Factory for LLMs)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py`

### 📚 Knowledge & Context Management (RAG Components)
These modules facilitate proprietary data ingestion and retrieval for grounding AI responses:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py` (Loads source data)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_to_dcouments.py` (Specialized document conversion)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_db.py` (Database interaction layer)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py` (Vector store integration)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_qa_splitter.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/settings.py`

### 💬 Chat, Context, & Interaction
These files manage the user interaction and conversational state:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py` (Manages session context)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_engine.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_knowledge.py` (Integrating knowledge into chat)

### 🔨 Core APIs & Tools
These files implement specialized domain interactions:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py` (GitHub integration)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/file_finder.py` (File searching utility)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/utils.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/code_writer.py` (Code generation tool)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/fetch_webpage.py` (Web browsing tool)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py`

### 📜 Profiles, Settings, & Utilities
General utility and profile definition files:
*   `/home/codx-junior-projects/codx-junior/api/shared/codx-junior/scripts/docker-compose.yaml` (Deployment configuration)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/settings.py` (Application settings management)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/*` (Various Agent and Personas profiles, e.g., `analyst.profile`, `software_developer.profile`)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/task_manager.py`

***

## Dependencies

The following files are listed as primary entry points and dependencies, suggesting the core modules responsible for initiating or configuring services:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`

## Used By

*(No files listed in the provided metadata indicating usage)*

## Entry Points

The following scripts are designated as primary entry points, defining core functional modules:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`