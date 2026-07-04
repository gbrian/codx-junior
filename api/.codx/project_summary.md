# Codx-API Project Summary

An AI-driven platform for enhancing project communication, knowledge management, and collaboration through automation tools and API endpoints.

## Core Architecture

### Application & Entry Points
- **/codx/junior/api/analytics.py** - API endpoints for analytics.
- **/codx/junior/api/chat.py** - API for chat functionalities.
- **/codx/junior/app.py** - Main application setup and configuration.

### AI & Machine Learning
- **/codx/junior/ai/ai_logger.py** - Logging for AI processes.
- **/codx/junior/ai/llmfactory.py** - Language model utilities.
- **/codx/junior/ai/openai_ai.py** - OpenAI integration features.
- **/codx/junior/ai/vllm_cpu_ai.py** - VLLM CPU-based AI functionalities.
- **/codx/junior/ai/utils.py** - AI component utilities.

### Change & Version Control
- **/codx/junior/changes/change_manager.py** - File change management.
- **/codx/junior/changes/watch_project_file_changes.py** - Project file monitoring.

### Background & Task Processing
- **/codx/junior/background.py** - Background task processing.
- **/codx/junior/task_manager.py** - Scheduled task management.

### Wiki & Documentation
- **/wiki/database-and-data-storage/readme-md.md** - Database and storage guide.

### Analytics & Monitoring
- **/codx/junior/analytics/analytics.py** - Analytics aggregation and management.
- **/codx/junior/analytics/token_counter.py** - Track token usage.

### Knowledge Management
- **/codx/junior/knowledge/knowledge_ai_search.py** - AI-based knowledge search.
- **/codx/junior/knowledge/knowledge_graph.py** - Knowledge graph management.

### Chat & Communication
- **/codx/junior/chat/chat_engine.py** - Engine for chat operations.
- **/codx/junior/chat_manager.py** - Manage chat sessions.

### File & Project Management
- **/codx/junior/file_manager/__init__.py** - File management initialization.
- **/codx/junior/project/project_manager.py** - Project management tools.

### Security & User Management
- **/codx/junior/security/github_oauth.py** - GitHub OAuth security.
- **/codx/junior/security/user_management.py** - User account management.

### Plugins & Extensions
- **/codx/junior/plugins/plugin_manager.py** - Plugin and extension management.