# AI-Driven Application Agent

## Overview

This domain provides a robust and complex framework for running sophisticated, multi-step AI agents tailored specifically for development workflows. It functions as an intelligent orchestration layer, designed to autonomously process vast amounts of organizational knowledge—including code repositories, wiki documentation, project management data (like GitHub issues), and file system context.

The core functionality involves integrating various Large Language Model (LLM) providers and tools (OpenAI, Anthropic, Mistral, Ollama, etc.) to enable complex task execution. The agents assist users with critical tasks such as automated coding, detailed project analysis, documentation generation, and comprehensive query answering across the organization's knowledge base.

This system establishes modular components for:
*   **Knowledge Retrieval**: Utilizing advanced indexing (Milvus) and chunking techniques (`knowledge_splitter`, `knowledge_loader`) to turn raw data into retrievable knowledge chunks.
*   **Agentic Workflow**: Defining specialized agents (e.g., `devops_agent`, `git_issues_agent`) that interact with external tools (GitHub API, file manager) to perform multi-step actions.
*   **Context Management**: Maintaining state and context across various interactions using session management (`context.py`).
*   **Persistence & API Integration**: Providing structured APIs for interacting with backend functionalities like user profiles, project settings, and data storage.

In essence, this domain transforms scattered corporate knowledge and development tasks into a unified, intelligent workflow platform powered by advanced AI agents.

## Files in Domain

/home/codx-junior-projects/codx-junior/api/README.md
/home/codx-junior-projects/codx-junior/api/codx/junior/api/chatGPTLikeApi.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/analytics.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/db_router.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/file_finder.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/global_settings.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/knowledge.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/project_search.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/users.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py
/home/codx-junior-projects/codx-junior/api/codx/junior/app.py
/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py
/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py
/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py
/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_engine.py
/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_export.py
/home/codx-junior-projects/codx-junior/api/codx/junior/chat_manager.py
/home/codx-junior-projects/codx-junior/api/codx/junior/context.py
/home/codx-junior-projects/codx-junior/api/codx/junior/db.py
/home/codx-junior-projects/codx-junior/api/codx/junior/engine.py
/home/codx-junior-projects/codx-junior/api/codx/junior/events/event_manager.py
/home/codx-junior-projects/codx-junior/api/codx/junior/file_manager/__init__.py
/home/codx-junior-projects/codx-junior/api/codx/junior/globals.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/__init__.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_splitter.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_to_dcouments.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_db.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_keywords.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_prompts.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_qa_splitter.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_training.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_wiki.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/code_to_chunks.md
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/enrich_document.md
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/extract_document_tags.md
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/extract_query_tags.md
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/settings.py
/home/codx-junior-projects/codx-junior/api/codx/junior/log_parser.py
/home/codx-junior-projects/codx-junior/api/codx/junior/main.py
/home/codx-junior-projects/codx-junior/api/codx/junior/mentions/mention_manager.py
/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/chat_heatmap.py
/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/chat_wall.py
/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/codx_junior_metrics.py
/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py
/home/codx-junior-projects/codx-junior/api/codx/junior/utils/utils.py
/home/codx-junior-projects/codx-junior/api/codx/junior/whisper/audio_manager.py
/home/codx-junior-projects/codx-junior/api/testing/*

## Dependencies

None explicitly defined in the provided metadata.

## Used By

None specified in the provided metadata.

## Entry Points

The primary entry points for this domain are:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`