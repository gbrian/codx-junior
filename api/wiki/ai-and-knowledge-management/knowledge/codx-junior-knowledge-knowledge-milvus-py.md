# Knowledge Class Documentation

The `Knowledge` class acts as the central orchestrator for managing, indexing, and querying project-related information within the `codx-api` system. It bridges the gap between the local file system and the database, utilizing AI-driven processes to enrich documentation, summarize content, and maintain project context.

## Overview
The class manages a knowledge base that tracks project files, maintains a project-wide summary, and facilitates semantic search. It integrates with `KnowledgeDB` for storage, `AI` for natural language processing, and `KnowledgeLoader` for file system interactions.

## Key Features

### 1. Document Indexing and Enrichment
Documents are processed through an enrichment pipeline before being indexed:
- **Enrichment (`enrich_document`):** Generates AI-based summaries, keyword extraction, category classification, and content graph structures.
- **Training Dataset Generation:** Optionally generates training samples based on document content for model fine-tuning.
- **Parallel Processing (`parallel_enrich`):** Leverages thread pools to process multiple documents concurrently, supporting progress callbacks to report status (enrichment stage, indexing status, and completion).

### 2. Project Summary Management
The system maintains an evolving `project_summary.md` file:
- **Incremental Updates:** Instead of full re-processing, the system uses the `build_project_summary` method to update the summary based on newly added or deleted source files.
- **Purpose:** Acts as a high-level overview for LLMs, assisting in project structure navigation and effective retrieval.

### 3. Change Tracking and Intelligence
- **Change Detection (`detect_changes`):** Identifies updated, added, or removed files within the repository.
- **Code Change Summarization (`build_code_changes_summary`):** Accepts unified diff strings and uses AI to generate human-readable reports detailing file changes, improvements, and relevant snippets.

### 4. Search and Retrieval
- **Semantic Search:** Interfaces with the underlying database to perform queries.
- **Contextual Search:** Automatically includes non-indexed file paths if they match the query string, ensuring visibility for all repository files.
- **Query Intelligence:** The `extract_query_keywords` method analyzes user input to generate relevant tags (`TAG_*`), improving retrieval precision.

## Life Cycle Methods
- **`reload`:** Refreshes the knowledge base by loading file system changes and re-indexing modified content.
- **`reset`:** Clears the current knowledge database and triggers a forced re-index of all project files by touching them.
- **`clean_deleted_documents`:** Ensures synchronization between the file system and the database by removing entries for files that no longer exist.

## Technical Implementation
- **Concurrency:** Uses `ThreadPoolExecutor` for file loading, parallel document enrichment, and repository updates to maintain responsiveness.
- **Persistence:** Relies on `KnowledgeDB` for storing vector and metadata indices.
- **Callback Pattern:** Implements an asynchronous `ProgressCallback` system to communicate status events (`DOCUMENT_PROCESSING`, `DOCUMENT_ENRICHED`, `DOCUMENT_INDEXED`, `COMPLETED`) to UI or CLI components.

## Configuration
The class is initialized with a `CODXJuniorSettings` object, which governs:
- **Ignored Patterns:** Defines which files/directories are excluded from the knowledge base.
- **AI Models:** Specifies the LLM configurations used for summarization and enrichment.
- **Feature Flags:** Toggles for document enrichment, training dataset generation, and knowledge usage.

---
### References
*   `codx/junior/knowledge/knowledge_milvus.py` (Source)

## Dependencies
**Imports from:** codx/junior/knowledge/knowledge_db.py, codx/junior/model/model.py, codx/junior/engine/progress_callback.py, codx/junior/utils/utils.py, codx/junior/ai/__init__.py, codx/junior/settings.py, codx/junior/knowledge/knowledge_loader.py, codx/junior/knowledge/knowledge_prompts.py, codx/junior/knowledge/knowledge_keywords.py, codx/junior/wiki/wiki_manager.py
**Imported by:** codx/junior/changes/change_manager.py, codx/junior/chat/chat_engine.py, codx/junior/chat/chat_knowledge.py, codx/junior/context.py, codx/junior/engine/code_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/session.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/search/project_search_manager.py, codx/junior/tools/project_tools.py, tests/changes/project_file_watcher/project_file_watcher.py, tests/test_change_manager.py