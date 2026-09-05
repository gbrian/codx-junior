# Settings and Configuration

## Overview

The `settings.py` module provides core configuration management for CODX Junior projects. It defines the `CODXJuniorSettings` class, which serves as the central data model for project-specific settings and configuration parameters.

## CODXJuniorSettings Class

### Purpose

`CODXJuniorSettings` is a Pydantic BaseModel that manages all project configuration, including:
- Project metadata and paths
- Knowledge base and RAG (Retrieval-Augmented Generation) settings
- AI model configurations
- MCP (Model Context Protocol) servers
- Project scripts and dependencies
- File storage and access tracking

### Key Fields

#### Project Identification
- `project_id`: Unique identifier for the project (auto-generated UUID if not provided)
- `project_name`: Human-readable project name
- `project_path`: Relative or absolute path to the project directory
- `abs_project_path`: Computed absolute path to the project

#### File and Path Management
- `codx_path`: Path to the `.codx` configuration directory
- `project_branches`: List of git branches associated with the project
- `project_wiki`: Boolean flag to enable/disable project wiki
- `project_wiki_path`: Path to wiki documentation
- `knowledge_file_ignore`: Comma-separated file patterns to exclude from knowledge base

#### Knowledge Base Configuration
- `knowledge_extract_document_tags`: Extract tags from documents
- `knowledge_search_type`: Search algorithm type (default: "similarity")
- `knowledge_search_document_count`: Number of documents to retrieve (default: 10)
- `knowledge_enrich_documents`: Enable document enrichment
- `knowledge_context_cutoff_relevance_score`: Minimum relevance threshold (default: 0.9)
- `knowledge_context_rag_distance`: RAG distance metric (default: 0.4)
- `knowledge_external_folders`: External folders to include in knowledge base
- `knowledge_hnsw_M`: HNSW index parameter (default: 1024)

#### AI Model Settings
- `embeddings_model`: Model for generating embeddings
- `llm_model`: Primary language model
- `rag_model`: Model for RAG operations
- `wiki_model`: Model for wiki generation

#### Additional Configuration
- `mcp_servers`: List of configured MCP servers with enable/disable status
- `project_scripts`: Custom scripts associated with the project
- `project_dependencies`: Comma-separated project dependencies
- `is_git_root`: Boolean indicating if project root contains `.git` directory
- `repo_url`: Repository URL
- `last_access_time`: Timestamp of last project access
- `last_error`: Most recent error message

### Computed Properties

The following fields are computed and not persisted to storage:
- `codx_path`
- `metrics`
- `users`
- `is_git_root`

## Core Methods

### Configuration Loading

#### `from_project_file(project_file_path)`
Loads settings from a project JSON file. This method:
- Reads configuration from the `project.json` file
- Normalizes project paths (handles both absolute and relative paths)
- Auto-generates project ID if missing
- Detects git repository status
- Returns a fully configured `CODXJuniorSettings` instance

```
Usage: settings = CODXJuniorSettings.from_project_file("/path/to/.codx/project.json")
```

#### `from_codx_path(codx_path)`
Convenience method that loads settings from a `.codx` directory path.

#### `from_json(settings_dict)`
Creates settings instance from a dictionary.

### Configuration Saving

#### `save_project()`
Persists project settings to the project JSON file. This method:
- Ensures the `.codx` directory exists
- Auto-generates project ID if not set
- Filters out computed properties before saving
- Returns a freshly loaded `CODXJuniorSettings` instance
- Intelligently determines whether to store `project_path` as custom

### AI and Model Configuration

#### `get_llm_settings(llm_model)`
Retrieves AI settings for a specified language model. Falls back to project default, then global default.

#### `get_embeddings_settings()`
Retrieves AI settings for the embeddings model.

#### `get_rag_model()`
Returns the RAG model, falling back to global settings if not configured.

#### `get_wiki_model()`
Returns the wiki model, falling back to global settings if not configured.

#### `get_agent_max_iterations()`
Retrieves maximum agent iterations from global settings.

### MCP Server Management

#### `get_active_mcp_servers()`
Returns a filtered list of only the active (enabled) MCP servers.

#### `get_mcp_server_by_name(name)`
Retrieves a specific MCP server configuration by name. Returns `None` if not found.

### Project Structure

#### `get_sub_projects()`
Recursively discovers sub-projects within the project directory by searching for nested `.codx/project.json` files.

#### `get_sub_projects_paths()`
Returns a list of absolute paths for all sub-projects.

#### `get_project_workspaces()`
Retrieves workspaces from global settings that reference this project.

### Knowledge Base and File Handling

#### `get_ignore_patterns()`
Builds a comprehensive list of file patterns to exclude from knowledge base indexing. Includes:
- Git directories (`.git`)
- Node modules (`node_modules`)
- Project wiki path
- Custom patterns from `knowledge_file_ignore`
- Sub-project paths

#### `is_valid_project_file(file_path)`
Determines whether a file should be included in the knowledge base by checking against ignore patterns.

#### `get_project_dependencies()`
Parses and returns project dependencies as a list (splits comma-separated string).

### Database and AI Access

#### `get_dbs()`
Initializes and returns database instances configured for this project.

#### `get_ai()`
Initializes and returns AI/LLM instances configured for this project.

## CODXJuniorProject Class

`CODXJuniorProject` extends `CODXJuniorSettings` with additional fields for multi-user and workspace support:
- `metrics`: Project metrics and statistics
- `workspaces`: Associated workspace configurations
- `users`: List of users with project access
- `permissions`: Permission configuration string

## Validation

### `is_valid_project()`
Validates that the project has properly configured AI settings by checking:
- LLM settings contain an API URL, OR
- LLM provider is set to 'llmfactory'

### `get_valid_keys()`
Returns all serializable field names, excluding computed properties.

## Project File Format

Settings are persisted to `{codx_path}/project.json` as a JSON file containing only non-computed properties. The file structure allows for:
- Manual configuration editing
- Version control friendly serialization
- Backward compatibility

## Dependencies
**Imports from:** codx/junior/global_settings.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/__init__.py
**Imported by:** codx/junior/ai/ai.py, codx/junior/ai/llmfactory.py, codx/junior/ai/openai_ai.py, codx/junior/ai/vllm_cpu_ai.py, codx/junior/app.py, codx/junior/chat/chat_engine.py, codx/junior/chat/chat_knowledge.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/engine/session.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_code_splitter.py, codx/junior/knowledge/knowledge_code_to_dcouments.py, codx/junior/knowledge/knowledge_db.py, codx/junior/knowledge/knowledge_graph.py, codx/junior/knowledge/knowledge_keywords.py, codx/junior/knowledge/knowledge_loader.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_prompts.py, codx/junior/knowledge/knowledge_wiki.py, codx/junior/plugins/plugin_manager.py, codx/junior/profiles/profile_manager.py, codx/junior/project/project_discover.py, codx/junior/project/project_manager.py, codx/junior/search/project_search_manager.py, codx/junior/security/user_management.py, codx/junior/tools/code_writer.py, codx/junior/tools/project_tools.py, codx/junior/utils/chat_utils.py, codx/junior/views/view_manager.py, codx/junior/wiki/wiki_domains.py, codx/junior/wiki/wiki_index.py, codx/junior/wiki/wiki_manager.py, tests/db/test_db.py, tests/mention_manager/test_mention_manager.py, tests/wiki_manager/test_wiki_manager.py