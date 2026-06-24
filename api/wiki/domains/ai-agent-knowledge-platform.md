# AI Agent Knowledge Platform

## Overview
The AI Agent Knowledge Platform is a sophisticated system designed to provide advanced, context-aware assistance by leveraging multiple highly capable specialized AI agents. At its core, the platform acts as an orchestration layer that integrates various Large Language Model (LLM) APIs—including OpenAI, Anthropic, Mistral, and Ollama—to facilitate complex automation tasks.

A major focus of this platform is advanced knowledge retrieval: it manages a robust Retrieval-Augmented Generation (RAG) framework utilizing specialized vector database systems (Milvus). By giving agents specialized roles, tool access, and comprehensive context, the system empowers highly capable automation for intricate development, research, and data processing tasks. It serves as a centralized engine for AI-driven decision support within technical domains.

***

## Files in Domain

The repository structure is modular, with components separated into dedicated utilities, knowledge bases, agents, and core APIs.

**Core API & General Utilities (`api/codx/junior`)**
*   `app.py`: Main application entry point.
*   `main.py`: Primary script/entry point for the application logic.
*   `context.py`: Manages session context and state.
*   `db.py`: Handles database connections and interactions.
*   `engine.py`: Core execution engine managing workflows.
*   `utils/`: General utilities (e.g., `chat_utils.py`, `utils.py`).
*   `api/`: External interface modules (e.g., `global_settings.py`, `users.py`, `wiki.py`).

**AI Model Integration (`ai`)**
This module centralizes connections and wrappers for various LLM providers:
*   `llmfactory.py`: Central factory for managing different LLM implementations.
*   `openai_ai.py`: Wrapper for OpenAI API calls.
*   `ollama.py`: Integration layer for local Ollama models.
*   `anthropic.py.*` / `mistral_ai.py.*`: Disabled/Placeholder wrappers for other major model providers.

**Knowledge & RAG System (`knowledge`)**
This section handles all aspects of data indexing, retrieval, and knowledge enhancement:
*   `knowledge_db.py`, `milvus.py`: Core logic for the vector database and storage orchestration.
*   `knowledge_loader.py`, `knowledge_code_to_dcouments.py`, `knowledge_wiki.py`: Modules responsible for ingesting data from various sources (Wiki, Code).
*   `knowledge_splitter.*`: Utilities like `knowledge_splitter.py` and `knowledge_qa_splitter.py` to preprocess text into optimized chunks.
*   `settings.py`, `knowledge_prompts.py`: Configuration and template management for RAG queries.

**AI Agents & Roles (`agents`)**
These files define specialized, actionable worker modules:
*   `base_agent.py`: Defines the foundational structure for all derived agents.
*   `devops_agent.py`: Specialized agent for DevOps tasks (e.g., infrastructure).
*   `git_issues_agent.py`: Agent focused on interacting with version control and issue tracking APIs.

**Tools & Function Calling (`tools`)**
Defines external capabilities and actions agents can execute:
*   `code_writer.py`: Tool for generating or editing code snippets.
*   `fetch_webpage.py`: Tool for retrieving content from URLs (Web browsing).
*   `project_tools.py`: Toolkit for project-specific interactions.

**Profile & Behaviour Manager (`profiles`)**
Manages the persona and operational scope given to agents:
*   `profile_manager.py`: Core logic for loading and managing different agent profiles.
*   `analyst.profile`, `software_developer.profile`: Example profile definitions establishing context and skill sets.

***

## Dependencies
*(No explicit module dependencies were listed for this summary view.)*

***

## Used By
*(The platform is designed as a massive central system, making the dependency list vast. No specific files relying on this domain were explicitly listed in `used_by_files`.)*

***

## Entry Points
These modules represent critical starting points or independently functional components of the platform:

*   **/home/codx-junior-projects/codx-junior/api/README.md**: General documentation and initial overview for the entire repository.
*   **/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py**: The abstract base class defining the fundamental architecture for any custom AI agent.
*   **/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py**: An entry point demonstrating an actively specialized agent (DevOps) capable of infrastructure tasks.
*   **/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py**: An entry point defining an agent specialized in Git and issue tracker interactions.
*   **/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py**: The initialization point for all AI model wrappers and utility functions, allowing unified access to diverse LLM APIs.