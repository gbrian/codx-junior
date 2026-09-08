# CODX Junior Settings

## Overview

The `CODXJuniorSettings` class is a Pydantic BaseModel that manages project configuration and settings for CODX Junior. It handles database storage, AI model settings, knowledge management, and project-specific configurations.

## Core Properties

### Project Identity
- **project_id**: Unique identifier for the project (auto-generated UUID if not provided)
- **project_name**: Human-readable name of the project
- **project_path**: Relative or absolute path to the project directory
- **abs_project_path**: Computed absolute path to the project
- **codx_path**: Path to the .codx settings directory

### Project Structure
- **project_branches**: List of available git branches
- **project_wiki**: Enable/disable project wiki functionality
- **project_wiki_path**: Custom path for wiki storage
- **project_preview_url**: URL for project preview
- **repo_url**: Remote repository URL
- **is_git_root**: Boolean indicating if project is a git repository root

### Knowledge Management
- **use_knowledge**: Enable/disable knowledge base usage
- **knowledge_search_type**: Search algorithm type (default: "similarity")
- **knowledge_search_document_count**: Number of documents to retrieve (default: 10)
- **knowledge_extract_document_tags**: Enable tag extraction from documents
- **knowledge_enrich_documents**: Enable document enrichment
- **knowledge_context_cutoff_relevance_score**: Relevance threshold (default: 0.9)
- **knowledge_context_rag_distance**: RAG distance threshold (default: 0.4)
- **knowledge_external_folders**: Comma-separated external folders for knowledge
- **knowledge_query_subprojects**: Query sub-projects in knowledge search
- **knowledge_file_ignore**: Files to ignore during knowledge extraction (default: ".codx")
- **knowledge_hnsw_M**: HNSW index parameter (default: 1024)
- **knowledge_generate_training_dataset**: Generate training datasets from knowledge

### AI Model Configuration
- **llm_model**: Language model identifier
- **embeddings_model**: Embeddings model identifier
- **rag_model**: RAG-specific model identifier
- **wiki_model**: Wiki generation model identifier
- **image_generation_model**: Image generation model identifier
- **image_vision_model**: Image vision/analysis model identifier

### Image Settings
- **image_storage_folder**: Directory for generated images (default: "images/generated")
- **image_max_file_size_mb**: Maximum image file size in MB (default: 100)

### Additional Settings
- **project_scripts**: List of ProjectScript objects for automation
- **project_dependencies**: Comma-separated project dependencies
- **mcp_servers**: List of configured MCP servers
- **watching**: Monitor project for changes
- **save_mentions**: Store AI mentions/interactions
- **log_ignore**: Patterns to ignore in logging
- **last_access_time**: Timestamp of last project access
- **last_error**: Most recent error message
- **urls**: Associated URLs

## Key Methods

### Configuration Loading
- **from_codx_path(codx_path)**: Load settings from .codx directory
- **from_project_file(project_file_path)**: Load settings from project.json file
- **from_json(settings)**: Create settings from dictionary

### Configuration Saving
- **save_project()**: Persist settings to project.json file

### AI Settings Retrieval
- **get_llm_settings(llm_model)**: Get AI settings for language model
- **get_embeddings_settings()**: Get AI settings for embeddings model
- **get_image_generation_settings()**: Get AI settings for image generation
- **get_image_vision_settings()**: Get AI settings for image vision

### MCP Server Management
- **get_active_mcp_servers()**: Retrieve active MCP servers
- **get_mcp_server_by_name(name)**: Find MCP server by name

### Image Capabilities
- **is_image_generation_enabled()**: Check if image generation is configured
- **is_image_vision_enabled()**: Check if image vision is configured

### Project Validation
- **is_valid_project()**: Verify project has valid AI settings
- **is_valid_project_file(file_path)**: Check if file should be processed based on ignore patterns

### Knowledge & Utilities
- **get_ignore_patterns()**: Retrieve file patterns to exclude from processing
- **get_sub_projects()**: Find nested projects within this project
- **get_sub_projects_paths()**: Get absolute paths of sub-projects
- **get_project_dependencies()**: Parse and return dependencies list
- **get_project_wiki_path()**: Get absolute wiki directory path
- **get_valid_keys()**: Get all valid configuration keys (excludes computed properties)
- **get_dbs()**: Initialize database connections
- **get_ai()**: Initialize AI interface
- **get_agent_max_iterations()**: Get maximum agent iterations from global settings
- **get_project_ai_models()**: Retrieve available AI models
- **get_wiki_model()**: Get wiki model (project or global fallback)
- **get_rag_model()**: Get RAG model (project or global fallback)
- **get_project_workspaces()**: Get workspaces containing this project
- **get_log_ai()**: Get AI logging configuration from global settings

## Computed Properties

The following properties are computed and excluded from file persistence:
- codx_path
- metrics
- users
- is_git_root

## Project Extension

**CODXJuniorProject** extends `CODXJuniorSettings` with additional properties:
- **metrics**: Dictionary of project metrics
- **workspaces**: List of workspace configurations
- **users**: List of project users
- **permissions**: Permission string configuration

## Dependencies
**Imports from:** codx/junior/global_settings.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/__init__.py
**Imported by:** codx/junior/ai/ai.py, codx/junior/ai/llmfactory.py, codx/junior/ai/openai_ai.py, codx/junior/ai/vllm_cpu_ai.py, codx/junior/app.py, codx/junior/chat/chat_engine.py, codx/junior/chat/chat_knowledge.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/engine/session.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_code_splitter.py, codx/junior/knowledge/knowledge_code_to_dcouments.py, codx/junior/knowledge/knowledge_db.py, codx/junior/knowledge/knowledge_graph.py, codx/junior/knowledge/knowledge_keywords.py, codx/junior/knowledge/knowledge_loader.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_prompts.py, codx/junior/knowledge/knowledge_wiki.py, codx/junior/plugins/plugin_manager.py, codx/junior/profiles/profile_manager.py, codx/junior/project/project_discover.py, codx/junior/project/project_manager.py, codx/junior/search/project_search_manager.py, codx/junior/security/user_management.py, codx/junior/tools/code_writer.py, codx/junior/tools/project_tools.py, codx/junior/utils/chat_utils.py, codx/junior/views/view_manager.py, codx/junior/wiki/wiki_domains.py, codx/junior/wiki/wiki_index.py, codx/junior/wiki/wiki_manager.py, tests/db/test_db.py, tests/mention_manager/test_mention_manager.py, tests/wiki_manager/test_wiki_manager.py