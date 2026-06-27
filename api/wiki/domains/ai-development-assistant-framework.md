# AI Development Assistant Framework

## Overview

The AI Development Assistant Framework is an intelligent platform designed to provide automated and comprehensive support for modern software development workflows. It acts as a central hub, abstracting complexity by integrating various state-of-the-art capabilities: Large Language Model (LLM) access, specialized AI agents, version control systems (Git), and advanced structured knowledge retrieval.

This framework enables the execution of complex, multi-step developer tasks—ranging from context-aware coding assistance to managing project lifecycles via CI/CD actions—all within a unified API structure. By connecting modular agents (`devops_agent`, `git_issues_agent`) with robust tooling and an expansive knowledge base (RAG implementation), it aims to dramatically reduce the friction inherent in enterprise-level software development processes.

**Key Areas of Functionality:**
*   **LLM Management:** Provides wrappers for multiple AI providers (OpenAI, Mistral, Ollama) ensuring flexible LLM backend integration.
*   **Agent System:** Defines specialized agents capable of acting on behalf of the user (Code Writing, DevOps management, Git Operations).
*   **Knowledge Retrieval (RAG):** Structures unstructured data (wikis, documents, code chunks) into a searchable knowledge base using vector stores (Milvus).
*   **Workflow Automation:** Manages complex task execution and context flow throughout an entire development session.

## Files in Domain

Due to the large number of files, they are categorized by their function within the framework structure.

### 🚀 Agents & Specialized Tools
This directory contains logic for specialized AI agents that perform specific developer tasks.
*   `codx/junior/agents/base_agent.py`: Blueprint for all custom agents.
*   `codx/junior/agents/devops_agent.py`: Agent specialized in deployment, CI/CD, and infrastructure management.
*   `codx/junior/agents/git_issues_agent.py`: Agent focused on Git operations and issue tracking integration.

### 🧠 AI Core & LLM Integrations
These modules handle the interaction with various Large Language Models (LLMs) and general API utilities.
*   `codx/junior/ai/llmfactory.py`: Factory class for managing different LLM backend connections.
*   `codx/junior/ai/openai_ai.py`: Implementation wrapper for OpenAI APIs.
*   `codx/junior/ai/ollama.py`: Integration module for running local AI models via Ollama.
*   *(Disabled files: `anthropic.py`, `mistral_ai.py`)*

### 📜 Knowledge Base (RAG) Managment
Modules governing the ingestion, chunking, storage, and retrieval of project context from various sources.
*   **Processors:**
    *   `codx/junior/knowledge/knowledge_splitter.py`: Handles generic text/code segmentation.
    *   `codx/junior/knowledge/knowledge_qa_splitter.py`: Specialized splitter for question-answer pairs.
    *   `codx/junior/knowledge/knowledge_code_splitter.py`: Code-specific chunking utility.
    *   `codx/junior/knowledge/knowledge_loader.py`: Responsible for reading and loading data sources.
*   **Persistence:**
    *   `codx/junior/knowledge/knowledge_db.py`: Core database interaction logic.
    *   `codx/junior/knowledge/knowledge_milvus.py`: Specific integration layer for the Milvus vector database.

### ⚙️ Core Engines & Workflow Orchestration
These modules are responsible for running complex tasks and managing state across agents, APIs, and knowledge sources.
*   `codx/junior/engine/git_engine.py`: Direct interaction with Git functionality (branching, commits).
*   `codx/junior/engine/knowledge_engine.py`: Orchestrates the retrieval process using knowledge components.
*   `codx/junior/engine/session.py`: Manages the conversational and task context of a development session.
*   `codx/junior/tools/code_writer.py`: Primary tool for suggesting, writing, and modifying code.
*   `codx/junior/tools/project_tools.py`: General tools wrappers for project-level operations (e.g., running commands).

### 🌐 API Services & State Management
These files expose the framework's capabilities through dedicated APIs.
*   **File/Project:**
    *   `codx/junior/api/file_finder.py`: Utility to locate specific files within a codebase.
    *   `codx/junior/api/project_manager.py`, `codx/junior/api/project_search.py`: Logic for understanding and navigating project structures.
*   **User & Identity:**
    *   `codx/junior/api/users.py`: User profile retrieval and management.
    *   `codx/junior/security/github_oauth.py`: Handling GitHub authentication flow.
*   **API Abstraction:**
    *   `codx/junior/api/codx/junior/chat/chat_engine.py`: The primary entry point for multi-turn conversational logic.
    *   `codx/junior/api/codx/junior/context.py`: Manages and retrieves the current operational context.

### 🔬 Testing, Infrastructure & Utilities
Files dedicated to testing, setup, logging, and general utilities.
*   **Utilities:**
    *   `codx/junior/utils/chat_utils.py`, `codx/junior/utils/utils.py`: General purpose helper functions.
    *   `codx/junior/log_parser.py`: Utility for analyzing development logs.
*   **Metrics & Monitoring:**
    *   `codx/junior/metrics/*`: Modules designed to track usage, heatmaps, and performance metrics.
*   **Internal Setup:**
    *   `shared/scripts/docker-compose.yaml`: Containerization definition for the environment.

## Dependencies

No explicit dependencies were listed in `<depends_on_files>`. However, based on file structure, this framework relies heavily on:
*   Python standard libraries (e.g., `os`, `json`).
*   External SDKs for LLM Providers (e.g., OpenAI client, Anthropic API library).
*   Vector Database Clients (e.g., Milvus or Pinecone SDK).
*   Networking/Communication Libraries (Implied by use of `sio` modules, suggesting WebSocket communication).

## Used By

No files were explicitly listed in `<used_by_files>`. This framework is designed to be the core backend service for a client application or specialized orchestration layer.

## Entry Points

These are the primary callable points that initiate agent workflows and core functionalities:

*   `/home/codx-junior-projects/codx-junior/api/README.md` (Documentation entry point)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base class for developing new specialized agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Entry point for DevOps automation tasks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Entry point for version control and issue management workflows.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Initialization module for AI services.