# KnowledgeDB Implementation Guide

The `KnowledgeDB` class provides a sophisticated management layer for storing, indexing, and retrieving project knowledge using a hybrid architecture within Milvus. It combines traditional full-text searching with modern semantic vector search for superior retrieval accuracy.

## ⚙️ Overview

**Project Goal:** To manage a centralized, searchable repository of documents (sources) assigned to a specific code project.
**Backend Technology:** Milvus and local filesystem (for source-map persistence).
**Key Feature:** Hybrid Search, which fuses the results from two distinct search methodologies:
1. **Sparse Vectors (BM25):** For lexical (keyword-based) full-text matches.
2. **Dense Vectors (Embeddings):** For semantic similarity based on meaning.

### Core Data Fields

The knowledge base maintains a schema derived from constants like `KNOWLEDGE_FIELDS`:

| Field Name | Datatype | Description | Purpose in Search |
| :--- | :--- | :--- | :--- |
| `page_content` | VARCHAR | The primary text content of the document. | Input for BM25 and embedding generation. |
| `source` | VARCHAR | The absolute path to the source document (Unique identifier). | Used for filtering, deletion, and source-map keying. |
| `keywords` | VARCHAR | Comma-separated list of keywords extracted from the file. | Metadata enrichment. |
| `category` | VARCHAR | Assigned category (e.g., "API", "Frontend"). | Metadata grouping and filtering. |
| `last_update` | INT32 | Unix timestamp of when the source was last updated. | Tracking data freshness in the source-map. |
| `sparse` | SPARSE\_FLOAT\_VECTOR | The BM25 sparse embedding vector. | Used by `search_sparse`. |
| `dense` | FLOAT\_VECTOR | The semantic embedding vector for general meaning. | Used by `search_vector` and `search_hybrid`. |

The class utilizes a lightweight JSON **Source-map** (`<db_path>/<index_name>_file.json`) file as the single source of truth for metadata (sources, categories) to prevent unnecessary database queries when listing available content.

## 🛠️ Initialization and Setup

### `__init__(settings)`
Initializes a new `KnowledgeDB` instance using project settings (`CODXJuniorSettings`).

**Actions During Initialization:**
1. **Path Setup:** Creates structured paths for the Milvus database collection (`self.index_fulltext_name`) within the designated storage directory.
2. **Embeddings Model:** Initializes the `LocalEmbeddingsModel`, defaulting to `all-MiniLM-L6-v2`.
3. **Connection:** Calls `connect_db()` and ensures the Milvus collections are present via `create_db()`.

### `create_db()`
This method handles collection schema setup in Milvus, ensuring the necessary components exist:

*   **Schema Definition:** Sets up fields according to `KNOWLEDGE_FIELDS` and adds the required `FIELD_SPARSE` (for BM25) and `FIELD_DENSE` (for embeddings).
*   **Function Creation:** Adds the built-in Milvus function `text_bm25_emb` which populates the sparse vector field.
*   **Indexing:** Creates two primary indexes on the collection:
    1.  **Sparse Index:** Uses `SPARSE_INVERTED_INDEX` with BM25 metrics (`DAAT_MAXSCORE`, `bm25_k1`: 1.2, `bm25_b`: 0.75). (Lexical Search)
    2.  **Dense Index:** Uses `AUTOINDEX` with the **COSINE** metric. (Semantic Search)

## ✨ Core Functionality and Search Strategies

All search methods return a list of `Document` objects, and when relevance scoring is active, the score is included in the returned document's metadata under `score`.

### 1. Indexing Documents

#### `index_documents(documents: List[Document])`
This function handles inserting or updating documents into the database. It performs several critical steps:

1. **Content Aggregation:** Concatenates content from multiple potential fields (`source`, `page_content`, `summary`, `tags`) to create the single text bloc used for search (`page_content`).
2. **Embedding Generation:** Generates dense embedding vectors for all documents in a batch using `self._embed_documents()`.
3. **Milvus Upsert:** Inserts the processed data, including both the pre-calculated `dense` vector and relying on Milvus to calculate/store the `sparse` BM25 representation automatically.
4. **Source-Map Sync:** Crucially, it calls **`_upsert_source_map_entries()`** which updates the local JSON source-map file. This keeps external tools synchronized with the knowledge base status without hitting the database again.

### 2. Retrieval Methods (Search)

#### `search_sparse(query: str)`
Performs a pure **lexical search**. It translates the query into a request against the BM25 sparse vector field and returns results ranked by the BM25 score.

*   ***Best for:*** "Find all documents containing the phrase 'Kubernetes load balancer'."

#### `search_vector(query: str)`
Performs pure **semantic search**. It embeds the query using `self._embed_query()` and searches against the dense vector field using a COSINE similarity metric.

*   ***Best for:*** "What design patterns are used to decouple application services?" (even if those exact words aren't in the source, the meaning might match).

#### `search_hybrid(query: str, use_rrf: bool = True)`
The primary method. It performs a combined search for maximum relevance by executing two separate searches (sparse and dense) and fusing their rankings.

*   **Fusion Logic:**
    *   If `use_rrf` is `True`, it uses **Reciprocal Rank Fusion (RRFRanker)**, which is typically preferred for combining ranked lists.
    *   Otherwise, it uses a customizable **WeightedRanker** based on provided weights (`sparse_weight`, `dense_weight`).

#### `search(query: str)`
The generic default entry point. It serves as an alias to `search_hybrid()` and is recommended for general usage when developers want the best overall relevance score.

### 3. Metadata Management

| Method | Purpose | Data Source | Outcome |
| :--- | :--- | :--- | :--- |
| **`get_all_sources()`** | Retrieves all indexed source paths (Source $\rightarrow$ Metadata mapping). | Reads locally from the static source-map JSON file. | Returns a dictionary where keys are source paths and values are dummy `Document` objects containing metadata (last update, category, keywords). |
| **`get_all_categoties()`** | Retrieves all known categories. | Reads locally from the static source-map JSON file (`categories` list). | Returns a sorted `List[str]` of unique, deduplicated category names. |
| **`delete_documents(sources: List[str])`** | Removes content corresponding to specific sources. | 1. Deletes records via Milvus using the source filter. <br>2. Calls **`_remove_source_map_entries()`** to update and prune the local JSON source-map file. | Cleans both the database and the metadata index. |

## 📊 Information Retrieval Utilities

### `get_collection_metrics()`
Retrieves detailed operational statistics about the Milvus collection, including:
*   Total row count of indexed items.
*   Collection load state (e.g., "Explicitly Loaded").
*   Full schema description and field list.
*   A comprehensive list of all defined indexes on the collection (name, type, metric).

### `raw_search(search_filter, output_fields, limit)`
Allows executing arbitrary filter queries against the Milvus database using a raw filtering expression string (`Milvus filter expression`). This bypasses the semantic/hybrid search layers for specific data querying needs.

## Dependencies
**Imports from:** codx/junior/model/model.py, codx/junior/ai/__init__.py, codx/junior/settings.py, codx/junior/knowledge/embeddings.py, codx/junior/utils/utils.py, codx/junior/profiling/profiler.py
**Imported by:** codx/junior/api/db_router.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_wiki.py, codx/junior/wiki/wiki_domains.py, codx/junior/wiki/wiki_index.py, codx/junior/wiki/wiki_manager.py