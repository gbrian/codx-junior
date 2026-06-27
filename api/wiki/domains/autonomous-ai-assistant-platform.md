# Autonomous AI Assistant Platform

## Overview
The Autonomous AI Assistant Platform is an advanced, multi-modal system built to serve as a sophisticated aid in augmenting and automating modern software development workflows. This platform acts as a unified interface that enables users to interact with specialized AI capabilities without needing deep knowledge of underlying services or APIs.

**Key Functionalities:**

*   **AI Specialization:** It integrates multiple specialized agents (e.g., `devops_agent`, `git_issues_agent`) allowing the system to execute complex, role-specific tasks.
*   **Multi-Modal Capabilities:** The platform supports various inputs and outputs, including code generation, natural language interaction, web data processing, and understanding from audio inputs (via Whisper components).
*   **Deep Knowledge Retrieval (RAG):** It incorporates a comprehensive knowledge base management system (`knowledge/`) allowing it to process, store, and retrieve context from technical documentation, wikis, and project files.
*   **LLM Agnostic:** By utilizing a centralized `llmfactory`, the platform supports interaction with multiple leading LLM providers (OpenAI, Mistral, Ollama, Anthropic), ensuring flexibility and resilience.
*   **Contextual Awareness:** The system maintains awareness of the current project context, user profiles, global settings, and external APIs (GitHub, Wikis).

In essence, this platform transforms raw information access into actionable intelligence, dramatically speeding up coding cycles, debugging processes, and overall development operational tasks.

## Files in Domain
The following files comprise the domain's codebase:

**/home/codx-junior-projects/codx-junior/api/**
*   `README.md`
*   **Code & Logic:**
    *   `/api/codx/junior/app.py`: Main application entry point and orchestration layer.
    *   `/api/codx/junior/main.py`: Core runnable script for the service.
    *   `/api/codx/junior/engine.py`: Central logic engine coordinating various AI services.
    *   `/api/codx/junior/context.py`: Manages and stores conversational and operational context.
    *   `/api/codx/junior/db.py`: Handles database interactions and session management.
    *   `/api/codx/junior/utils/chat_utils.py`
    *   `/api/codx/junior/utils/utils.py`
    *   `/api/codx/junior/log_parser.py`: Utility for parsing system logs.
    *   `/api/codx/junior/global_settings.py` (Used as general configuration)
    *   `/api/codx/junior/globals.py` (Global state management)
*   **API Integrations:**
    *   `/api/codx/junior/api/chatGPTLikeApi.py`: Wrapper for OpenAI-style API calls.
    *   `/api/codx/junior/api/db_router.py`: Routes specialized database queries.
    *   `/api/codx/junior/api/file_finder.py`: Locates and indexes project files.
    *   `/api/codx/junior/api/github.py` & `/api/codx/junior/api/misc/github.py`: Handles GitHub integrations (OAuth, fetching data).
    *   `/api/codx/junior/api/users.py`: Manages user-related services and profiles.
    *   `/api/codx/junior/api/wiki.py` & `/api/codx/junior/api/knowledge.py`: Interface definitions for Wiki and Knowledge Base interactions.
*   **Agents:**
    *   `/api/codx/junior/agents/base_agent.py`: Abstract base class for all specialized agents.
    *   `/api/codx/junior/agents/devops_agent.py`: Agent handling DevOps tasks (deployment, monitoring).
    *   `/api/codx/junior/agents/git_issues_agent.py`: Agent for interacting with Git repository issues.
*   **AI Model Handling (`ai/`):**
    *   `/api/codx/junior/ai/__init__.py`: Initialization package for AI services.
    *   `/api/codx/junior/ai/llmfactory.py`: Factory responsible for selecting and initializing different LLM providers.
    *   `/api/codx/junior/ai/openai_ai.py`, `/api/codx/junior/ai/ollama.py`, (and disabled modules like `anthropic.py` and `mistral_ai.py`): Implementations for various AI Model APIs.
*   **Knowledge Management (`knowledge/`):**
    *   `/api/codx/junior/knowledge/__init__.py`: Initialization package for knowledge processes.
    *   `/api/codx/junior/knowledge/knowledge_loader.py`: Loads raw documents (Markdown, files).
    *   `/api/codx/junior/knowledge/knowledge_splitter.py`: Splits large chunks of text into manageable pieces.
    *   `/api/codx/junior/knowledge/knowledge_db.py` & `/knowledge/knowledge_milvus.py`: Handles structured storage and vector database interactions for RAG.
    *   `/api/codx/junior/knowledge/knowledge_qa_splitter.py`: Specialized splitter for Question Answering workflows.
    *   *(Multiple specialized knowledge files for tagging, enrichment, etc.)*
*   **Workflow & Tools:**
    *   `/api/codx/junior/tools/__init__.py`: Entry point for external tools.
    *   `/api/codx/junior/tools/code_writer.py`: Tool for generating and modifying code snippets.
    *   `/api/codx/junior/tools/fetch_webpage.py`: Tool for web scraping and gathering live data.
    *   `/api/codx/junior/workspace/workspace_manager.py`: Manages the current working environment state.
*   **Profiles & Settings:**
    *   `/api/codx/junior/profiles/profile_manager.py` / `/api/codx/junior/models/user.py`: Logic for managing user context and professional profiles (e.g., `software_developer.profile`).
    *   `/api/codx/junior/metrics/chat_wall.py`, etc.: Modules dedicated to collecting and analyzing usage metrics.

## Dependencies
*(Based on the provided metadata, there are no explicit external dependencies marked for this domain.)*

**None listed.** The platform's design suggests it interacts with many services (LLM APIs, GitHub, Databases), but these interactions are handled via internal service wrappers rather than being listed as hard dependencies within `depends_on_files`.

## Used By
*(Based on the provided metadata, there are no consumer files marked for this domain.)*

**None listed.** This domain appears to serve as a core backend API suite, meaning it is intended to be consumed by other services (e.g., a frontend Web UI or a CLI tool), but no specific calling modules were identified in `used_by_files`.

## Entry Points
These files represent the primary starting points or service registration paths for this domain:

*   `/home/codx-junior-projects/codx-junior/api/README.md` (Documentation)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`