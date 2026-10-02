# Knowledge Engine Operations

The KnowledgeEngine class is responsible for managing all knowledge base operations for a CODXJuniorSession. It handles search, indexing, document enrichment, and overall knowledge context management, providing methods for sophisticated retrieval augmented generation (RAG) processes.

## 🚀 Core Knowledge Search

### `knowledge_search`
This is the primary method for performing knowledge searches. It accepts a `KnowledgeSearch` model which dictates how the search should run:

*   **Configuration:** The process allows granular control over search parameters via session settings, including the `knowledge_search_type`, `document_count`, and relevance scores (`knowledge_context_cutoff_relevance_score` or `knowledge_context_rag_distance`).
*   **Search Modes:** It supports multiple modes:
    1.  **Raw Search (Chat-based):** When the search type is "raw," it validates documents using the query and executes a chat interaction (`chat_with_project`) to generate an answer, retrieving both documents and a response message.
    2.  **Indexed Search:** For other types, it utilizes direct indexing searching via `Knowledge(settings=...)` which accepts a search term, type, and limit.

### `project_search`
Provides a simpler interface for general knowledge querying by calling the session's dedicated search function (`self.session.get_knowledge().search(query=query)`). This method returns a list of matching documents based on the query string.

### Advanced Document Retrieval: `select_afefcted_documents_from_knowledge`
This specialized function selects relevant documents by searching across multiple project scopes simultaneously. It is essential when the context needs to draw information from several related repositories. Key functions include:

*   **Scoped Search:** Allows searching within a list of defined projects (`search_projects`).
*   **Multi-Source Aggregation:** Collects results and file lists from every specified search project, ensuring that document relevance is maintained across disparate sources.

## 💾 Knowledge Maintenance and Indexing

### Project Scope Management
To ensure comprehensive knowledge retrieval, the engine can resolve all related projects:

*   `get_project_dependencies()`: Retrieves a tuple containing all child projects (sub-projects) and direct project dependencies related to the current context.
*   `get_all_search_projects()`: Combines the main project setting, its children, and its dependencies into a comprehensive list of `settings` objects suitable for broad searches.

### Source Handling
These methods control which documents are considered part of the knowledge base:

*   `index_knowledge_source(sources: list)`: Iterates through provided source paths and calls the underlying maintenance tool (`knowledge.reload_path`) to index new or updated knowledge documents, returning an acknowledgement of success. (Reference: `index_knowledge_source`).
*   `delete_knowledge_source(sources: list)`: Deletes specified knowledge documents using a list of source paths. (Reference: `delete_knowledge_source`).
*   `delete_knowledge()`: Completely resets and deletes all recorded knowledge for the current project, ensuring a clean slate.

## 🧠 Enrichment and Query Optimization

### Keyword Extraction
The engine provides tools to enrich both queries and documents with keywords:

*   `get_keywords(query: str)`: Takes free text and utilizes `KnowledgeKeywords` to extract relevant search terms/keywords for the query (Reference: `get_keywords`).
*   `create_knowledge_search_query(query: str)`: Optimizes a raw user input query by passing it through the AI chat. The goal is to prompt the LLM to transform the natural language text into an optimized, keyword-rich search string suitable for the knowledge base (Reference: `create_knowledge_search_query`).
*   `extract_tags(doc)`: Performs document enrichment by calling a function on the `Knowledge` object to extract keywords/tags directly from an individual document object.

## ⚙️ Status and Background Processing

### Change Detection and Synchronization
Since knowledge sources change over time, background processes are required to keep the index current:

*   ***Project File Changes (`process_project_changes`)**: Runs periodically to identify local file system changes. It checks for files that have been modified recently enough (beyond a defined elapsed time constant) and selectively reloads them into the knowledge base. This process handles media files by first transcribing audio content and adjusting the reference path accordingly.
*   ***Project Mentions (`process_project_mentions`)**: Executes mention checks on recent project file changes identified through change detection, ensuring that document references (mentions) are valid before indexing processes continue.

### Status Reporting
Detailed inspection of the knowledge base status is handled by:

*   `get_knowledge_files()`: Returns a list of all source paths keys currently registered in the system's database, providing a basic inventory.
*   `check_knowledge_status()`: Provides a comprehensive snapshot of the current state. It returns details including:
    *   All current sources and updates detected (`current_sources_and_updates`).
    *   A list of files that have changed recently, indicating pending actions (`pending_files`, `total_pending_changes`).
    *   Collection metrics from the underlying vector database (`collection_metrics`), alongside general status messages.

## Dependencies
**Imports from:** codx/junior/context.py, codx/junior/db.py, codx/junior/globals.py, codx/junior/knowledge/knowledge_keywords.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/model/model.py, codx/junior/profiling/profiler.py, codx/junior/project/project_discover.py, codx/junior/utils/utils.py, codx/junior/engine/session.py, codx/junior/ai/__init__.py
**Imported by:** codx/junior/engine/session.py