# Model Documentation

## Overview

This module defines the core data models used throughout the Codx Junior application. It provides Pydantic-based models for managing users, AI configurations, projects, workspaces, and various application settings.

## Core Imports

The module imports specialized models from dedicated sub-modules:

- **User Models**: Authentication and profile management (`CodxUserLogin`, `CodxUserProjectProfile`, `CodxUser`)
- **AI Models**: Provider and model configurations (`AIProvider`, `AIModel`, `AISettings`)
- **Profile Models**: User profile and API settings (`Profile`, `ProfileApiSettings`)
- **Workspace Models**: Workspace and application management (`Workspace`, `WorkspaceApp`)

## Chat and Communication Models

### ChatMessage
Represents a message in a chat conversation with role and content structure.

**Fields:**
- `role`: Message sender role (e.g., 'user', 'assistant')
- `content`: List of `Content` objects containing the message payload

### Content
Defines the structure of message content, supporting text and image data.

**Fields:**
- `type`: Content type (default: 'text')
- `text`: Text content
- `image_url`: Image URL object for image content

### ImageUrl
Simple wrapper for image URLs in messages.

**Fields:**
- `url`: Image URL string

## Board and Organization Models

### Board
Represents a project board with columns for organizing chats.

**Fields:**
- `name`: Board name
- `description`: Board description
- `remote_url`: Remote repository URL
- `bookmark`: Optional bookmark flag
- `columns`: List of `Column` objects
- `project_id`: Associated project identifier

### Column
Organizes chats within a board.

**Fields:**
- `name`: Column name
- `chat_ids`: List of chat identifiers
- `project_id`: Associated project identifier

## Knowledge Management Models

### KnowledgeSearch
Configures search parameters for project knowledge retrieval.

**Fields:**
- `search_term`: Search query string
- `search_type`: Type of search to perform
- `document_search_type`: Specific document search type
- `document_count`: Maximum documents to return
- `document_cutoff_score`: Score threshold for results
- `document_cutoff_rag`: RAG-specific cutoff threshold

### KnowledgeReloadPath
Specifies a path for reloading knowledge sources.

**Fields:**
- `path`: File or directory path

### KnowledgeDeleteSources
Identifies sources to remove from knowledge base.

**Fields:**
- `sources`: List of source identifiers to delete

### Document
Represents a document in the knowledge base.

**Fields:**
- `id`: Unique document identifier
- `page_content`: Document content text
- `metadata`: Additional document metadata as dictionary

## Tool Models

### Tool
Base definition for tools available to agents.

**Fields:**
- `name`: Tool name
- `description`: Tool functionality description

### CodxJuniorBaseTools
Default tools provided by Codx Junior.

**Fields:**
- `knowledge`: Knowledge search tool

### CommandTool
Extended tool definition with command execution capability.

**Fields:**
- `command`: Optional command string to execute

## Project Configuration Models

### ProjectScript
Defines executable scripts within a project.

**Fields:**
- `name`: Script name
- `description`: Script description
- `script`: Bash script content
- `status`: Execution status (running, stopped, error)
- `background`: Run in background mode
- `restart`: Auto-restart on failure
- `pid_file_path`: Process ID file location
- `engine`: Script execution engine (default: 'bash')

### Bookmark
Quick access bookmark for project resources.

**Fields:**
- `name`: Bookmark name
- `icon`: Optional icon identifier
- `title`: Optional display title
- `url`: Optional resource URL
- `port`: Optional port number

## AI Provider Settings Models

### OpenAISettings
Configuration for OpenAI API integration.

**Fields:**
- `openai_api_url`: API endpoint URL
- `openai_api_key`: API authentication key
- `openai_model`: Model identifier (default: 'gpt-4o')

### AnthropicAISettings
Configuration for Anthropic Claude API integration.

**Fields:**
- `anthropic_api_url`: API endpoint URL
- `anthropic_api_key`: API authentication key
- `anthropic_model`: Model identifier (default: 'claude-3-5-sonnet-20240620')

### MistralAISettings
Configuration for Mistral AI API integration.

**Fields:**
- `mistral_api_url`: API endpoint URL
- `mistral_api_key`: API authentication key
- `mistral_model`: Model identifier (default: 'codestral-latest')

## Agent and Workflow Models

### AgentSettings
Configures agent behavior parameters.

**Fields:**
- `max_agent_iteractions`: Maximum iterations per agent execution (default: 4)

### Plugin
Defines a loadable plugin extending Codx Junior functionality.

**Fields:**
- `plugin_id`: Unique plugin identifier
- `name`: Plugin name
- `description`: Plugin purpose description
- `module_path`: Python module path
- `plugin_path`: Plugin file path
- `method`: Entry point method name
- `arguments`: List of `PluginArgument` configuration
- `roles`: User roles with access permissions
- `extends`: List of extended components
- `image`: Optional plugin image/icon URL
- `async_`: Asynchronous execution flag

### PluginArgument
Configuration parameter for plugin methods.

**Fields:**
- `name`: Argument name
- `description`: Argument purpose
- `default_value`: Default value if not provided

## Integration Models

### GitSettings
Git configuration for project integration.

**Fields:**
- `username`: Git username
- `email`: Git user email

### OAuthProvider
OAuth provider configuration.

**Fields:**
- `name`: Provider name
- `client_id`: OAuth client identifier
- `secret`: Client secret key
- `token_url`: Token endpoint URL

### LiveEdit
Real-time collaborative editing configuration.

**Fields:**
- `chat_name`: Associated chat session
- `html`: HTML content being edited
- `url`: Content URL
- `message`: Associated message text

## Global Settings

### GlobalSettings
Master configuration model for Codx Junior instance.

**Key Sections:**

**AI Configuration:**
- `log_ai`: Enable AI activity logging
- `embeddings_model`: Model for embeddings (default: OLLAMA_EMBEDDINGS_MODEL)
- `llm_model`: Primary language model
- `rag_model`: RAG-specific model
- `wiki_model`: Wiki documentation model

**System Configuration:**
- `projects_root_path`: Root directory for projects
- `enable_file_manager`: Enable file management features
- `log_ignore`: Log entries to ignore
- `codx_junior_avatar`: System avatar URL

**User Management:**
- `users`: List of authorized users (default: admin user)
- `user_logins`: User login history
- `secret`: Encryption secret

**Workspace Management:**
- `workspaces`: Available workspaces
- `workspace_start_port`: Port range start (default: 16000)
- `workspace_end_port`: Port range end (default: 17000)
- `workspace_docker_settings`: Docker configuration for workspaces

**Extension Points:**
- `ai_providers`: Configured AI providers
- `ai_models`: Available AI models
- `oauth_providers`: OAuth integrations
- `plugins`: Loaded plugins
- `project_scripts`: Executable project scripts
- `bookmarks`: Quick-access bookmarks

**Chat Configuration:**
- `chat_global_instructions`: Default instructions for chat sessions

**Environment:**
- `env`: Environment variables dictionary

## UI Models

### PRView
Pull request view configuration.

**Fields:**
- `from_branch`: Source branch name
- `to_branch`: Target branch name

### Screen
Display resolution settings.

**Fields:**
- `resolution`: Current resolution
- `resolutions`: List of supported resolutions (13 common options provided)

## Dependencies
**Imports from:** codx/junior/model/user.py, codx/junior/model/ai_model.py, codx/junior/model/profile.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/ai/ai.py, codx/junior/ai/llmfactory.py, codx/junior/ai/openai_ai.py, codx/junior/ai/vllm_cpu_ai.py, codx/junior/ai/wallet_check.py, codx/junior/api/__init__.py, codx/junior/api/analytics.py, codx/junior/api/github.py, codx/junior/api/global_settings.py, codx/junior/api/knowledge.py, codx/junior/api/logs.py, codx/junior/api/projects.py, codx/junior/api/users.py, codx/junior/api/views.py, codx/junior/api/wiki.py, codx/junior/api/workspaces.py, codx/junior/app.py, codx/junior/chat/chat_engine.py, codx/junior/context.py, codx/junior/db.py, codx/junior/engine/file_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/session.py, codx/junior/global_settings.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_db.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/mentions/mention_manager.py, codx/junior/plugins/plugin_manager.py, codx/junior/profiles/profile_manager.py, codx/junior/project/project_discover.py, codx/junior/project/project_manager.py, codx/junior/settings.py, codx/junior/tools/project_tools.py, codx/junior/utils/chat_utils.py, codx/junior/wiki/wiki_domains.py, codx/junior/wiki/wiki_manager.py, codx/junior/workspace/workspace_manager.py