# Knowledge Management System

## Overview

The `Knowledge` class is a comprehensive document management system for the CODX Junior project. It handles document indexing, enrichment, searching, and summarization using AI-powered processing and a vector database backend.

## Core Functionality

### Initialization

The Knowledge system initializes with project settings and optional progress callbacks:

- **AI Integration**: Lazy-loads an AI instance for RAG model operations
- **Database**: Manages a Milvus-based knowledge database
- **Loaders**: Uses KnowledgeLoader for file discovery and processing
- **Wiki Management**: Integrates with WikiManager for document generation

### Document Loading and Indexing

#### File Discovery
- `get_all_repo_files()`: Retrieves all repository files
- `detect_changes()`: Identifies modified files by filtering empty files and applying ignore patterns
- `is_valid_file()`: Validates files against ignore patterns

#### Document Reloading
- `reload(full=False)`: Asynchronously reloads documents incrementally or completely
  - On full reload, resets the database
  - Loads only changed documents if not full reload
  - Triggers summary building after indexing
  
- `reload_path(path)`: Loads documents from a specific file path with error handling

### Document Enrichment

#### AI-Powered Enhancement
The `enrich_document()` method augments documents with AI-generated metadata:

**Enrichment Fields:**
- **Summary**: 10-line business-focused summarization
- **Keywords**: Hyphen-separated keyword extraction
- **Category**: Automatic document classification
- **Content Graph**: Node and relation representation of content

**Training Data Generation** (optional):
- Creates 10 user request/AI response pairs for model fine-tuning
- Extracted from document content

#### Parallel Processing
`parallel_enrich()` processes multiple documents concurrently using asyncio:
- Provides progress callbacks for each enrichment stage
- Tracks completion rates and errors
- Handles exceptions gracefully with error reporting

### Indexing Pipeline

The `index_documents()` method orchestrates the complete indexing workflow:

1. **Preparation**: Collects unique sources and calculates MD5 checksums
2. **Enrichment**: Parallel AI enrichment of all documents
3. **Cleanup**: Deletes old versions of updated documents
4. **Indexing**: Stores enriched documents in the database with metadata
5. **Summary**: Updates project summary document incrementally

**Progress Tracking**: Reports progress through multiple stages:
- Document processing
- Enrichment progress
- Indexing progress
- Summary generation

### Document Search and Retrieval

#### Search Capabilities
`search(query, search_type='fulltext', limit=100)`:
- Performs full-text search in indexed documents
- Supplements results with file path matches when query appears in filename
- Returns Document objects with source paths

#### Document Loading
`doc_from_project_file(file_path)`: Loads raw document content from project files with metadata

`doc_and_summary(doc)`: Enhances documents with AI-generated summaries in both metadata and content

### Project Summary Management

#### Summary Generation
`build_project_summary(added_sources=None, deleted_sources=None)`:
- Generates concise markdown overview of the entire project
- Updates incrementally based on file changes
- Stored at `project_summary.md` in the CODX path
- Helps LLM models understand project structure and locate relevant files

**Summary Features:**
- Logical grouping of files by folders
- One-line descriptions of key files
- Incorporates added and deleted files
- Based solely on file paths and existing content

#### Summary Access
- `get_project_summary()`: Retrieves current project summary from disk
- Cached locally to reduce AI calls

### Utility Functions

#### Document Management
- `delete_documents(documents=None, sources=None)`: Removes documents from knowledge base and updates summary
- `clean_deleted_documents()`: Identifies and removes documents for deleted files
- `reset()`: Clears database and marks all files for reindexing

#### Keyword and Query Processing
- `extract_query_keywords(query)`: Uses AI to extract search-optimized keywords from queries
- `get_categories()`: Retrieves all document categories from database

#### Status and Information
- `status()`: Returns comprehensive knowledge base status including file count, folders, keywords, and database info
- `get_db_info()`: Provides database-specific information
- `get_all_sources()`: Lists all indexed document sources
- `is_valid_project_file(file_path)`: Validates if a file is in project sources

### Change Summary Generation

`build_code_changes_summary(diff, force=False)`:
- Analyzes unified diff format code changes
- Generates human-friendly reports with file grouping and descriptions
- Caches results in `last_changes_summary.md`
- Can be forced to regenerate despite cache

### Helper Methods

- `get_documents_from_sources(file_paths)`: Creates Document objects from file paths with language detection
- `build_doc_summary(doc)`: Generates AI-powered document summaries with keywords
- `create_wiki_doc(source)`: Generates wiki documentation for source files

## Progress Callback System

The system supports granular progress tracking through callback events:

- `DOCUMENT_PROCESSING`: Stage initialization
- `DOCUMENT_ENRICHED`: Individual document enrichment completion
- `DOCUMENT_INDEXED`: Individual document indexing completion
- `ITERATION_COMPLETE`: Stage completion
- `COMPLETED`: Full process completion

Error events are also reported with context information for debugging and monitoring.

## Database Integration

The system uses KnowledgeDB (Milvus-backed) for:
- Document storage and retrieval
- Vector similarity search
- Metadata management
- Source tracking with MD5 checksums
- Last update timestamps for incremental loading

## Dependencies
**Imports from:** codx/junior/knowledge/knowledge_db.py, codx/junior/model/model.py, codx/junior/engine/progress_callback.py, codx/junior/utils/utils.py, codx/junior/ai/__init__.py, codx/junior/settings.py, codx/junior/knowledge/knowledge_loader.py, codx/junior/knowledge/knowledge_prompts.py, codx/junior/knowledge/knowledge_keywords.py, codx/junior/wiki/wiki_manager.py
**Imported by:** codx/junior/changes/change_manager.py, codx/junior/chat/chat_engine.py, codx/junior/chat/chat_knowledge.py, codx/junior/context.py, codx/junior/engine/code_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/session.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/search/project_search_manager.py, codx/junior/tools/project_tools.py, tests/changes/project_file_watcher/project_file_watcher.py, tests/test_change_manager.py