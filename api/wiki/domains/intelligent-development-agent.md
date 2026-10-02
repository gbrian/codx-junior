# Intelligent Development Agent

## Overview

The Intelligent Development Agent is a complex, context-aware AI framework designed to revolutionize software development assistance. It acts as an orchestrator layer, enabling specialized agents and tools to interact seamlessly with data sources and Large Language Model (LLM) providers. Its core intelligence function revolves around deep knowledge retrieval—drawing actionable insights from project files, sprawling documentation, and historical development data (such as Git logs and ticket systems).

This domain incorporates modular components for managing various AI interactions:
*   **Agent Orchestration:** Managing specialized agents like `devops_agent` and `git_issues_agent`.
*   **LLM Integration:** Providing abstract interfaces to communicate with multiple LLMs (OpenAI, Mistral, Ollama, Anthropic).
*   **Knowledge Retrieval (RAG):** Implementing sophisticated knowledge bases (`knowledge/`) using techniques like document chunking, embedding generation (Milvus), and semantic searching to ensure the AI's responses are grounded in project context.
*   **Tooling:** Providing practical tools for common dev workflows, such as code writing, file searching, web scraping, and database routing.

The structure suggests a robust architecture capable of handling full development lifecycles, from initial planning (using profilers and profiles) to continuous deployment support via integrated agents.

## Files in Domain

The following files constitute the codebase for the Intelligent Development Agent:

`/home/codx-junior-projects/codx-junior/api/README.md`
`/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ai.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ai_logger.py`
`/home/codx-junior-projects/codx-junior/api/codx-junior/api/codx/junior/ai/anthropic.py.disabled`
`/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/ai/mistral_ai.py.disabled`
`/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/api/chatGPTLikeApi.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/api/db_router.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/api/file_finder.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/api/global_settings.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/api/users.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/app.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/changes/watch_project_file_changes.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_engine.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_export.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/chat_manager.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/context.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/db.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/engine.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/events/event_manager.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/file_manager/__init__.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/globals.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/README.md`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/__init__.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_splitter.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_to_dcouments.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_db.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_keywords.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_prompts.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_qa_splitter.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_training.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_wiki.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/code_to_chunks.md`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/enrich_document.md`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/extract_document_tags.md`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/extract_query_tags.md`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/settings.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/log_parser.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/main.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/mentions/mention_manager.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/chat_heatmap.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/chat_wall.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/codx_junior_metrics.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/misc/github.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/model/model.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/model/user.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/plugins/plugin_manager.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/agent-coding-task.md`
`/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/analyst.profile`
`/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/analyst.profile.md`
`/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/browser.profile`
`/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/coding_profiles.json`
`/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/profile_manager.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/project.profile`
`/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/software_developer.profile`
`/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/wiki.profile`
`/home/codx-junior-projects/codx-junior/api/codx/junior/profiling/profiler.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/project/project_discover.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/project/project_manager.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/prompts/__init__.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/security/github_oauth.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/security/user_management.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/settings.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/sio/model.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/sio/session_channel.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/sio/sio.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/sio/sio_background.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/task_manager.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/tools/__init__.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/tools/code_writer.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/tools/fetch_webpage.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/tools/project_tools.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/utils/utils.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/whisper/audio_manager.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/README.md`
`/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/model.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_manager.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_template/.vitepress/config.json`
`/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_template/.vitepress/config.mts`
`/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_template/index.md`
`/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_template/package-lock.json`
`/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_template/package.json`
`/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_template/wiki-manager.sh`
`/home/codx-junior-projects/codx-junior/api/codx/junior/workspace/workspace_manager.py`
`/home/codx-junior-projects/codx-junior/api/pyproject.toml`
`/home/codx-junior-projects/codx-junior/api/shared/codx-junior/scripts/docker-compose.yaml`
`/home/codx-junior-projects/codx-junior/api/shared/codx-junior/scripts/traefik/traefik.yaml`
`/home/codx-junior-projects/codx-junior/api/tests/changes/project_file_watcher/project_file_watcher.py`
`/home/codx-junior-projects/codx-junior/api/tests/changes/project_file_watcher/test_project_file_watcher.py`
`/home/codx-junior-projects/codx-junior/api/tests/changes/watch_project_file_changes.test.py`
`/home/codx-junior-projects/codx-junior/api/tests/db/sharedcodxjuniorapitestsdb.db.json`
`/home/codx-junior-projects/codx-junior/api/tests/db/test_db.py`
`/home/codx-junior-projects/codx-junior/api/tests/mention_manager/test_mention_manager.py`
`/home/codx-junior-projects/codx-junior/api/tests/test_change_manager.py`
`/home/codx-junior-projects/codx-junior/api/tests/wiki_manager/test_wiki_manager.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/api/project_search.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/search/project_search_manager.py`
`/home/codx-junior-projects/codx-junior/README.md`
`/home/codx-junior-projects/codx-junior/api/codx/junior/api/knowledge.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_knowledge.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/engine/file_engine.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/engine/git_engine.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/engine/knowledge_engine.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/engine/session.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/engine/wiki_engine.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/global_settings.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_ai_search_message.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_ai_search.py`
`/home/codx-junior-projects/codx-junior/api/codx/junior/model/wallet.py`

## Dependencies

The system currently shows no explicit dependencies listed in the metadata structure. However, due to its nature as an agent orchestrator and context retriever, it is highly coupled with multiple internal components:
*   **AI Model APIs:** Requires connection modules for various LLMs (OpenAI, Mistral, Ollama).
*   **Data Stores:** Relies on database and vector store client implementations (Milvus module suggests Vector DB usage).
*   **External Services:** Integration with GitHub services (`github.py`, `git_issues_agent`).

## Used By
The system currently shows no explicit files using it as a dependency. As the core "Intelligent Development Agent," all major parts of the application likely interact with its internal modules for context, tool invocation, and model routing (e.g., `main.py`, `app.py`).

## Entry Points

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` (Base agent definition)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` (Specialized DevOps actions agent)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py` (Agent specialized in Git and Issue tracking)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py` (AI subsystem initialization)