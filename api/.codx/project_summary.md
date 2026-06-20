# Codx-API Project Summary: Advanced AI Coding Assistant Orchestrator

Advanced developer assistance platform that orchestrates conversational AI workflows, integrates specialized agents, provides RAG capabilities over codebases, and abstracts multiple LLM interactions through a unified interface.

***

## 🌐 System APIs & Service Layer
Domain-specific service interfaces for authentication, projects, users, and knowledge retrieval.
- `codx/junior/api/users.py` - User management and authentication
- `codx/junior/api/projects.py` - Project configuration and metadata
- `codx/junior/api/chat.py` - Conversational interface
- `codx/junior/api/wiki.py` - Wiki content retrieval and management
- `codx/junior/api/analytics.py` - Usage tracking and metrics reporting
- `codx/junior/api/logs.py` - Operational log persistence
- `codx/junior/api/github.py` - GitHub integration and issue tracking
- `codx/junior/api/knowledge.py` - RAG knowledge base queries
- `codx/junior/api/global_settings.py`, `views.py`, `chatGPTLikeApi.py` - Supporting API utilities

## ⚙️ Core Engine & State Management
Orchestration hub for chat flow, async tasks, and persistent context.
- `codx/junior/chat_manager.py` - Manages chat lifecycle and state
- `codx/junior/engine.py` - Main orchestration controller
- `codx/junior/context.py` - Conversational memory and context
- `codx/junior/task_manager.py` - Background job scheduling
- `codx/junior/background.py` - Async task execution
- `codx/junior/events/event_manager.py` - Event-driven communication

## 💬 Chat, Agents & Interaction Layer
Conversational logic, specialized autonomous agents, and tool execution.
- `codx/junior/chat/chat_engine.py` - Workflow generation and chat logic
- `codx/junior/agents/base_agent.py` - Agent framework
- `codx/junior/agents/devops_agent.py` - DevOps automation agent
- `codx/junior/agents/git_issues_agent.py` - GitHub issues agent
- `codx/junior/profiles/profile_manager.py` - Role/profile management
- `codx/junior/profiles/*.profile*` - Specialized role definitions (analyst, developer, etc.)
- `codx/junior/tools/code_writer.py` - Code generation and writing
- `codx/junior/tools/project_tools.py` - Project-specific utilities
- `codx/junior/tools/fetch_webpage.py` - Web content retrieval
- `codx/junior/mentions/mention_manager.py` - User/entity mention handling

## 📚 Knowledge Management & RAG
Vector-based retrieval augmented generation for codebase and wiki integration.
- `codx/junior/knowledge/knowledge_loader.py` - Document ingestion pipeline
- `codx/junior/knowledge/knowledge_splitter.py` - Document chunking strategy
- `codx/junior/knowledge/knowledge_code_splitter.py` - Code-specific parsing
- `codx/junior/knowledge/knowledge_graph.py` - Knowledge graph construction and traversal
- `codx/junior/knowledge/knowledge_db.py` - Vector DB abstraction
- `codx/junior/knowledge/knowledge_milvus.py` - Milvus vector store implementation
- `codx/junior/knowledge/knowledge_ai_search.py` - AI-powered semantic search
- `codx/junior/knowledge/knowledge_training.py` - Knowledge base training
- `codx/junior/knowledge/knowledge_wiki.py` - Wiki document processing
- `codx/junior/knowledge/knowledge_prompts.py` - Search and enrichment prompts

## 🧠 AI Model Abstraction Layer
Unified interface for multiple LLM providers with consistent request/response handling.
- `codx/junior/ai/ai.py` - Abstract AI provider interface
- `codx/junior/ai/llmfactory.py` - Model provider factory
- `codx/junior/ai/openai_ai.py` - OpenAI API wrapper
- `codx/junior/ai/ollama.py` - Ollama local model support
- `codx/junior/ai/vllm_cpu_ai.py` - vLLM CPU inference
- `codx/junior/ai/raw_logger.py`, `raw_log_reader.py` - Request/response logging
- `codx/junior/ai/cancellation.py` - Request cancellation handling
- `codx/junior/ai/wallet_check.py` - Token quota management
- `codx/junior/ai/ai_logger.py` - AI interaction logging

## 🔨 Execution & Domain Engines
Safe, structured environments for code, filesystem, and version control operations.
- `codx/junior/engine/code_engine.py` - Code execution sandbox
- `codx/junior/engine/file_engine.py` - Filesystem read/write operations
- `codx/junior/engine/git_engine.py` - Git version control interactions
- `codx/junior/engine/knowledge_engine.py` - Knowledge retrieval orchestration
- `codx/junior/engine/wiki_engine.py` - Wiki content management
- `codx/junior/engine/chat_engine_actions.py` - Chat workflow actions
- `codx/junior/engine/session.py` - User session management

## 📊 Analytics & Profiling
Usage tracking, performance metrics, and behavior analysis.
- `codx/junior/analytics/analytics.py` - Analytics collection and reporting
- `codx/junior/analytics/token_counter.py` - LLM token usage tracking
- `codx/junior/analytics/storage.py` - Metrics persistence
- `codx/junior/metrics/codx_junior_metrics.py` - System-wide metrics
- `codx/junior/metrics/chat_heatmap.py` - Chat activity visualization
- `codx/junior/metrics/chat_wall.py` - Activity aggregation
- `codx/junior/profiling/profiler.py` - Performance profiling

## 🔌 Project & File Management
Project discovery, file tracking, and change detection.
- `codx/junior/project/project_manager.py` - Project lifecycle management
- `codx/junior/project/project_discover.py` - Project detection and initialization
- `codx/junior/changes/change_manager.py` - File change tracking
- `codx/junior/changes/watch_project_file_changes.py` - File system watcher
- `codx/junior/search/project_search_manager.py` - Project-wide code search
- `codx/junior/api/file_finder.py`, `project_search.py` - File discovery utilities

## 🔐 Security & User Management
Authentication, authorization, and workspace isolation.
- `codx/junior/security/user_management.py` - User account management
- `codx/junior/security/github_oauth.py` - OAuth integration
- `codx/junior/api/users.py` - User service API
- `codx/junior/workspace/workspace_manager.py` - Workspace isolation

## 📡 Real-Time Communication
WebSocket-based real-time bidirectional communication.
- `codx/junior/sio/sio.py` - Socket.IO server implementation
- `codx/junior/sio/session_channel.py` - Session-based messaging
- `codx/junior/sio/sio_background.py` - Background job communication

## 📖 Wiki & Documentation
Wiki content management, domain classification, and documentation rendering.
- `codx/junior/wiki/wiki_manager.py` - Wiki lifecycle management
- `codx/junior/wiki/wiki_domains.py` - Wiki domain classification and ontology
- `codx/junior/wiki/wiki_index.py` - Wiki indexing and search
- `codx/junior/wiki/model.py` - Wiki data structures
- `codx/junior/wiki/wiki_template/` - VitePress wiki template

## 🎯 Application Entry Points
- `codx/junior/main.py` - Application bootstrap
- `codx/junior/app.py` - Flask/FastAPI application setup
- `codx/junior/db.py` - Database initialization and ORM