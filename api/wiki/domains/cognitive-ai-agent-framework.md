# Cognitive AI Agent Framework

## Overview
The Cognitive AI Agent Framework provides a comprehensive and robust platform designed for building sophisticated, autonomous, multi-step AI agents. Its core purpose is to abstract away much of the complexity involved in creating highly capable virtual assistants or workflow automation tools driven by Large Language Models (LLMs).

**Key Features:**

*   **Agent Autonomy:** Supports the creation of self-directing agents capable of executing complex objectives via multi-step reasoning and planning.
*   **Knowledge Management (RAG):** Integrates dedicated Retrieval Augmented Generation (RAG) pipelines, allowing agents to manage complex knowledge bases sourced from various data types (documents, code, wikis).
*   **Tool Integration:** Empowers agents by enabling them to utilize external tools and interact with APIs. This includes connectivity with major platforms like GitHub and internal systems like Wikis.
*   **LLM Flexibility:** Provides abstraction layers for integrating multiple LLM backends (`openai`, `ollama`, etc.), ensuring developers are not locked into a single provider.
*   **Context Persistence:** Maintains persistent session context, allowing agents to remember details across extended interactions, crucial for multi-turn dialogues and long-running tasks.

In essence, this framework acts as the brain for advanced AI services within the Codx Junior ecosystem, bridging raw LLM power with practical business logic and deep data integration via explicit tools and knowledge bases.

## Files in Domain
This domain contains a large and modular collection of files, organized logically by functionality:

**Root & Initialization Files:**
*   `api/README.md`: Main documentation page for the API.
*   `pyproject.toml`: Project dependency configuration.

**Agents (Business Logic):**
*   `agents/base_agent.py`: The foundational class implementations for all custom agents.
*   `agents/devops_agent.py`: Specialized agent for DevOps tasks and managing infrastructure details.
*   `agents/git_issues_agent.py`: Agent dedicated to interacting with GitHub/Git issues management APIs.

**AI Backends & Core Logic:**
*   `ai/__init__.py`: Initialization file for the AI backend modules.
*   `ai/llmfactory.py`: Utility responsible for managing and selecting appropriate LLM instances.
*   `ai/openai_ai.py`: Integration layer for OpenAI API calls.
*   `ai/ollama.py`: Integration layer for local Ollama model execution.
*   `ai/utils.py`: General helper functions within the AI module.

**API Integrations (Tools & Connectors):**
*   `api/codx/junior/api/github.py`: Utility and connector for GitHub interactions.
*   `api/codx/junior/api/wiki.py`: Connector specifically designed to interact with internal Wiki systems.
*   `api/codx/junior/api/users.py`: Manages user-related API interaction.
*   `api/codx/junior/api/global_settings.py`: Handles global configuration retrieval and usage.
*   *(Various other API modules like `db_router.py`, `file_finder.py`, `project_search.py`)*.

**Knowledge & RAG Pipelines:**
*   `knowledge/__init__.py`: Initialization for the knowledge module.
*   `knowledge/knowledge_loader.py`: Standardized method for ingesting various data sources (PDFs, docs).
*   `knowledge/knowledge_milvus.py`: Specific integration for vector stores (Milvus).
*   `knowledge/knowledge_splitter.py`: Utility for chunking and segmenting large documents efficiently.
*   `knowledge/knowledge_qa_splitter.py`, `knowledge_code_to_dcouments.py`: Specialized splitters for code and QA data.
*   `knowledge/settings.py`: Configuration specifically related to knowledge base operations.
*   *(Pre-prompts directories establish guidance for document processing: e.g., `code_to_chunks.md`, `extract_document_tags.md`)*.

**Chat & Context Management:**
*   `chat/chat_engine.py`: Handles the main flow of chat interactions and generation.
*   `context.py`: Manages and maintains conversational context history.
*   `chat_manager.py`: Core component for managing multi-turn dialogue state.

**Engines (System Components):**
*   `engine/file_engine.py`: Handles file system operations and search within project files.
*   `engine/git_engine.py`: Manages Git command execution, diffs, and history retrieval.
*   `engine/knowledge_engine.py`: Orchestrates the RAG process (search $\rightarrow$ context injection).
*   `engine/session.py`: Controls agent session state management.

**Utilities & Infrastructure:**
*   `apps/**`: General application entry points (`app.py`, `main.py`).
*   `sio/**/*.py`: Files related to Socket IO for real-time communication between client and server components.
*   `utils/**/*.py`: Generic helper functions (e.g., logging, chat helpers).
*   `task_manager.py`: Handles asynchronous execution of defined tasks or workflows.

## Dependencies
While no explicit file dependencies were provided in the schema, the system relies on a tight architectural dependency graph:

**Architectural Flow:**
1. **Inputs:** Agents (`base_agent.py`, `devops_agent.py`) receive user prompts and context from Chat/API layers.
2. **Execution Core (The Brain):** The request moves through the Conversation context, managed by the Requestor/Chat Manager.
3. **Intent Resolution & Knowledge:** The system determines if external knowledge is needed, triggering the `KnowledgeEngine` which utilizes specialized services like `knowledge_splitter` and vector stores (`milvus`).
4. **Tool Use & Context Gathering:** If a tool call is necessary (GitHub API, Wiki lookup), the request hits the relevant tooling modules (`github.py`, `wiki.py`, `project_tools.py`).
5. **Computation:** The final prompt, enriched with retrieved knowledge and tool outputs, is passed to an abstracted LLM Backend via `llmfactory.py` (e.g., OpenAI or Ollama).

**Conceptual Dependencies:**
*   Agents fundamentally depend on the **AI Backends** (`ai/`) for reasoning.
*   All complex query handling depends on the **Context Management** (`context.py`, `chat_manager.py`).
*   Advanced functionality relies on the robust data integration provided by the **Knowledge Module** (`knowledge/*`).

## Used By
This framework is the foundational layer for several critical applications and external interfaces within the Codx Junior ecosystem:

*   Client front-ends or user interfaces attempting to interact with AI capabilities.
*   The core `app.py` endpoint, which orchestrates incoming requests from users.
*   Any higher-level service that requires automated file reading, code analysis, or structured data retrieval (e.g., CI/CD pipeline integration).

## Entry Points
These files serve as the primary starting points for initializing and executing core agents within the system:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base class for agent definitions.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Entry point for DevOps functionalities.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Gateway for issues tracking agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`