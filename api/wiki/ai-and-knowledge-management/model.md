# Model Classes Documentation

## Overview

This module defines the core data models for the Codx Junior AI and Knowledge Management system. It provides Pydantic-based models for handling user data, AI configurations, workspace management, and project-related entities.

## Core Model Classes

### User Models

**CodxUser, CodxUserLogin, CodxUserProjectProfile**
- Imported from `codx.junior.model.user`
- Handle user authentication, profiles, and project-specific user data

### AI Configuration Models

**AIProvider, AIModel, AISettings**
- Imported from `codx.junior.model.ai_model`
- Manage AI provider configurations and model settings
- Support for LLM and embedding models
- Default providers include Ollama with pre-configured knowledge and embedding models

**AILLMModelSettings, AIEmbeddingModelSettings, AIModelType**
- Define specific AI model type configurations
- Constants: `OLLAMA_PROVIDER`, `OLLAMA_EMBEDDINGS_MODEL`, `OLLAMA_KNOWLEDGE_MODEL`

### Chat and Communication Models

**ChatMessage**
- Role-based messaging (e.g., 'user', 'assistant')
- Supports multimodal content (text and images)

**Content**
- Type: text or image
- Text content as string
- Image URLs for visual content

**ImageUrl**
- Encapsulates URL references for images

### Knowledge Management Models

**KnowledgeSearch**
- `search_term`: Query string
- `search_type`: Type of search operation
- `document_search_type`: Specific document search method
- `document_count`: Number of results
- `document_cutoff_score`: Score threshold for relevance
- `document_cutoff_rag`: RAG (Retrieval-Augmented Generation) cutoff threshold

**KnowledgeReloadPath**
- Path for reloading knowledge sources

**KnowledgeDeleteSources**
- List of sources to delete from knowledge base

**Document**
- `id`: Document identifier
- `page_content`: Document text content
- `metadata`: Associated document metadata

### Project Management Models

**Board**
- `name`, `description`: Board identification
- `columns`: List of Column objects organizing chats
- `bookmark`: Optional bookmark flag
- `remote_url`: External board reference
- `project_id`: Associated project identifier

**Column**
- `name`: Column identifier
- `chat_ids`: List of chat IDs in column
- `project_id`: Parent project reference

**ProjectScript**
- `name`, `description`: Script identification
- `script`: Bash script content
- `status`: Running state (running, stopped, error)
- `background`: Run in background mode
- `restart`: Auto-restart on stop
- `engine`: Script execution engine (default: bash)
- `pid_file_path`: Process ID file location

### Tool Models

**Tool**
- `name`: Tool identifier
- `description`: Tool functionality description

**CodxJuniorBaseTools**
- Predefined knowledge search tool

**CommandTool**
- Extends Tool with optional command field

### Configuration Models

**OpenAISettings**
- API URL and key configuration
- Default model: gpt-4o

**AnthropicAISettings**
- API URL and key configuration
- Default model: claude-3-5-sonnet-20240620

**MistralAISettings**
- API URL and key configuration
- Default model: codestral-latest

**GitSettings**
- `username`, `email`: Git configuration

**AgentSettings**
- `max_agent_iteractions`: Maximum iterations (default: 4)

### Workspace and Profile Models

**Workspace, WorkspaceApp, Profile, ProfileApiSettings**
- Imported from dedicated modules
- Manage workspace configurations and user profiles
- Default workspace provided via `DEFAULT_WORKSPACE`

### Integration Models

**MCPServer**
- Model Context Protocol server configuration
- `name`, `url`: Server identification
- `api_key`: Authentication credentials
- `active`: Activation status

**OAuthProvider**
- OAuth provider configuration
- `name`, `client_id`, `secret`, `token_url`

**Plugin**
- `plugin_id`, `name`, `description`: Plugin identification
- `module_path`, `plugin_path`, `method`: Code location
- `arguments`: List of PluginArgument objects
- `roles`: Permission roles
- `extends`: Extended functionality list
- `async_`: Asynchronous execution flag (aliased as "async")

**PluginArgument**
- `name`, `description`: Argument details
- `default_value`: Fallback value

### Media Models

**ImageGenerationRequest, ImageGenerationResponse**
- Image generation operations

**ImageAnalysisRequest, ImageAnalysisResponse**
- Image analysis operations

**ImageMetadata**
- Image metadata storage

**LiveEdit**
- Real-time chat editing
- `chat_name`: Chat identifier
- `html`, `url`: Content and location
- `message`: Edit message

### Utility Models

**Logprobs**
- Token probability logging
- `tokens`: Token list
- `token_logprobs`: Probability values
- `top_logprobs`: Top alternative probabilities
- `text_offset`: Character positions

**Bookmark**
- `name`, `icon`, `title`: Bookmark display
- `url`, `port`: Resource location

**PRView**
- `from_branch`, `to_branch`: Git branch references

**Screen**
- Display resolution configurations
- Default resolution list with 13 common screen sizes

## Global Settings Model

**GlobalSettings**
- Centralized configuration container
- AI model selections for embeddings, LLM, RAG, Wiki, vision, and image generation
- User management with default admin user
- Workspace configuration with port ranges (16000-17000)
- Plugin registry
- OAuth provider configuration
- Project root path specification
- File manager toggle
- Project scripts collection
- Bookmarks and global chat instructions
- Logging configuration with AI logging flag and ignore list
- Environment variables dictionary
- Docker workspace settings

## Dependencies
**Imports from:** codx/junior/model/user.py, codx/junior/model/ai_model.py, codx/junior/model/profile.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/ai/ai.py, codx/junior/ai/llmfactory.py, codx/junior/ai/openai_ai.py, codx/junior/ai/vllm_cpu_ai.py, codx/junior/ai/wallet_check.py, codx/junior/api/__init__.py, codx/junior/api/analytics.py, codx/junior/api/github.py, codx/junior/api/global_settings.py, codx/junior/api/knowledge.py, codx/junior/api/logs.py, codx/junior/api/projects.py, codx/junior/api/users.py, codx/junior/api/views.py, codx/junior/api/wiki.py, codx/junior/api/workspaces.py, codx/junior/app.py, codx/junior/chat/chat_engine.py, codx/junior/context.py, codx/junior/db.py, codx/junior/engine/file_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/session.py, codx/junior/global_settings.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_db.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/mentions/mention_manager.py, codx/junior/plugins/plugin_manager.py, codx/junior/profiles/profile_manager.py, codx/junior/project/project_discover.py, codx/junior/project/project_manager.py, codx/junior/settings.py, codx/junior/tools/project_tools.py, codx/junior/utils/chat_utils.py, codx/junior/wiki/wiki_domains.py, codx/junior/wiki/wiki_manager.py, codx/junior/workspace/workspace_manager.py