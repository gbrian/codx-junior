# Agentic AI Workflow Engine

## Overview

This domain implements a sophisticated backend infrastructure for complex, agent-driven AI applications. It is designed to move beyond simple Q&A by facilitating structured, multi-step workflows orchestrated by specialized agents.

The core functionality revolves around integrating multiple Large Language Model (LLM) providers and enabling domain-specific agents—such as DevOps or Git management—to perform sophisticated tasks within a development workflow. Crucially, the system incorporates advanced knowledge retrieval (RAG), allowing the AI to search, contextualize, and assist using proprietary content from wikis, project files, and internal documentation, ensuring highly context-aware assistance for technical workflows.

**Key Functionalities:**
*   **Agent System:** Supports specialized agents attached to distinct roles (e.g., `DevOpsAgent`, `GitIssuesAgent`).
*   **LLM Abstraction:** Provides a unified interface (`llmfactory.py`) to interact with various commercial and local LLMs (OpenAI, Mistral, Ollama, Anthropic).
*   **Knowledge Base:** Manages structured retrieval from diverse sources (Wikis, Code Repositories) using RAG pipelines in the `/knowledge` directory.
*   **Workflow Orchestration:** Coordinates interactions between agents, knowledge search, and external tools to complete complex tasks.

## Files in Domain

This section lists all files contained within the Agentic AI Workflow Engine domain structure.

- `api/README.md`
- `api/codx/junior/agents/base_agent.py`: Base class for all specialized agents.
- `api/codx/junior/agents/devops_agent.py`: Specialized agent for DevOps-related tasks.
- `api/codx/junior/agents/git_issues_agent.py`: Agent designed to interact with Git and issue tracking systems.
- `api/codx/junior/ai/__init__.py`
- `api/codx/junior/ai/ai.py`: Core utilities for AI operations (logging, context, etc.).
- `api/codx/junior/ai/anthropic.py.disabled`: Disabled implementation for Anthropic access.
- `api/codx/junior/ai/llmfactory.py`: Factory pattern for managing and selecting different LLM providers.
- `api/codx/junior/ai/mistral_ai.py.disabled`: Disabled implementation for Mistral AI access.
- `api/codx/junior/ai/ollama.py`: Implementation for utilizing models hosted via Ollama.
- `api/codx/junior/ai/openai_ai.py`: Implementation for OpenAI API interaction.
- `api/codx/junior/ai/utils.py`
- `api/codx/junior/api/chatGPTLikeApi.py`: Wrapper or proxy for ChatGPT-like interactions.
- `api/codx/junior/api/db_router.py`: Router responsible for database context and interaction.
- `api/codx/junior/api/file_finder.py`: Utility for locating relevant files within a project.
- `api/codx/junior/api/github.py`: Handles interactions with GitHub APIs.
- `api/codx/junior/api/global_settings.py`: Global configuration settings for the application.
- `api/codx/junior/api/users.py`: Manages user authentication and profiles.
- `api/codx/junior/api/wiki.py`: Main interface for interacting with wiki data sources.
- `api/codx/junior/app.py`: Core application initialization point (likely the FastAPI/Flask app).
- `api/codx/junior/changes/watch_project_file_changes.py`: Watches and processes changes in project files.
- `api/codx/junior/chat/chat_engine.py`: Engine for high-level chat processing and orchestration.
- `api/codx/junior/chat/chat_export.py`
- `api/codx/junior/chat_manager.py`: Manages the state and context of ongoing conversations.
- `api/codx/junior/context.py`: Handles persistent chat context memory within sessions.
- `api/codx/junior/db.py`: Database connection and basic CRUD operations setup.
- `api/codx/junior/engine.py`: Core workflow engine managing overall task flow.
- `api/codx/junior/events/event_manager.py`: System for broadcasting and handling application events.
- `api/codx/junior/file_manager/__init__.py`
- `api/codx/junior/globals.py`: Global variables and constants.
- `api/codx/junior/knowledge/README.md`: Documentation for the knowledge retrieval module.
- `api/codx/junior/knowledge/__init__.py`
- `api/codx/junior/knowledge/knowledge_code_splitter.py`: Splits code blocks into manageable chunks for RAG.
- `api/codx/junior/knowledge/knowledge_code_to_dcouments.py`: Converts raw code structures into searchable documents.
- `api/codx/junior/knowledge/knowledge_db.py`: Wrapper for interacting with the backend knowledge database (e.g., vector store).
- `api/codx/junior/knowledge/knowledge_keywords.py`: Handles keyword extraction and indexing for context enrichment.
- `api/codx/junior/knowledge/knowledge_loader.py`: Loads varied data types (PDF, markdown, etc.) into the system.
- `api/codx/junior/knowledge/knowledge_milvus.py`: Specific implementation using Milvus vector database.
- `api/codx/junior/knowledge/knowledge_prompts.py`: Manages structured prompts for RAG enhancement.
- `api/codx/junior/knowledge/knowledge_qa_splitter.py`: Specialized splitter optimized for Question-Answer pairs.
- `api/codx/junior/knowledge/knowledge_splitter.py`: General utility module for content chunking.
- `api/codx/junior/knowledge/knowledge_training.py`: Handles the ingestion and training pipeline for new knowledge.
- `api/codx/junior/knowledge/knowledge_wiki.py`: Specific logic for parsing and querying wiki formats.
- `api/codx/junior/knowledge/prepromts/code_to_chunks.md`: Preprompt instructing how to chunk code.
- `api/codx/junior/knowledge/prepromts/enrich_document.md`: Preprompt template for document enrichment.
- `api/codx/junior/knowledge/prepromts/extract_document_tags.md`: Preprompt for extracting metadata from documents.
- `api/codx/junior/knowledge/prepromts/extract_query_tags.md`: Preprompt for refining user queries with tags.
- `api/codx/junior/knowledge/settings.py`: Knowledge module specific settings and constants.
- `api/codx/junior/log_parser.py`: Parses system logs to extract actionable insights.
- ... (and remaining files in similar structure)

## Dependencies

The following modules, classes, or domains rely on the components provided by this domain:

*   `api/codx/junior/utils/chat_utils.py`
*   `api/codx/junior/model/wallet.py` (Indicates core system models are used)

## Used By

This domain provides foundational building blocks and specialized APIs that are consumed by multiple parts of the application:

*   `api/codx/junior/main.py`: The main entry point, which initializes and orchestrates workflow using all agents and knowledge components.
*   The entire chat ecosystem (`chat_manager.py`, `chat_engine.py`) relies on the specialized knowledge retrieval (RAG) and agent services for context generation.

## Entry Points

These files are designated as primary entry points for external or internal calls, defining how the system's core functionality can be accessed programmatically.

- `/home/codx-junior-projects/codx-junior/api/README.md`
- `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Starting point for creating custom agents.
- `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
- `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
- `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Initialization of the AI component wrapper.