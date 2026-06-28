# Intelligent Agent Framework

## Overview

This domain provides a robust framework for creating and managing specialized AI agents. It integrates various LLM APIs to power agents that can execute complex tasks, utilizing tools for project interaction, knowledge retrieval (RAG), and system automation. The core purpose is to act as an autonomous developer assistant automating entire software development lifecycles.

The framework encompasses multiple components crucial for advanced AI functionality, including:
*   **Agent Management:** Classes like `base_agent.py`, `devops_agent.py`, and `git_issues_agent.py` provide structured ways to define specialized behaviors.
*   **LLM Abstraction:** Modules within the `ai/` directory (`openai_ai.py`, `ollama.py`, `llmfactory.py`, etc.) abstract connections to various Language Model APIs, ensuring flexibility and portability.
*   **Knowledge Retrieval (RAG):** The `knowledge/` subdirectory handles document ingestion, splitting, embedding, and retrieval (e.g., using Milvus), forming the backbone of context-aware assistance.
*   **System Interaction:** Tools for managing codebase changes (`file_manager`), interacting with external services (GitHub APIs), and maintaining state (`db`, `context`) are provided.

This architecture is designed to enable complex, multi-step operations ranging from reading project structure and analyzing requirements to writing code, submitting pull requests, and managing project artifacts independently.

## Files in Domain

The domain contains a comprehensive set of files covering agent logic, API integrations, knowledge ingestion pipelines, system utilities, and core application components:

### Core Functionality & Agents
*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`

### LLM API Wrappers (`ai/`)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ai_logger.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/anthropic.py.disabled`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/mistral_ai.py.disabled`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py`

### API Integration Layer (`api/`)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/chatGPTLikeApi.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/db_router.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/file_finder.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/global_settings.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/users.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py`

### Core System & Manager Modules
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py` (Main application entry point)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/changes/watch_project_file_changes.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_engine.py` (Chat conversation logic)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_export.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py` (State management)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/db.py` (Database handling)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine.py` (Core execution engine)

### Knowledge Retrieval (`knowledge/`)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_splitter.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_to_dcouments.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_keywords.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py` (Vector storage)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_prompts.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_qa_splitter.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_training.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_wiki.py` (Wiki source ingestion)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/code_to_chunks.md` (Prompts/Templates)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/enrich_document.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/extract_document_tags.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/extract_query_tags.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/settings.py`

### Logging, Monitoring, and Utilities
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/log_parser.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/main.py` (Main client entry point)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/mentions/mention_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/chat_heatmap.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/chat_wall.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/codx_junior_metrics.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/misc/github.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/model.py`, `/home/codx-junior-projects/codx-junior/api/codx/junior/model/user.py`, `/home/codx-junior-projects/codx-junior/api/codx/junior/model/wallet.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/plugins/plugin_manager.py`

### Profile & Project Management
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/agent-coding-task.md` & Associated profiles (`analyst.profile`, `software_developer.profile`, etc.)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/profile_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/project/project_discover.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/project/project_manager.py`

### Security & Networking
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/security/github_oauth.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/security/user_management.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/settings.py`

### WebSocket (Sio) Implementation
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/model.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/session_channel.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/sio.py` (WebSocket server core)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/sio_background.py`

### Tools & Utilities
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/code_writer.py` (Code manipulation tool)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/fetch_webpage.py` (Web browsing tool)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/project_tools.py` (Project structure interactions)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py`, `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/utils.py`

### Wiki Documentation (`wiki/`)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/model.py`, `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_manager.py`

### Infrastructure & Testing
*   `/home/codx-junior-projects/codx-junior/api/pyproject.toml`: Project configuration file.
*   `/home/codx-junior-projects/codx-junior/api/shared/codx-junior/scripts/docker-compose.yaml`: Deployment configuration.
*   Paths under `/api/tests/`: Testing files for components like `chat`, `db`, and `mention_manager`.

## Dependencies

No explicit external file dependencies were listed. The framework, however, relies heavily on:
1.  **LLM APIs:** OpenAI, Anthropic, Ollama (via helper modules).
2.  **Vector Database:** Milvus (for specialized knowledge storage).
3.  **Realtime Messaging:** WebSocket/SocketIO (for system state updates and chat streaming).

## Used By

No files were listed as dependencies. This domain represents a self-contained, foundational core providing services to other applications or entry points.

## Entry Points

These modules serve as the primary starting points for utilizing the agent framework:
*   `/home/codx-junior-projects/codx-junior/api/README.md`: General API documentation access point.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base class for custom AI agent development.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Specialized agent for DevOps tasks (e.g., deployment, system health checks).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Agent focused on GitHub interaction and issue management.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Primary entry point for LLM API wrapper initialization and selection.