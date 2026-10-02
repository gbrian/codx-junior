# Knowledge & Agent Framework

## Overview
This domain constitutes a sophisticated, advanced framework designed for building highly capable AI-powered software development tools and co-pilots. Its core functionality revolves around unifying specialized agents (such as DevOps, GitHub handlers) with deep context retrieval mechanisms derived from project knowledge bases.

It acts as a central intelligence layer by ingesting information from multiple sources—including active codebases, technical wikis, documentation, and issue trackers—and providing this contextual awareness to various LLM APIs. This allows the system to execute complex, multi-step tasks that mimic highly skilled developer assistance, greatly enhancing development productivity within an integrated environment.

## Files in Domain
### Core Application Logic and Management
*   `api/codx/junior/app.py`: Main entry point for the application logic.
*   `api/codx/junior/main.py`: Primary execution script.
*   `api/codx/junior/global_settings.py`: Centralized settings management across the project.
*   `api/codx/junior/utils/utils.py`: General utility functions for the domain.

### Agent Implementations (Specialized Tools)
These files implement specialized AI agents designed to interact with external services or specific functional areas:
*   `/codx-junior/api/codx/junior/agents/base_agent.py`: The foundational class for all custom agents.
*   `/codx-junior/api/codx/junior/agents/devops_agent.py`: Agent module handling DevOps tasks and workflows.
*   `/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Agent specific for managing GitHub issues and interactions.

### Knowledge Retrieval System (RAG Infrastructure)
This section manages the ingestion, structuring, storage, and retrieval of complex corporate knowledge:
*   `api/codx/junior/knowledge/knowledge_loader.py`: Manages the process of loading raw documentation and data.
*   `api/codx/junior/knowledge/knowledge_splitter.py`: Handles the splitting of large documents into optimized chunks for retrieval.
*   `api/codx/junior/knowledge/knowledge_db.py`: Contains logic for interacting with the underlying knowledge database (e.g., Milvus).
*   `api/codx/junior/knowledge/knowledge_milvus.py`: Specific implementation for vector search using Milvus.
*   `api/codx/junior/knowledge/knowledge_qa_splitter.py`: Specialized splitter for question-answer pairs.
*   `api/codx/junior/knowledge/knowledge_wiki.py`: Module dedicated to processing and integrating wiki content.

### API & Integration Layers
These files provide structured interfaces to various technical systems:
*   `api/codx/junior/api/github.py`: Utility layer for interacting with the GitHub API.
*   `api/codx/junior/api/wiki.py`: Module handling interactions with external wiki systems.
*   `api/codx/junior/api/user_management.py`: Handles user profiles and authentication logic.
*   `api/codx/junior/security/github_oauth.py`: Manages OAuth flow for GitHub integration.

### AI Model Interaction
These files manage the communication with various Large Language Models (LLMs):
*   `api/codx/junior/ai/llmfactory.py`: Factory pattern for creating connections to different LLM APIs.
*   `api/codx/junior/ai/openai_ai.py`: Wrapper for OpenAI API calls.
*   `api/codx/junior/ai/ollama.py`: Wrapper for local Ollama deployments.

## Dependencies
The domain relies heavily on:
*   **External APIs:** GitHub, various LLM providers (OpenAI, Mistral/Anthropic via wrappers), and internal Wiki services.
*   **Vector Stores:** Specialized dependency on a vector database like Milvus (`knowledge_milvus.py`).
*   **Messaging:** Asynchronous communication setup using Socket.IO (Sio for real-time updates).
*   **File/Process System:** Requires robust file system access and monitoring capabilities (`watch_project_file_changes.py`).

## Used By
The entire application structure relies on this framework, suggesting that primary consumer roles include:
*   `api/codx/junior/chat/chat_engine.py`: Uses knowledge engines and agents to power the chat experience.
*   `api/codx/junior/player_manager.py`: Manages session state and user interactions (implied).
*   `README.md` files: Serve as documentation consumption points for users integrating the framework.

## Entry Points
The following files are designated primary entry points for initializing or running core agent logic:
*   `/home/codx-junior-projects/codx-junior/api/README.md` (General Documentation Start)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` (Agent initialization reference).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` (DevOps workflows startup point).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py` (GitHub issue management startup point).