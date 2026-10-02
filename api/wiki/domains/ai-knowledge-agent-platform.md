# AI Knowledge Agent Platform

## Overview
This comprehensive backend serves as an API platform for an intelligent developer assistant. It is designed to orchestrate specialized agents—such as DevOps and Git issue management—and utilizes various Large Language Models (LLMs) to process complex tasks. The platform's core functionalities include managing proprietary knowledge bases, fetching contextual information from diverse sources (wiki, code repositories), facilitating advanced chat interactions, and enabling automated actions across development workflows (like watching project file changes). It provides a highly structured backend for integrating AI intelligence into developer tools, covering aspects like resource management, state handling, logging, and metric tracking.

## Files in Domain
The domain encompasses a wide range of modules critical for interaction, knowledge representation, agent logic, and infrastructural services.

**API and Core Logic:**
*   `README.md`
*   `codx/junior/app.py` (Main application entry point)
*   `codx/junior/api/global_settings.py`
*   `codx/junior/core/utils/*` (Various utility functions and definitions)
*   `codx/junior/db.py`, `codx/junior/sio/*` (Database handling and Socket.IO communications)

**AI Integration & Models:**
*   `codx/junior/ai/llmfactory.py` (Central LLM initialization)
*   `codx/junior/ai/openai_ai.py`
*   `codx/junior/ai/ollama.py`
*   `codx/junior/knowledge/*` (Knowledge loading, splitting, and querying modules: `knowledge_qa_splitter.py`, `knowledge_loader.py`, etc.)

**Agents & Tools:**
*   `codx/junior/agents/base_agent.py` (Abstract Agent base class)
*   `codx/junior/agents/devops_agent.py` (Agent for DevOps tasks)
*   `codx/junior/agents/git_issues_agent.py` (Agent for Git issue management)
*   `codx/junior/tools/*` (Tools for code writing, web fetching, and project interactions)

**Context & Persistence:**
*   `codx/junior/context.py` (Handles state management during chat sessions)
*   `codx/junior/profiles/*` (Manages user/system profiles like `analyst.profile`, `coding_profiles.json`)
*   `codx/junior/knowledge/README.md`

**Utilities, Managers & Services:**
*   `codx/junior/chat/*` (Logic for chat flow and knowledge integration: `chat_engine.py`, `chat_manager.py`)
*   `codx/junior/project/*` (Project discovery and management logic)
*   `codx/junior/wiki/*` (Wiki interaction modules: `wiki_manager.py`)

***
Available files include:
```
/home/codx-junior-projects/codx-junior/api/README.md
/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py
/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py
/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py
/... (and all other files listed in the source data)
```

## Dependencies
No explicit dependencies were provided for this domain.

## Used By
No modules or services explicitly use this domain, as it appears to serve as a highly comprehensive API layer itself.

## Entry Points
The primary entry points initiating agent logic and core functionality are:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` (Foundation for agents)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` (DevOps agent functionality entry point)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py` (Git issues management entry point)