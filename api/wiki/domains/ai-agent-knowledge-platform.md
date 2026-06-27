# AI Agent & Knowledge Platform

## Overview
This domain represents a core module cluster designed to provide a robust API framework for advanced, intelligent software assistance. It is built upon an architecture that coordinates specialized, modular agents (such as DevOps and Git issues trackers) with integrated knowledge bases.

The primary function of the platform is to facilitate complex interactions by:
1.  **Agent Coordination:** Managing specialized task execution via dedicated agents.
2.  **Context Management:** Handling chat sessions, maintaining state, and managing context across multi-step conversations.
3.  **Knowledge Retrieval (RAG):** Leveraging multiple knowledge sources (e.g., defined wiki content, code documentation) through advanced retrieval methods.
4.  **LLM Abstraction:** Providing a unified interface to interact with various Large Language Model providers (OpenAI, Anthropic, Mistral, Ollama, etc.), ensuring flexibility and scalability.

The platform is highly interconnected, covering aspects from project management (`project/`) to chat interactions (`chat/`), security (`security/`), and content indexing (`knowledge/`).

## Files in Domain
### Core API & Execution Logic
* `/home/codx-junior-projects/codx-junior/api/README.md`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py` (Main application entry point)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/main.py`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/engine.py` (Engine coordination logic)

### Agents & Specialized Tools
These files define the AI agents and specialized tools that perform actions against external systems or internal data silos.
* `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` (Base class for all agents)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` (DevOps task automation agent)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py` (GitHub Issue management agent)

### AI Model & Integration Layers (`ai/`)
This section handles the logic for interacting with various LLM providers and utility functions.
* `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py` (LLM provider abstraction)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/anthropic.py.disabled`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/mistral_ai.py.disabled`

### Knowledge Base & RAG (`knowledge/`)
The most extensive part, dedicated to ingesting, chunking, retrieving, and utilizing external knowledge documents (RAG).
* `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/README.md`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/__init__.py`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py` (Document ingestion)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py` (General document chunking logic)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_qa_splitter.py` (Specialized Q&A splitting)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_db.py` (Database interaction)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py` (Vector database implementation)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_splitter.py` / `knowledge_code_to_dcouments.py` (Code specific handling)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_wiki.py` / `knowledge_training.py` (Source-specific processing)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/settings.py`
* *Preprompt Logic:* (`prepromts/`) Handles detailed prompt generation for specific knowledge types.

### Chat & Context Management
* `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_engine.py` (Core chat execution logic)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/chat_manager.py` (State management for sessions)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py` (Contextual data storage and retrieval)

### Project & Data APIs (`api/`)
These files handle specific interfaces to external sources or internal services.
* `/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py` (GitHub API wrapper)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/api/users.py`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py` (Wiki management API)
* `/home/codx-junior-projects/codx-junior/api/codx/junior/api/global_settings.py`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/api/file_finder.py` (File system search)

### Profile, Model & Utilities
* `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/profile_manager.py`: Handles user and context profiles.
* `/home/codx-junior-projects/codx-junior/api/codx/junior/model/model.py`: Core data structures and models.
* `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/utils.py`

## Dependencies
The platform has numerous implicit functional dependencies across modules, but structured dependencies are not explicitly defined in the provided metadata fields (`depends_on_files`).

Functionally, key components rely on:
* **Knowledge Base:** The `chat/chat_engine.py` depends heavily on `knowledge/knowledge_loader.py`, `knowledge/knowledge_splitter.py`, and `knowledge/knowledge_db.py` to provide grounded responses.
* **LLM Integration:** Most services depend on the LLM abstraction layer (`ai/llmfactory.py`) for text generation capabilities.
* **State Management:** Chat features rely on `context.py` and `chat_manager.py` to maintain conversational history and state.

## Used By
The metadata did not specify files that use this domain's components (`used_by_files`). Given its nature as a core API, it serves as the central backend layer for any client or application consuming intelligent features within the entire project structure.

## Entry Points
These files are designated as primary entry points for initial module loading and testing:
* `/home/codx-junior-projects/codx-junior/api/README.md`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
* `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`