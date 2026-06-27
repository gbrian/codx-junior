# Intelligent Agent Framework

## Overview
The Intelligent Agent Framework serves as a robust and comprehensive backend system designed for developing sophisticated AI agents and automating complex software development workflows. It acts as an intelligent middleware layer, orchestrating multi-step developer tasks automatically.

This framework is highly modular, integrating various Large Language Models (LLMs) from providers like OpenAI and Anthropic. Its advanced capabilities include:
*   **RAG Knowledge Retrieval:** Utilizing dedicated components for ingesting, managing, and retrieving knowledge from diverse sources (documents, code, wikis).
*   **GitHub Interaction:** Enabling agents to interact with repositories, issues, and pull requests.
*   **Structured Data Management:** Providing tools for handling and interacting with various data types and APIs.

The system facilitates rapid prototyping of AI-powered developer tools by offering specialized agents (e.g., `devops_agent`, `git_issues_agent`) built upon a common base structure.

## Files in Domain
This domain contains files related to agent logic, LLM compatibility, knowledge base management, API integration layers, and core application services:

**API & Core Services:**
*   `/home/codx-junior-projects/codx-junior/api/README.md` (General documentation)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py` (Main application entry point)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/main.py` (General application usage example)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/settings.py` (Configuration management)

**Agents:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` (Base class for all agents)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` (Agent specialized in DevOps tasks)
*   `/home/codx-junior-projects/codx-junior/api/codx-junior/api/codx/junior/agents/git_issues_agent.py` (Agent for GitHub issue management)

**LLM Integration & Utility:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py` (Factory for selecting LLMs)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py` (OpenAI integration layer)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py` (Local Ollama LLM integration)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py` (General AI utilities)

**Knowledge Retrieval (RAG):**
This directory is extensive, supporting various components of a modern RAG pipeline:
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py` (Loading data sources)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py` (Splitting large documents into chunks)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py` (Milvus vector store integration)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_db.py` (Database interaction for knowledge)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_wiki.py` (Wiki specific knowledge handling)
*   Files in `prepromts/`: Logic for enriching documents and setting up context.

**API Clients & Resource Management:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py` (Dedicated GitHub API client)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/users.py`, `/home/codx-junior-projects/codx-junior/api/codx/junior/api/global_settings.py` (User and configuration management)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/file_finder.py`, `/home/codx-junior-projects/codx-junior/api/codx/junior/workspace/workspace_manager.py` (File and workspace context management)

**Chat & Orchestration:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_engine.py` (Core logic for conversational interaction)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py` (Managing conversation state and context window)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine.py`, `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/knowledge_engine.py` (Orchestration engines that coordinate agents and tools)

## Dependencies
*This section is empty, indicating no direct hard dependencies are listed in the domain manifest.*

## Used By
*This section is empty, indicating this framework is likely foundational and used by many external components and services within the larger application structure.*

## Entry Points
These files represent key entry points for external instantiation and use of the agent capabilities:

*   `/home/codx-junior-projects/codx-junior/api/README.md`: General documentation access point.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base class used to initialize and execute all specialized agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: The concrete implementation for managing DevOps workflows, allowing automation of complex development operations.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: A specialized agent for interacting with GitHub issues and pull requests, enabling task management based on code context.