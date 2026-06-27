# Codx-API Project Summary

An AI-driven platform for enhancing communication, knowledge management, and project automation with real-time collaboration capabilities.

## Core Architecture

### AI & Language Models
- `/codx/junior/ai/ai.py` - Main AI interface and orchestration
- `/codx/junior/ai/llmfactory.py` - Factory for creating LLM instances
- `/codx/junior/ai/openai_ai.py` - OpenAI integration
- `/codx/junior/ai/ollama.py` - Ollama local model support
- `/codx/junior/ai/vllm_cpu_ai.py` - vLLM CPU inference
- `/codx/junior/ai/wallet_check.py` - Token/wallet management
- `/codx/junior/ai/cancellation.py` - Request cancellation handling
- `/codx/junior/ai/ai_logger.py` - AI activity logging

### API & Service Layer
- `/codx/junior/api/chat.py` - Chat endpoints
- `/codx/junior/api/projects.py` - Project management
- `/codx/junior/api/users.py` - User authentication and profiles
- `/codx/junior/api/workspaces.py` - Workspace management
- `/codx/junior/api/github.py` - GitHub integration
- `/codx/junior/api/global_settings.py` - Configuration management
- `/codx/junior/api/knowledge.py` - Knowledge base endpoints
- `/codx/junior/api/wiki.py` - Wiki endpoints
- `/codx/junior/api/logs.py` - Logging endpoints
- `/codx/junior/api/analytics.py` - Analytics endpoints and metrics exposure
- `/codx/junior/api/file_finder.py` - File search utilities
- `/codx/junior/api/project_search.py` - Project search endpoints
- `/codx/junior/api/db_router.py` - Database routing

### Chat & Conversation
- `/codx/junior/chat/chat_engine.py` - Chat processing engine
- `/codx/junior/chat/chat_knowledge.py` - Knowledge integration in chat
- `/codx/junior/chat/chat_export.py` - Chat export functionality
- `/codx/junior/chat_manager.py` - Chat session management

### Knowledge Management & RAG
- `/codx/junior/knowledge/knowledge_ai_search.py` - AI-powered search
- `/codx/junior/knowledge/knowledge_training.py` - Knowledge base training
- `/codx/junior/knowledge/knowledge_milvus.py` - Milvus vector DB integration
- `/codx/junior/knowledge/knowledge_loader.py` - Document loading
- `/codx/junior/knowledge/knowledge_splitter.py` - Text chunking strategies
- `/codx/junior/knowledge/knowledge_graph.py` - Knowledge graph construction
- `/codx/junior/knowledge/knowledge_db.py` - Knowledge base storage
- `/codx/junior/knowledge/knowledge_keywords.py` - Keyword extraction
- `/codx/junior/knowledge/knowledge_code_splitter.py` - Code-specific chunking
- `/codx/junior/knowledge/knowledge_code_to_dcouments.py` - Code to document conversion

### Analytics & Monitoring
- `/codx/junior/analytics/analytics.py` - Analytics aggregation and reporting
- `/codx/junior/analytics/token_counter.py` - Token usage analytics
- `/codx/junior/analytics/storage.py` - Analytics data storage
- `/codx/junior/analytics/model.py` - Analytics data models

### Execution Engines
- `/codx/junior/engine/code_engine.py` - Code execution and analysis
- `/codx/junior/engine/file_engine.py` - File operations
- `/codx/junior/engine/git_engine.py` - Git operations
- `/codx/junior/engine/wiki_engine.py` - Wiki content management
- `/codx/junior/engine/knowledge_engine.py` - Knowledge retrieval
- `/codx/junior/engine/chat_engine_actions.py` - Chat action execution
- `/codx/junior/engine/session.py` - Session management

### Agents
- `/codx/junior/agents/base_agent.py` - Base agent framework
- `/codx/junior/agents/devops_agent.py` - DevOps automation
- `/codx/junior/agents/git_issues_agent.py` - Git issue handling

### Real-Time Communication
- `/codx/junior/sio/sio.py` - Socket.IO server setup
- `/codx/junior/sio/session_channel.py` - Session and channel management
- `/codx/junior/sio/sio_background.py` - Background task execution via sockets
- `/codx/junior/sio/model.py` - Socket.IO data models

### Background Processing
- `/codx/junior/background.py` - Background task initialization
- `/codx/junior/task_manager.py` - Task execution and scheduling

### Data & Storage
- `/codx/junior/db.py` - Database connection and models
- `/codx/junior/model/model.py` - Core data models
- `/codx/junior/model/user.py` - User models
- `/codx/junior/model/ai_model.py` - AI model definitions
- `/codx/junior/model/wallet.py` - Wallet/token models
- `/codx/junior/model/logs.py` - Log models

### File & Project Monitoring
- `/codx/junior/changes/watch_project_file_changes.py` - File change monitoring
- `/codx/junior/changes/change_manager.py` - Change management in project files
- `/codx/junior/project/project_manager.py` - Project operations
- `/codx/junior/project/project_discover.py` - Project discovery

### Wiki & Documentation
- `/codx/junior/wiki/wiki_manager.py` - Wiki lifecycle management
- `/codx/junior/wiki/wiki_index.py` - Wiki indexing
- `/codx/junior/wiki/wiki_domains.py` - Domain-specific wikis
- `/codx/junior/wiki/model.py` - Wiki data models

### Utilities & Support
- `/codx/junior/profiles/profile_manager.py` - User/role profiles
- `/codx/junior/search/project_search_manager.py` - Project search
- `/codx/junior/security/user_management.py` - User authorization
- `/codx/junior/security/github_oauth.py` - GitHub OAuth flow
- `/codx/junior/tools/code_writer.py` - Code generation tools
- `/codx/junior/tools/fetch_webpage.py` - Web content fetching
- `/codx/junior/tools/project_tools.py` - Project utilities
- `/codx/junior/utils/chat_utils.py` - Chat utilities
- `/codx/junior/utils/utils.py` - General utilities
- `/codx/junior/mentions/mention_manager.py` - Mention handling
- `/codx/junior/events/event_manager.py` - Event management
- `/codx/junior/plugins/plugin_manager.py` - Plugin system
- `/codx/junior/views/view_manager.py` - View management
- `/codx/junior/whisper/audio_manager.py` - Audio transcription

### Entry Points
- `/codx/junior/main.py` - Application startup
- `/codx/junior/app.py` - Flask/API application
- `/codx/junior/context.py` - Request context management
- `/codx/junior/settings.py` - Global settings
- `/codx/junior/globals.py` - Global variables