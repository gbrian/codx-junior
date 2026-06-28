# AI Development Agent Platform

## Overview

This domain serves as an advanced, orchestration layer for comprehensive software development tasks leveraging AI agents. It structures complex workflows by integrating multimodal knowledge bases via Retrieval-Augmented Generation (RAG) from diverse sources like internal code repositories, project documentation, and wiki content.

The platform's core functionality allows specialized, dedicated AI agents to interact with external services. It facilitates multi-step coding solutions, advanced project management functions, and dynamic interaction with tools such as GitHub. Structurally, the domain manages communication flow through messaging queues (Sio), handles user authentication and session context, and provides modular engines for accessing deep knowledge across code, documentation, and collaborative wiki sources, making it a central hub for AI-driven development support.

## Files in Domain

### Core API & Utilities
*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/global_settings.py`
*   `/home/codx-junior-projects/codx-junior/api/backend/app.py`
*   `/home/codx-junior-projects/codx-junior/api/shared/codx-junior/scripts/docker-compose.yaml`
*   `/home/codx-junior-projects/codx-junior/api/shared/codx-junior/scripts/traefik/traefik.yaml`

### Agents and Processors
These files contain the specialized, modular agents that execute tasks:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: The foundational agent class.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Agent for DevOps tasks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Agent specialized in GitHub issues and Git operations.

### AI Model & Local Inference Management (`ai` package)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/anthropic.py.disabled` (Disabled integration)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py`: Utility for accessing multiple LLMs.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py`: Integration with the Ollama local model runner.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py`: Standard OpenAI integration.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py`: General AI utility functions.

### API Endpoints & Services (`api` package)
These modules define interaction points for system features:
*   `api/codx/junior/api/chatGPTLikeApi.py`: Simulated or wrapper API for common LLM endpoints.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/db_router.py`: Routes database interactions.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/file_finder.py`: Manages file searching capabilities.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py`: Direct integration with GitHub API operations.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/global_settings.py` (Duplicate, used by process): System configuration handling.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/users.py`: User management APIs.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py`: API layer for wiki interactions.

### Knowledge Retrieval & RAG System (`knowledge` package)
This suite handles the ingestion, chunking, and querying of diverse data types:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py`: Loads source documents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_to_dcouments.py`: Converts code bases into searchable documentation chunks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_qa_splitter.py`: Specialized splitter for Q&A formats.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py`: General intelligent document chunker.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py`: Integration with Milvus vector database.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_ai_search.py` / `knowledge_ai_search_message.py`: Core AI search logic.

### Messaging, Context & Core Logic
These files handle the underlying operational flow:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py`: Manages conversational and session context.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/db.py`: Database connection and persistence layer.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine.py`: The primary execution engine (Orchestrator).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/events/event_manager.py`: System event handling mechanism.

### Tools & Extensions (`tools` package)
These functions provide specialized capabilities to the agents:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/code_writer.py`: Tool for generating and managing code snippets.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/fetch_webpage.py`: Web scraping tool.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/project_tools.py`: Tools for navigating and manipulating project structure.

### Chat, State Management & Workflow
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_engine.py`: Dedicated engine for dialogue management.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat_manager.py`: Manages chat session state and history.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/model.py`, `sio/session_channel.py`, `sio/sio.py`, `sio/sio_background.py`: WebSocket (SocketIO) implementation for real-time communication.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/task_manager.py`: Coordinates asynchronous task execution.

### Profile Management & User Context (`profiles` package)
Handles various user and role definitions:
*   `/home/codx-junior-projects/codx/junior/api/codx/junior/profiles/agent-coding-task.md`
*   `/home/codx-junior-projects/codx/junior/api/codx/junior/profiles/analyst.profile`
*   `/home/codx-junior-projects/codx/junior/api/codx/junior/profiles/browser.profile`
*   `/home/codx-junior-projects/codx/junior/api/codx/junior/profiles/software_developer.profile`
*   `/home/codx-junior-projects/codx/junior/api/codx/junior/profiles/project.profile`

### Monitoring & Reporting (`metrics` package)
*   `/home/codx-junior-projects/codx/junior/api/codx/junior/metrics/chat_heatmap.py`: Analysis tool for chat usage patterns.
*   `/home/codx-junior-projects/codx/junior/api/codx/junior/metrics/chat_wall.py`: Interface for tracking interaction history ("context wall").

## Dependencies

No explicit dependencies are listed in the provided metadata. The domain functions as a monolithic orchestrator, suggesting that its operational dependencies rely heavily on robust external services (like LLM APIs and vector stores like Milvus) which are integrated via specialized modules (`ai/`, `knowledge/knowledge_milvus.py`).

## Used By

No specific files are listed in the provided metadata that depend upon this entire domain package, suggesting it acts as a core infrastructure layer accessed by top-level entry points (e.g., the front-end client or main startup scripts).

## Entry Points

The following modules serve as primary access points for external interfaces and general use:
*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base class for all executable agents defining the agent framework.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Entry point for managing all AI interactions and API keys.