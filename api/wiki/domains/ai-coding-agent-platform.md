# AI Coding Agent Platform

## Overview

The AI Coding Agent Platform is a comprehensive and advanced framework designed to revolutionize software development assistance through artificial intelligence. It functions as an intelligent orchestrator, unifying multiple sophisticated technologies into a cohesive platform for automation and complex task execution.

At its core, this system integrates:
1. **Multiple LLMs:** Seamless connectivity to various Large Language Models (LLM) allows developers to choose the best AI backend for specific tasks (e.g., OpenAI, Mistral, Ollama).
2. **Knowledge Retrieval (RAG):** Advanced Retrieval-Augmented Generation capabilities allow agents to access and utilize proprietary project documentation, wikis, and code bases directly, ensuring contextually accurate assistance.
3. **Specialized Agents:** The platform hosts various specialized agent classes (`DevOpsAgent`, `GitIssuesAgent`) capable of executing complex, multi-step workflows. These agents interact with external tools and APIs to perform real-world development tasks.

By analyzing the project state, managing conversational context, and leveraging dedicated tool APIs (like GitHub interaction or code writing utilities), this platform empowers developers to receive highly contextual, actionable, and sophisticated assistance throughout their entire development lifecycle—from ideation and planning to coding, testing, and deployment.

## Files in Domain

The domain is structured into logical packages covering core agents, AI integrations, knowledge management, toolkits, chat functionalities, and system utilities.

### Core Infrastructure & Utils
*   `api/README.md`: Project documentation.
*   `api/codx/junior/globals.py`: Global configuration settings.
*   `api/codx/junior/settings.py`: System environment settings.
*   `api/codx/junior/utils/utils.py`: General utility functions.
*   `api/shared/codx-junior/scripts/docker-compose.yaml`: Docker deployment configuration file.

### Agents & Logic
*   `api/codx/junior/agents/base_agent.py`: Base class for all AI agents.
*   `api/codx/junior/agents/devops_agent.py`: Agent specialized in DevOps tasks and workflows.
*   `api/codx/junior/agents/git_issues_agent.py`: Agent designed to interact with Git platforms and issue tracking.

### AI Integrations (`api/codx/junior/ai`)
*   `api/codx/junior/ai/__init__.py`: Initialization for the AI module.
*   `api/codx/junior/ai/anthropic.py.disabled`: Placeholder/Disabled client for Anthropic LLM.
*   `api/codx/junior/ai/llmfactory.py`: Centralized factory for managing multiple LLM connections.
*   `api/codx/junior/ai/ollama.py`: Implementation for interfacing with the local Ollama model runtime.
*   `api/codx/junior/ai/openai_ai.py`: Client implementation for OpenAI models.
*   `api/codx/junior/api/chatGPTLikeApi.py`: Generic API wrapper simulating a ChatGPT-like interface.

### Knowledge Management (`api/codx/junior/knowledge`)
The knowledge package handles all aspects of RAG, indexing, and querying project information.
*   `api/codx/junior/knowledge/README.md`
*   `api/codx/junior/knowledge/__init__.py`
*   `api/codx/junior/knowledge/knowledge_loader.py`: Handles ingestion of various data sources.
*   `api/codx/junior/knowledge/knowledge_splitter.py`: Logic for splitting large documents into manageable chunks.
*   `api/codx/junior/knowledge/knowledge_qa_splitter.py`: Specific chunking logic optimized for Question Answering tasks.
*   `api/codx/junior/knowledge/knowledge_milvus.py`: Implementation for connecting to the Milvus vector database.
*   `api/codx/junior/knowledge/knowledge_ai_search.py`, `knowledge_ai_search_message.py`: Classes related to performing advanced AI-driven semantic lookups.
*   `api/codx/junior/knowledge/knowledge_wiki.py`: Handles interaction with wiki content for RAG.
*   *Preparatory Guides:* Includes files like `experience_code_to_dcouments.md`, `extract_query_tags.md`, etc., guiding the knowledge pipeline.

### API Services (`api/codx/junior/api`)
This section contains service wrappers for core platform functionalities:
*   `api/codx/junior/api/github.py`: Handles OAuth and interactions with GitHub APIs.
*   `api/codx/junior/api/users.py`: Module for user management.
*   `api/codx/junior/api/wiki.py`: Manager for the wiki system.
*   `api/codx/junior/api/file_finder.py`: Utility for programmatically finding files within a project structure.

### Chat and Conversational Logic (`api/codx/junior/chat`)
*   `api/codx/junior/chat_manager.py`: Central manager handling chat sessions, history, and context.
*   `api/codx/junior/chat/chat_engine.py`: Core engine responsible for processing user input and generating responses.
*   `api/codx/junior/chat_knowledge.py`: Integration layer to inject knowledge into the chat response pipeline.

### Tools and Utilities (`api/codx/junior/tools`)
Tools define external functionalities agents can use:
*   `api/codx/junior/tools/__init__.py`: Tool module initializer.
*   `api/codx/junior/tools/code_writer.py`: Specialized tool for generating and manipulating code snippets.
*   `api/codx/junior/tools/fetch_webpage.py`: Tool to fetch content from external URLs (Web scraping).
*   `api/codx/junior/tools/project_tools.py`: Wrapper for project-specific system commands or interactions.

### Profiles and Context
*   `api/codx/junior/context.py`: Manages the current state and conversational context.
*   `api/codx/junior/profiles/*`: Directory containing various user, role, and project profile definitions (`developer`, `analyst`, etc.), defining agent personas and access roles.

## Dependencies

*(No explicit dependencies were provided in the manifest.)*

This platform is designed to depend on:
*   **External APIs:** OpenAI, Anthropic, Ollama endpoints for LLM communication.
*   **Databases:** A vector database (e.g., Milvus) for knowledge retrieval and potentially a primary SQL/Redis store for session data (`db.py`).
*   **Version Control Systems:** GitHub or similar platforms via OAuth tokens.

## Used By

*(No explicit usage relationships were provided in the manifest.)*

The core domain classes are consumed by:
*   `api/codx/junior/main.py`: The main entry point for running the application.
*   `api/codx/junior/app.py`: Application initialization logic (likely the FastAPI or Flask instance).
*   `api/codx/junior/task_manager.py`: Orchestrates long-running background tasks and agent executions.

## Entry Points

These are the files designated as primary entry points for the system components:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Defines the core agent interaction structure.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Execution entry for DevOps workflows.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Execution entry for Git/Issue tracking workflows.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Initialization module for AI services.