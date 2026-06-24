# AI Agent Orchestration Platform

## Overview

This domain defines a comprehensive framework for building sophisticated, intelligent, and multi-step developer workflows. It functions as an orchestration layer designed to empower autonomous goal completion in complex development environments.

The core functionality involves integrating various Large Language Models (LLMs) with specialized agents—such as DevOps Agents, Git Issue Management Agents, and knowledge retrieval systems. Through these integrations, the platform can perform intricate tasks including:

*   **Complex Coding & Development:** Managing project lifecycles and collaborating across different codebases.
*   **Information Retrieval:** Utilizing dynamic knowledge bases (including structured documentation and unstructured Wikis) to answer complex queries.
*   **Platform Interaction:** Performing actions on external platforms like GitHub (e.g., issue tracking, branch management) and internal document systems (Wikis).

To facilitate autonomous operations, the system manages persistent context, robust user profiles, and a dynamic knowledge base, allowing it to handle sophisticated developer tasks from initial problem definition through final solution deployment.

## Files in Domain

The following files constitute the implemented modules and logic for the AI Agent Orchestration Platform:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` (Base structure for all specialized agents)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` (Agent handling DevOps tasks)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py` (Agent for Git and issue tracking)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ai.py` (Core AI logic)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ai_logger.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/anthropic.py.disabled`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py` (Factory for different LLM connections)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py` (OpenAI integration)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/chatGPTLikeApi.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/db_router.py` (Database routing logic)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/file_finder.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py` (GitHub API interaction)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/global_settings.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/users.py` (User profile management)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py` (Wiki interaction)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py` (Main application entry point skeleton/setup)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/background.py` (Background task handling)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/changes/change_manager.py` (Change tracking and management)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/changes/watch_project_file_changes.py` (File change monitoring)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_engine.py` (Primary chat processing logic)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_export.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat_manager.py` (State management for chat sessions)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py` (System context and memory storage)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/db.py` (Database connection layer)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine.py` (Main execution engine)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/events/event_manager.py` (Event handling system)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/file_manager/__init__.py` (File utility utilities)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/globals.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_splitter.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_to_dcouments.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_db.py` (Knowledge database interaction)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_keywords.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py` (Data loading)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py` (Vector store integration)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_prompts.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_qa_splitter.py` (Question Answer splitting)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py` (Generic content splitter)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_training.py` (Knowledge updating mechanism)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_wiki.py` (Wiki specific knowledge handling)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/code_to_chunks.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/enrich_document.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/extract_document_tags.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/extract_query_tags.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/settings.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/log_parser.py` (Log analysis)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/main.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/mentions/mention_manager.py` (Managing in-chat mentions)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/chat_heatmap.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/chat_wall.py` (Visualization tools)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/codx_junior_metrics.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/misc/github.py` (Utility for GitHub operations)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/model.py` (Core data models)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/user.py` (User model definition)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/plugins/plugin_manager.py` (Plugin management system)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/agent-coding-task.md` (Profile definitions)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/analyst.profile`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/analyst.profile.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/browser.profile`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/coding_profiles.json`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/profile_manager.py` (Loading and managing user profiles)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/project.profile`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/software_developer.profile`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/wiki.profile`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiling/profiler.py` (Profiling user behavior)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/project/project_discover.py` (Project finding utility)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/project/project_manager.py` (Project lifecycle state management)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/prompts/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/security/github_oauth.py` (OAuth handling)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/security/user_management.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/settings.py` (Global configuration)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/model.py` (Socket IO data models)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/session_channel.py` (Handling real-time sessions)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/sio.py` (Socket IO core implementation)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/sio_background.py` (Background Socket IO processing)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/task_manager.py` (Asynchronous task management)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/code_writer.py` (Code generation tool)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/fetch_webpage.py` (External web fetching utility)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/project_tools.py` (Project specific tools)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/utils.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/whisper/audio_manager.py` (Audio processing)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/model.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_manager.py` (Wiki content handling)
*   (`/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_template/.vitepress/config.json`, `.../config.mts`, etc.) (Static Wiki Assets)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/workspace/workspace_manager.py`

## Dependencies

No explicit module dependencies were listed in the provided metadata.

## Used By

This domain is not explicitly listed as being used by other defined domains or files.

## Entry Points

The following modules are designated as primary entry points for the system:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`