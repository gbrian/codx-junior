# AI Agent Orchestration Platform

## Overview
The AI Agent Orchestration Platform provides a comprehensive, high-level framework for developing specialized and sophisticated AI agents. Its core function is to orchestrate diverse capabilities by integrating multiple Large Language Models (LLMs). This platform significantly enhances agent functionality beyond basic chat models, allowing them to interact with complex external systems and internal knowledge bases.

**Key Capabilities:**
*   **Multi-LLM Integration:** Seamlessly integrates various LLMs (e.g., OpenAI, Mistral, Ollama) for flexibility and optimal performance depending on the task.
*   **Knowledge Retrieval (RAG):** Provides robust mechanisms to retrieve deep context from internal documents, wikis, and proprietary knowledge stores, ensuring highly grounded responses.
*   **Tool Execution:** Enables agents to interact with external services and APIs by executing defined tools, such as searching GitHub, managing project issues, or running specific code tasks.
*   **Context-Aware Intelligence:** Designed specifically for advanced technical applications, the platform generates deep context-aware intelligence to assist users with complex software development workflows, debugging, and architectural tasks.

The architecture supports modular agent creation (e.g., `devops_agent`, `git_issues_agent`) built on a core base class, promoting reusability and extensibility.

## Files in Domain
### API Layer Core & Utilities
*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/utils.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/global_settings.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/*` (e.g., `analytstics.py`, `knowledge.py`, `db_router.py`, `github.py`, `users.py`)

### Agents System
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`

### LLM & AI Integration
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py`: Central factory for managing connections to different LLM providers.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py`
*(Includes disabled files for Anthropic and Mistral, indicating architectural support.)*

### Knowledge Retrieval (RAG) - The `knowledge` Module
This extensive module handles document ingestion, splitting, embedding, storage, and retrieval.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/*`: Contains logic for chunking (`knowledge_code_splitter.py`), loading, database interaction (`knowledge_db.py`, `knowledge_milvus.py`), and prompt engineering (`knowledge_prompts.py`).
*   Includes specialized ingestion functions: `knowledge_wiki.py` (for wiki content), `knowledge_loader.py`, and various preprompt definitions.

### Tooling & Execution
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/*`: Defines external actions agents can take, such as `code_writer.py` or fetching web content (`fetch_webpage.py`).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/workspace/workspace_manager.py`: Manages the working context for complex tasks.

### Application Logic & Chat Management
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py`, `/home/codx-junior-projects/codx-junior/api/codx/junior/main.py`: Main application entry points.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/*`: Modules for handling the chat flow (`chat_engine.py`, `chat_manager.py`).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py`: Manages conversational and operational context.

## Dependencies
The following domain modules are structurally separated but not explicitly listed with dependency files in the metadata. The platform relies on robust internal packages for its operation, implying a high degree of interdependency between core services:

*   **Knowledge Backend:** Relies heavily on external vector stores (e.g., Milvus) and document processing libraries.
*   **API Handlers:** Depends on specialized clients for GitHub, user management, and wiki systems.
*   **LLM Providers:** Is coupled with multiple LLM SDKs (OpenAI, Mistral, Ollama) managed via the LLMFactory pattern.

## Used By
This platform serves as a foundational engine for:

*   The main application runner (`app.py` / `main.py`).
*   Client-facing chat interfaces that require advanced conversational context and tool use.
*   Internal tooling modules responsible for project discovery, file watching, or analytics reporting.

## Entry Points
These files are designated as primary entry points for utilizing the core agent functionality:

*   `/home/codx-junior-projects/codx-junior/api/README.md` (General Documentation Entry)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base class for creating new, customized agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Specialized agent tailored for DevOps tasks using tools and APIs.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Agent specifically designed to interact with and analyze data from Git issues (e.g., GitHub).