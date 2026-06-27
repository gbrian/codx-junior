# AI Development Platform

## Overview
The AI Development Platform is an advanced, comprehensive artificial intelligence system designed to streamline and assist software developers across their entire development lifecycle. This platform acts as a central intelligence layer, integrating specialized autonomous agents and robust knowledge retrieval mechanisms.

It provides intelligent guidance, automates complex tasks inherent in the developer workflow, and crucially manages and maintains deep project context. Key functionalities include:

*   **Agent Specialization:** Contains dedicated agents for specific developer concerns like DevOps management (`devops_agent`) and managing GitHub issues/workflow coordination (`git_issues_agent`).
*   **Knowledge Retrieval (RAG):** Implements structured knowledge bases, allowing the system to pull context from multiple sources (wiki articles, code documentation, issue trackers) to ensure responses are accurate, relevant, and grounded in project reality.
*   **Lifecycle Support:** Supports various stages of development, from initial feature planning and coding assistance to deployment management and historical record keeping.

In essence, this platform aims to function as a tireless digital pair programmer and DevOps orchestrator, enhancing developer productivity by providing immediate, context-aware support for every stage of the software creation process.

## Files in Domain
The domain encompasses a vast modular structure covering agents, AI backends, knowledge management, API endpoints, chat functionalities, and infrastructure utilities.

**API & Configuration:**
*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/global_settings.py` (Multiple instances noted)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/settings.py`

**Agents:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`

**AI Integration & Utilities:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ai.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ai_logger.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py`

**API Endpoints & Core Logic:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py` (Main application entry)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/cdb_router.py` (Database routing)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/file_finder.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/users.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/global_settings.py` (Contextual API settings)

**Chat and Context Management:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_engine.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py`

**Knowledge Base (RAG):**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_db.py` (Database interaction)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py` (Document chunking)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py` (Vector store integration)
*   Numerous files related to structured knowledge processing and prompts (`prepromts/*.md`, `*_keywords.py`, etc.)

**Workflow & Project Management:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/changes/change_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/background.py` (Background tasks)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/file_manager/__init__.py`

**Models, Tools, and Utilities:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/code_writer.py` (Code writing tool)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/fetch_webpage.py` (Web access tool)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py`

**Documentation and Testing:**
*   The domain includes extensive documentation in `README.md` files (top level, API, Wiki).
*   Numerous test files for ensuring reliability (`test_*.py`).
*   Infrastructure scripts (`docker-compose.yaml`, `traefik.yaml`).

## Dependencies
*(No explicit dependencies were listed in the input metadata.)*

*As no specific dependencies were provided, further research or inspection of code imports would be required to chart full dependency graphs (e.g., external libraries like LangChain, PineCone, or internal module requirements).*

## Used By
*(No modules directly using this domain were specified in the input metadata.)*

## Entry Points
These files serve as primary starting points for initializing key components of the platform:

*   `/home/codx-junior-projects/codx-junior/api/README.md` (General API documentation)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` (Base class for all agents)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` (DevOps agent logic)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py` (GitHub Issue handling agent)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py` (AI backend initialization)