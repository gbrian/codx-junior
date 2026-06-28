# KnowledgeDB

The `KnowledgeDB` module provides a management system for a Milvus-backed hybrid knowledge base tailored for individual projects. It facilitates both lexical (full-text) and semantic (vector) search, utilizing a hybrid retrieval approach.

## Overview
Each project is assigned a unique collection in Milvus, derived from the project's directory path. To optimize performance and avoid costly full-database scans, the system maintains a local JSON `source-map` file (located at `<db_path>/<index_name>_file.json`) that acts as the source of truth for administrative tasks like listing sources or categories.

## Retrieval Strategies
The system supports three distinct search strategies:
*   **Sparse Search (`search_sparse`)**: Performs BM25 full-text lexical search using the sparse vector index.
*   **Vector Search (`search_vector`)**: Performs semantic search by comparing dense embedding vectors using Cosine similarity.
*   **Hybrid Search (`search_hybrid`)**: Combines both sparse and dense retrieval methods, fused using either Reciprocal Rank Fusion (RRF) or a weighted ranker.

## Key Components

### Database Management
*   **Connection Handling**: The system manages connections to the Milvus server via `get_milvus_client()`.
*   **Initialization**: The `create_db` method sets up the schema, including fields for `page_content`, `metadata`, `sparse` (BM25), and `dense` (Float Vector).
*   **Indexing**: `index_documents` processes `LangChain` documents, generating dense embeddings and triggering the Milvus-native BM25 function.
*   **Maintenance**: `reset` drops the collection and recreates it from scratch, while `delete_documents` removes records by source path.

### Source-Map Helpers
The `source-map` provides a performant interface for querying metadata without hitting the database.
*   **Synchronization**: The system ensures the source-map remains in sync with the database via `_upsert_source_map_entries` and `_remove_source_map_entries` during index and delete operations.
*   **Bootstrapping**: If the source-map is missing or outdated, `_init_source_map_from_db` performs a one-time scan to reconstruct the file.
*   **Utility Methods**: `get_all_sources()` and `get_all_categoties()` retrieve metadata directly from the static file.

### Metrics and Info
*   **`get_collection_metrics`**: Aggregates comprehensive data regarding the current state of the collection, including row counts, index configuration (BM25 and Autoindex), partition information, and load status.
*   **`get_db_info`**: Returns high-level collection statistics and configuration details.

## Implementation Details
*   **Embeddings**: Uses `LocalEmbeddingsModel` (defaulting to "all-MiniLM-L6-v2") for dense vector generation.
*   **Hybrid Fusing**: The `search_hybrid` method enables over-fetching from individual search legs to improve the quality of the fused results returned to the user.
*   **Relevance Scoring**: All search methods automatically inject a `score` into the document's metadata, representing the relevance distance calculated by the underlying Milvus search engine.

---
### References
*   *Section: KnowledgeDB Class Definition & Diagram*
*   *Section: Source-map helpers*
*   *Section: Search strategies*
*   *Section: Embedding helpers*

## Dependencies
**Imports from:** codx/junior/model/model.py, codx/junior/ai/__init__.py, codx/junior/settings.py, codx/junior/knowledge/embeddings.py, codx/junior/utils/utils.py, codx/junior/profiling/profiler.py
**Imported by:** codx/junior/api/db_router.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_wiki.py, codx/junior/wiki/wiki_domains.py, codx/junior/wiki/wiki_index.py, codx/junior/wiki/wiki_manager.py