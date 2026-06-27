# AI Coding Assistant Platform

## Overview
The AI Coding Assistant Platform provides a comprehensive, agentic framework designed to revolutionize software development and knowledge retrieval experiences. It moves beyond simple chat interfaces by empowering generative AI models to interact with deep, complex context across multiple sources:

*   **File Systems:** Accessing the current project structure and code base depth.
*   **Version Control Data (Git):** Analyzing commit histories, diffs, and issue tracking integration.
*   **Internal Wikis/Knowledge Bases:** Retrieving specialized domain knowledge and accumulated company best practices.

The system supports advanced capabilities including:
*   **Specialized Agents:** Pre-configured agents (e.g., DevOps Agent, Git Issues Agent) for specific development roles.
*   **Advanced Prompt Engineering:** Tools to structure complex instructions and context injection.
*   **Tool Usage:** Enabling the AI to execute external functions and interact with system APIs to automate tasks and guide human developers effectively.

This platform is built to manage highly complex multi-step coding tasks, making it a central intelligence layer for development teams.

## Files in Domain
The project file structure contains components related to API infrastructure, agent definitions, knowledge management (`knowledge`), chat logic, project lifecycle management, models, and utilities.

### Core API & Structure
*   `api/README.md`
*   `api/codx/junior/app.py`: Main application entry point wrapper.
*   `api/codx/junior/main.py`: Primary operational script.
*   `api/codx/junior/settings.py`, `global_settings.py`: Configuration and settings management.

### Agents & Profiles
This section manages specialized AI behaviors and user roles.
*   `api/codx/junior/agents/base_agent.py`: Base class for all specialized agents.
*   `api/codx/junior/agents/devops_agent.py`: Agent focused on DevOps/infrastructure tasks.
*   `api/codx/junior/agents/git_issues_agent.py`: Dedicated agent for GitHub issue management.
*   `api/codx/junior/profiles/profile_manager.py`: Handles user and profile definition logic.
*   `api/codx/junior/profiles/*.profile`, `*.profile.md`: various role definitions (e.g., Analyst, Software Developer).

### AI Model Integration (`ai/`)
This directory handles the connections to various LLMs.
*   `api/codx/junior/ai/__init__.py`
*   `api/codx/junior/ai/llmfactory.py`: Central factory for model initialization.
*   `api/codx/junior/ai/openai_ai.py`: OpenAI integration helper.
*   `api/codx/junior/ai/ollama.py`: Ollama local model integration.
*   `api/codx/junior/ai/utils.py`, `anthropic.py.disabled`, `mistral_ai.py.disabled`: Utility and external API wrappers.

### Chat & Interaction Logic
*   `api/codx/junior/chat/chat_manager.py`: Manages chat sessions and history.
*   `api/codx/junior/chat/chat_engine.py`: Core logic for processing chat inputs.
*   `api/codx/junior/context.py`: Responsible for maintaining conversational context across turns.
*   `api/codx/junior/db.py`: Database interaction layer.
*   `api/codx/junior/chat_utils.py`: General utilities for chat components.

### Knowledge Retrieval (`knowledge/`)
The knowledge modules handle ingestion, retrieval, and embedding from multiple sources (Code, Wiki).
*   `api/codx/junior/knowledge/**.py`: Contains modules for splitting, loading, querying (`knowledge_qa_splitter.py`, `knowledge_loader.py`), and managing the vector database (`knowledge_milvus.py`).
*   `api/codx/junior/knowledge/prepromts/*.md`: Standard prompt templates used in the RAG process (e.g., structure extraction).

### Engines, Tools, & APIs
These modules encapsulate domain-specific reading and writing capabilities.
*   `api/codx/junior/engine/**.py`: Core engines for data interaction (`file_engine.py`, `git_engine.py`, `knowledge_engine.py`, etc.).
*   `api/codx/junior/tools/**.py`: Defined external functions the AI can call automatically (e.g., `code_writer.py`).
*   `api/codx/junior/api/*/*.py`: Various exposed API endpoints (e.g., `github.py`, `wiki.py`, `user_management.py`).

### Monitoring, Utilities, & Persistence
*   `api/codx/junior/**/utils/*.py`: Generic utility files.
*   `api/codx/junior/events/event_manager.py`: System event dispatching mechanism.
*   `api/codx/junior/metrics/*/*.py`: Components for tracking usage and performance (e.g., `chat_heatmap.py`).

## Dependencies
The domain relies heavily on internal structuring of modules, especially within the `/api/codx/junior/` namespace. Functionally, it has deep dependencies on data sources that are abstracted through its engines and API layers:

*   **LLM Providers:** Requires integration with OpenAI, Anthropic (if enabled), Ollama, etc.
*   **Data Persistence:** Relies on a structured database access layer (`api/codx/junior/db.py`).
*   **Version Control System:** Direct interaction with Git data and GitHub APIs (`api/codx/junior/api/github.py`, `api/codx/junior/engine/git_engine.py`).
*   **Knowledge Backends:** Requires a vector store backend (e.g., Milvus, as suggested by file names) for knowledge retrieval.

## Used By
As the core API and framework structure of the application, this domain serves as the central component utilized throughout the system's frontend and orchestration layers.

*   **Frontend UI Layer:** The main client interface will consume services exposed here (e.g., `api/codx/junior/chat_manager.py`).
*   **Task Orchestration:** Any process initiating complex tasks (including CI/CD or automated coding sprints) will utilize the agent structures and engines defined within this domain.
*   **Testing Suite:** The extensive test directory (`apis/tests/`) confirms that the entire structure is designed to be consumed, tested, and validated by other components.

## Entry Points
The following files serve as key starting points or fundamental modules for system initialization and component execution:

*   `/home/codx-junior-projects/codx-junior/api/README.md`: General project documentation entry.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Core abstract class for creating specialized agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Example agent for DevOps routines.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Specific agent focused on GitHub workflows.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Initialization point for the AI model wrapper module.