# AI Development Automation Platform

## Overview

This domain provides an advanced, integrated framework designed for AI-powered software development collaboration. It acts as a sophisticated coordination layer, allowing specialized intelligent agents to interact deeply and autonomously with critical developer resources.

The platform's capabilities are highly comprehensive, managing complex workflows across multiple stages, from initial information retrieval (Retrieval Augmented Generation - RAG) against internal knowledge bases to full autonomous task execution in version control systems and codebases. Key components include advanced agent architectures (`devops_agent`, `git_issues_agent`), structured API interfaces for various services (GitHub, Wiki, DB), and a robust system for modular model integration (supporting OpenAI, Astra Anthropic, Ollama, etc.).

This platform aims to drastically accelerate the development lifecycle by combining context awareness (reading project scope, old designs, issues, and documentation) with execution capabilities.

## Files in Domain

### Agents & Core Logic
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` - Base class for all AI agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` - Agent specialized in DevOps tasks and deployment workflows.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py` - Agent designed for managing Git repositories and issues.

### AI Integration & Utilities
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ai_logger.py` - Central logging utility for AI operations.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py` - Factory responsible for integrating various Large Language Models (LLMs).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py` - Integration module for connecting to Ollama local LLM deployments.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py` - Wrapper/client for OpenAI API calls.

### Infrastructure & State Management
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/db.py` - Database connection and interaction layer.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py` - Manages the contextual state of a development session.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/utils.py`

### Networking & API Services
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py` - Handles interactions with GitHub APIs (e.g., fetching commits, issues).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/users.py` - User management API utilities.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py` - Core interface for Wiki interactions, providing knowledge retrieval.

### Knowledge and RAG Implementations
The platform features extensive modules for consuming external knowledge (RAG):
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py` - Responsible for loading diverse data sources.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py` - Tool for segmenting documents into manageable chunks (chunking).
*   (And specialized splitters): `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_splitter.py`, `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_qa_splitter.py`.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py` - Integration layer for vector databases (Milvus).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_wiki.py` - Specific handler for processing Wiki content.

### Project & Workflow Management
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/project/project_manager.py` - Core logic for managing project context and scope.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tasks/task_manager.py` - Module focused on task decomposition and execution management.

## Dependencies

The structure provided does not explicitly list file dependencies, indicating that the framework is highly modular with clean interfaces between components. Its core functionality relies heavily on:

*   **External APIs:** GitHub, designated LLM services (OpenAI, Anthropic), and Vector DBs (Milvus).
*   **Internal Services:** Database connection logic (`db.py`), and State Management (`context.py`).

## Used By

No files were designated as using this domain structure definitionally in the provided input sets. This suggests that the components within this directory are foundational services themselves, used broadly across the application.

## Entry Points

The following Python files act as primary entry points or initializers for key functional modules, allowing external calls to initiate core functionalities:

*   `/home/codx-junior-projects/codx-junior/api/README.md` (Documentation)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py` (AI service initialization)