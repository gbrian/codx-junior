# AI Developer Agent

## Overview
This domain provides a sophisticated, agent-based platform designed for advanced Artificial Intelligence interactions within a development context. It functions as an intelligent coding assistant that orchestrates multiple models and data sources (including Git and Wiki) to analyze codebases, retrieve documented knowledge, and execute complex software development tasks through specialized agents.

The architecture includes modules for project management, chat functionality, task execution, and advanced knowledge retrieval systems (knowledge graphs/vector databases).

## Files in Domain
```
/home/codx-junior-projects/codx-junior/api/README.md
/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py
/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py
/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ai.py
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ai_logger.py
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/anthropic.py.disabled
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/mistral_ai.py.disabled
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/chatGPTLikeApi.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/db_router.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/file_finder.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/global_settings.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/users.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py
/home/codx-junior-projects/codx-junior/api/codx/junior/app.py
/home/codx-junior-projects/codx-junior/api/codx/junior/changes/watch_project_file_changes.py
/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_engine.py
/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_export.py
/home/codx-junior-projects/codx-junior/api/codx/junior/chat_manager.py
/home/codx-junior-projects/codx-junior/api/codx/junior/context.py
/home/codx-junior-projects/codx-junior/api/codx/junior/db.py
/home/codx-junior-projects/codx-junior/api/codx/junior/engine.py
/home/codx-junior-projects/codx-junior/api/codx/junior/events/event_manager.py
/home/codx-junior-projects/codx-junior/api/codx/junior/file_manager/__init__.py
/home/codx-junior-projects/codx-junior/api/codx/junior/globals.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/README.md
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
/home/codx-junior-projects/codx-junior/api/codx/junior/misc/github.py
/home/codx-junior-projects/codx-junior/api/codx/junior/model/model.py
/home/codx-junior-projects/codx-junior/api/codx/junior/model/user.py
/home/codx-junior-projects/codx-junior/api/codx/junior/plugins/plugin_manager.py
/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/agent-coding-task.md
/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/analyst.profile
/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/analyst.profile.md
/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/browser.profile
/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/coding_profiles.json
/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/profile_manager.py
/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/project.profile
/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/software_developer.profile
/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/wiki.profile
/home/codx-junior-projects/codx-junior/api/codx/junior/profiling/profiler.py
/home/codx-junior-projects/codx-junior/api/codx/junior/project/project_discover.py
/home/codx-junior-projects/codx-junior/api/codx/junior/project/project_manager.py
/home/codx-junior-projects/codx-junior/api/codx/junior/prompts/__init__.py
/home/codx-junior-projects/codx-junior/api/codx/junior/security/github_oauth.py
/home/codx-junior-projects/codx-junior/api/codx/junior/security/user_management.py
/home/codx-junior-projects/codx-junior/api/codx/junior/settings.py
/home/codx-junior-projects/codx-junior/api/codx/junior/sio/model.py
/home/codx-junior-projects/codx-junior/api/codx/junior/sio/session_channel.py
/home/codx-junior-projects/codx-junior/api/codx/junior/sio/sio.py
/home/codx-junior-projects/codx-junior/api/codx/junior/sio/sio_background.py
/home/codx-junior-projects/codx-junior/api/codx/junior/task_manager.py
/home/codx-junior-projects/codx-junior/api/codx/junior/tools/__init__.py
/home/codx-junior-projects/codx-junior/api/codx/junior/tools/code_writer.py
/home/codx-junior-projects/codx-junior/api/codx/junior/tools/fetch_webpage.py
/home/codx-junior-projects/codx-junior/api/codx/junior/tools/project_tools.py
/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py
/home/codx-junior-projects/codx-junior/api/codx/junior/utils/utils.py
/home/codx-junior-projects/codx-junior/api/codx/junior/whisper/audio_manager.py
/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/README.md
/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/model.py
/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_manager.py
/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_template/.vitepress/config.json
/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_template/.vitepress/config.mts
/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_template/index.md
/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_template/package-lock.json
/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_template/package.json
/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_manager.sh
/home/codx-junior-projects/codx-junior/api/codx/junior/workspace/workspace_manager.py
/home/codx-junior-projects/codx-junior/api/pyproject.toml
/home/codx-junior-projects/codx-junior/api/shared/codx-junior/scripts/docker-compose.yaml
/home/codx-junior-projects/codx-junior/api/shared/codx-junior/scripts/traefik/traefik.yaml
/home/codx-junior-projects/codx-junior/api/tests/changes/project_file_watcher/project_file_watcher.py
/home/codx-junior-projects/codx-junior/api/tests/changes/project_file_watcher/test_project_file_watcher.py
/home/codx-junior-projects/codx-junior/api/tests/changes/watch_project_file_changes.test.py
/home/codx-junior-projects/codx-junior/api/tests/chat/test_chat_manager.py
/home/codx-junior-projects/codx-junior/api/tests/db/sharedcodxjuniorapitestsdb.db.json
/home/codx-junior-projects/codx-junior/api/tests/db/test_db.py
/home/codx-junior-projects/codx-junior/api/tests/mention_manager/test_mention_manager.py
/home/codx-junior-projects/codx-junior/api/tests/test_change_manager.py
/home/codx-junior-projects/codx-junior/api/tests/wiki_manager/test_wiki_manager.py
/home/codx-junior-projects/codx-junior/api/codx/junior/api/project_search.py
/home/codx-junior-projects/codx-junior/api/codx/junior/search/project_search_manager.py
/home/codx-junior-projects/codx-junior/README.md
/home/codx-junior-projects/codx-junior/api/codx/junior/api/knowledge.py
/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_knowledge.py
/home/codx-junior-projects/codx-junior/api/codx/junior/engine/file_engine.py
/home/codx-junior-projects/codx-junior/api/codx/junior/engine/git_engine.py
/home/codx-junior-projects/codx-junior/api/codx/junior/engine/knowledge_engine.py
/home/codx-junior-projects/codx-junior/api/codx/junior/engine/session.py
/home/codx-junior-projects/codx-junior/api/codx/junior/engine/wiki_engine.py
/home/codx-junior-projects/codx-junior/api/codx/junior/global_settings.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_ai_search_message.py
/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_ai_search.py
/home/codx-junior-projects/codx-junior/api/codx/junior/model/wallet.py
```

## Dependencies
No explicit dependencies were listed for this domain in the metadata.

## Used By
This domain is not explicitly used by any other file in the project structure according to the metadata.

## Entry Points
These files are designated as primary entry points, suggesting they are starting points or core components for initializing agent functionality:

*   `/home/codx-junior-projects/codx-junior/api/README.md`: General documentation root.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`: Base class or initialization point for agents.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`: Specialized agent for DevOps tasks (deployment, infrastructure).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`: Agent focused on interacting with Git and issue trackers.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`: Entry point for AI configuration or utilities related to LLM communication.