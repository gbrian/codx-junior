# Model Definitions

This module defines the core data models used throughout the Codx Junior AI and Knowledge Management system. It provides structured representations for users, AI configurations, workspaces, chat management, and system settings.

## Core Imports

The module integrates models from several dedicated sub-modules:

- **User Models**: Authentication and user profile management
- **AI Models**: Provider configurations and language model settings
- **Profile Models**: User profile and API settings
- **Workspace Models**: Workspace and application configurations

## Chat and Content Models

### ChatMessage
Represents a message in a chat conversation with support for multiple content types.

- `role`: Message role (e.g., user, assistant)
- `content`: List of Content items within the message

### Content
Defines individual content elements within a message.

- `type`: Content type (default: 'text')
- `text`: Text content
- `image_url`: Optional image URL reference via ImageUrl object

### ImageUrl
Container for image URLs in messages.

- `url`: The image URL string

## Board and Column Management

### Board
Organizes chat conversations into a kanban-style board structure.

- `name`: Board identifier
- `description`: Board description
- `remote_url`: Optional remote repository URL
- `bookmark`: Toggle for bookmarking the board
- `columns`: List of Column objects
- `project_id`: Associated project identifier

### Column
Represents a column within a Board, grouping related chats.

- `name`: Column name
- `chat_ids`: List of chat identifiers in this column
- `project_id`: Associated project identifier

## Knowledge Management Models

### KnowledgeSearch
Configuration for searching project knowledge base.

- `search_term`: The search query
- `search_type`: Type of search to perform
- `document_search_type`: Specific document search type
- `document_count`: Number of documents to retrieve
- `document_cutoff_score`: Minimum relevance score threshold
- `document_cutoff_rag`: RAG-specific cutoff score

### KnowledgeReloadPath
Specifies a path for reloading knowledge sources.

- `path`: File system path to reload

### KnowledgeDeleteSources
Defines sources for deletion from knowledge base.

- `sources`: List of source identifiers to delete

### Document
Represents a document in the knowledge base.

- `id`: Unique document identifier
- `page_content`: The document content
- `metadata`: Associated metadata dictionary

## Tool and Agent Models

### Tool
Base definition for available tools.

- `name`: Tool identifier
- `description`: Tool description

### CommandTool
Extended tool definition supporting command execution.

- `command`: Optional command string to execute
- Inherits `name` and `description` from Tool

### CodxJuniorBaseTools
Defines default tools available to agents.

- `knowledge`: Tool for searching project knowledge base

### AgentSettings
Configuration for agent behavior.

- `max_agent_iteractions`: Maximum number of agent iterations (default: 4)

## Development and Integration Models

### ProjectScript
Defines scripts for project automation and background tasks.

- `name`: Script identifier
- `description`: Script purpose
- `script`: Bash script content
- `status`: Current status (running, stopped, error)
- `background`: Whether script runs in background
- `restart`: Auto-restart on failure
- `pid_file_path`: Process ID file location
- `engine`: Script engine (default: bash)

### Tool Models
- **Tool**: Base tool configuration with name and description
- **CommandTool**: Tool that executes system commands

### PRView
Pull request visualization configuration.

- `from_branch`: Source branch
- `to_branch`: Target branch

### LiveEdit
Real-time document editing capabilities.

- `chat_name`: Associated chat identifier
- `html`: HTML content
- `url`: Document URL
- `message`: Edit message or description

## Provider Configuration Models

### OpenAISettings
OpenAI API configuration.

- `openai_api_url`: API endpoint URL
- `openai_api_key`: Authentication key
- `openai_model`: Model selection (default: gpt-4o)

### AnthropicAISettings
Anthropic Claude API configuration.

- `anthropic_api_url`: API endpoint URL
- `anthropic_api_key`: Authentication key
- `anthropic_model`: Model selection (default: claude-3-5-sonnet-20240620)

### MistralAISettings
Mistral AI API configuration.

- `mistral_api_url`: API endpoint URL
- `mistral_api_key`: Authentication key
- `mistral_model`: Model selection (default: codestral-latest)

### GitSettings
Git configuration for version control.

- `username`: Git username
- `email`: Git user email

## Plugin and Extension Models

### Plugin
Defines extensible plugin functionality.

- `plugin_id`: Unique plugin identifier
- `name`: Display name
- `description`: Plugin description
- `module_path`: Python module path
- `plugin_path`: Plugin file path
- `method`: Entry point method name
- `arguments`: List of PluginArgument definitions
- `roles`: List of user roles that can use plugin
- `extends`: List of extension points
- `image`: Optional plugin icon/image URL
- `async_`: Whether plugin executes asynchronously (aliased as `async`)

### PluginArgument
Defines plugin function arguments.

- `name`: Argument name
- `description`: Argument description
- `default_value`: Default argument value

## OAuth and Security Models

### OAuthProvider
OAuth provider configuration for authentication.

- `name`: Provider name
- `client_id`: OAuth client identifier
- `secret`: OAuth client secret
- `token_url`: Token endpoint URL

## MCP Server Model

### MCPServer
Model Context Protocol (MCP) server configuration for extended capabilities.

- `name`: Server name
- `url`: Server endpoint URL
- `api_key`: Optional authentication key
- `active`: Whether the server is enabled

## Logging and Analytics Models

### Logprobs
Token probability information from language models.

- `tokens`: List of generated tokens
- `token_logprobs`: Log probability for each token
- `top_logprobs`: Top alternative log probabilities per token
- `text_offset`: Character offset for each token

## User Interface Models

### Bookmark
Quick access bookmark for important resources.

- `name`: Bookmark identifier
- `icon`: Optional icon identifier
- `title`: Display title
- `url`: Target URL
- `port`: Optional port number for local services

### Screen
Display resolution configuration.

- `resolution`: Current resolution setting
- `resolutions`: List of supported resolutions (13 predefined options from 640x480 to 1920x1200)

## Global System Configuration

### GlobalSettings
Comprehensive system-wide configuration model containing:

**AI Configuration**
- `log_ai`: Enable AI logging
- `embeddings_model`: Embedding model selection
- `llm_model`: Large language model selection
- `rag_model`: RAG-specific model
- `wiki_model`: Wiki knowledge model

**System Paths and Files**
- `projects_root_path`: Root directory for projects
- `log_ignore`: List of patterns to ignore in logging

**User and Access**
- `users`: List of system users
- `user_logins`: User login history
- `secret`: Encryption secret
- `oauth_providers`: OAuth provider configurations

**Workspace Management**
- `workspaces`: Available workspaces
- `workspace_start_port`: Port range start for workspace services
- `workspace_end_port`: Port range end for workspace services
- `workspace_docker_settings`: Docker configuration for workspaces

**Extensions and Features**
- `plugins`: Available plugin list
- `ai_providers`: Configured AI providers
- `ai_models`: Available AI models
- `project_scripts`: Automation scripts

**User Interface**
- `codx_junior_avatar`: System avatar URL
- `enable_file_manager`: File manager feature toggle
- `bookmarks`: Quick access bookmarks

**Chat Configuration**
- `chat_global_instructions`: Default system instructions for chat

## Dependencies
**Imports from:** codx/junior/model/user.py, codx/junior/model/ai_model.py, codx/junior/model/profile.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/ai/ai.py, codx/junior/ai/llmfactory.py, codx/junior/ai/openai_ai.py, codx/junior/ai/vllm_cpu_ai.py, codx/junior/ai/wallet_check.py, codx/junior/api/__init__.py, codx/junior/api/analytics.py, codx/junior/api/github.py, codx/junior/api/global_settings.py, codx/junior/api/knowledge.py, codx/junior/api/logs.py, codx/junior/api/projects.py, codx/junior/api/users.py, codx/junior/api/views.py, codx/junior/api/wiki.py, codx/junior/api/workspaces.py, codx/junior/app.py, codx/junior/chat/chat_engine.py, codx/junior/context.py, codx/junior/db.py, codx/junior/engine/file_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/session.py, codx/junior/global_settings.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_db.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/mentions/mention_manager.py, codx/junior/plugins/plugin_manager.py, codx/junior/profiles/profile_manager.py, codx/junior/project/project_discover.py, codx/junior/project/project_manager.py, codx/junior/settings.py, codx/junior/tools/project_tools.py, codx/junior/utils/chat_utils.py, codx/junior/wiki/wiki_domains.py, codx/junior/wiki/wiki_manager.py, codx/junior/workspace/workspace_manager.py