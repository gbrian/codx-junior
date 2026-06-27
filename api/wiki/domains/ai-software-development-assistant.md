# AI Software Development Assistant

## Overview
This domain provides a comprehensive platform for advanced AI-driven software development assistance. It is designed to be an intelligent orchestrator that tackles complex coding and project management workflows. The system utilizes specialized components, including autonomous agents (such as DevOps and Git issue agents), and features a robust knowledge retrieval system. This knowledge system digests codebases, extensive documentation, and historical project data, allowing the core functionality to plan, execute, and generate sophisticated solutions autonomously. The `codx-junior` architecture facilitates deep integration of various AI models and APIs for maximum development support.

## Files in Domain
The following files constitute this software domain:

*   `/home/codx-junior-projects/codx-junior/api/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ai.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/anthropic.py.disabled`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/llmfactory.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/mistral_ai.py.disabled`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/ollama.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/openai_ai.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/utils.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/chatGPTLikeApi.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/db_router.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/file_finder.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/github.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/global_settings.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/users.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/wiki.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/app.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/changes/watch_project_file_changes.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_engine.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_export.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/context.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/db.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/events/event_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/file_manager/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/globals.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_splitter.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_code_to_dcouments.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_db.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_keywords.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_loader.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_milvus.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_prompts.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_qa_splitter.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_splitter.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_training.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_wiki.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/code_to_chunks.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/enrich_document.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/extract_document_tags.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/prepromts/extract_query_tags.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/settings.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/log_parser.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/main.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/mentions/mention_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/chat_heatmap.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/chat_wall.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/metrics/codx_junior_metrics.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/misc/github.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/model.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/user.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/plugins/plugin_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/agent-coding-task.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/analyst.profile`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/analyst.profile.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/browser.profile`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/coding_profiles.json`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/profile_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/project.profile`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/software_developer.profile`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiles/wiki.profile`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/profiling/profiler.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/project/project_discover.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/project/project_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/prompts/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/security/github_oauth.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/security/user_management.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/settings.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/model.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/session_channel.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/sio.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/sio/sio_background.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/task_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/code_writer.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/fetch_webpage.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/tools/project_tools.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/chat_utils.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/utils/utils.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/whisper/audio_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/model.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_manager.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_template/.vitepress/config.json`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/project_search.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/search/project_search_manager.py`
*   `/home/codx-junior-projects/codx-junior/README.md`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/knowledge.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/chat/chat_knowledge.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/file_engine.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/git_engine.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/knowledge_engine.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/session.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/wiki_engine.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/global_settings.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_ai_search_message.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_ai_search.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/wallet.py`

## Dependencies
No explicit dependencies were listed for this domain, suggesting a highly modular structure where components communicate primarily through internal APIs and services rather than rigid library requirements.

## Used By
This domain is currently not specified as being used by other parts of the codebase according to the provided manifest data.

## Entry Points
The following files serve as primary or specialized entry points for initiating workflows within this domain:

*   `/home/codx-junior-projects/codx-junior/api/README.md` (General API Documentation)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/base_agent.py` (Base Agent definition)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/devops_agent.py` (DevOps Workflow Agent)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/agents/git_issues_agent.py` (Git Issue Management Agent)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/__init__.py` (AI Core Initialization)