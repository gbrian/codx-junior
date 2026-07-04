# Knowledge Base API Documentation

This documentation details the available RESTful API endpoints and SocketIO handlers for managing, querying, and utilizing the project's internal knowledge base (KnowledgeDB).

## 📘 Knowledge Management Endpoints

### Get Status Check
Retrieves the current status of the knowledge base.

*   **Endpoint:** `GET /knowledge/status` [API: knowledge\_status]
*   **Purpose:** Returns a dictionary detailing the accumulated knowledge base status for the project.
    *   *(Reference: The function `api_knowledge_status` uses `codx_junior_session.check_knowledge_status()`.)*

### Get Knowledge Files List
Retrieves information regarding the files indexed in the knowledge base.

*   **Endpoint:** `GET /knowledge/files` [API: knowledge\_files]
*   **Purpose:** Returns a dictionary containing details of the currently processed knowledge source file(s).
    *   *(Reference: The function `api_knowledge_files` uses `codx_junior_session.get_knowledge_files()`.)*

### Get Collection Metrics
Retrieves detailed metrics from the underlying Milvus storage collection used by the KnowledgeDB.

*   **Endpoint:** `GET /knowledge/metrics` [API: knowledge\_metrics]
*   **Purpose:** Provides operational statistics, including row count, load state, schema details, index metadata, and partition information for troubleshooting and monitoring.
    *   *(Reference: The function `api_knowledge_metrics` calls `KnowledgeDB.get_collection_metrics()`.)*

### Reload a Single Path
Triggers the re-indexing of knowledge documents from a specific source path. This is crucial when local files change but full indexing isn't desired.

*   **Endpoint:** `POST /knowledge/reload-path` [API: knowledge\_reload\_path]
*   **Payload:** Requires an object containing the path to reload (`KnowledgeReloadPath`).
    *   *(Reference: This endpoint calls `codx_junior_session.index_knowledge_source(sources=[path])`.)*

### Delete Knowledge Source by Path (Bulk)
Deletes knowledge documents associated with a list of specified source paths. Use this for permanently removing old or incorrect documentation sets.

*   **Endpoint:** `POST /knowledge/delete` [API: knowledge\_delete\_path]
*   **Payload:** Requires an object listing the source paths to delete (`KnowledgeDeleteSources`).
    *   *(Reference: This endpoint calls `codx_junior_session.delete_knowledge_source(sources=list_of_paths)`.)*

### Delete All Knowledge (Full Reset)
Performs a complete wipe of all indexed knowledge documents for the project, returning the database to a clean state.

*   **Endpoint:** `DELETE /knowledge/delete` [API: knowledge\_reload\_all]
*   **Function:** Executes `codx_junior_session.delete_knowledge()` across all sources.

## 🔎 Search and Retrieval Endpoints

### AI-Assisted Q&A Search
Uses advanced LLM techniques to search the corpus iteratively, providing conversational answers grounded in retrieved context.

*   **Endpoint:** `POST /knowledge/ai-search` [API: knowledge\_ai\_search]
*   **Parameters (Query Params):**
    *   `query`: The natural language question from the user (required).
    *   `max_iterations`: Maximum search cycles allowed. Defaults to 3.
*   **Process:** The system executes multiple search-and-check cycles, refining queries until the AI determines sufficient context has been gathered or the iteration limit is reached.
*   **Response:** Returns an `AISearchResult` dictionary containing:
    *   `answer`: The final synthesized answer.
    *   `queries_used`: All initial and refined search queries executed.
    *   `documents`: Supporting retrieved document chunks with metadata.

### AI-Assisted Agent Planning Search
Generates a structured "Resource Plan" detailing which project files an agent needs to interact with to complete a complex request (e.g., "Add contacts section").

*   **Endpoint:** `POST /knowledge/agent-search` [API: knowledge\_agent\_search]
*   **Parameters (Query Params):**
    *   `request`: Natural language description of the task for the agent.
    *   `max_iterations`: Maximum search cycles allowed. Defaults to 3.
*   **Process:** The AI searches not just for answers, but for relevant *file locations*. It follows an iterative cycle similar to Q&A search, culminating in a structured plan generation.
*   **Response:** Returns an `AgentResourcePlan` dictionary encompassing:
    *   `overview`: Narrative summary of the required actions.
    *   `files_to_read`: Paths for context gathering.
    *   `files_to_modify`: Paths requiring suggested edits/reasoning.
    *   `files_to_create`: Required new file paths.

## 📝 Summary and Keyword Handling

### Get Project Summary (Markdown)
Generates a human-readable summary of the entire project, suitable for displaying in read-only markdown format.

*   **Endpoint:** `GET /knowledge/summary` [API: knowledge\_summary]
*   **Return Type:** `text/markdown`.
    *   *(Reference: Uses `knowledge.get_project_summary()`.)*

### Get Project Summary (JSON)
Returns the project summary in a structured JSON format, ideal for API consumption by clients that need to parse markdown content programmatically.

*   **Endpoint:** `GET /knowledge/summary/json` [API: knowledge\_summary\_json]
*   **Response:** `{"summary": "Markdown Content..."}`

### Manual Summary Rebuild (Admin Only)
Forces the regeneration of the project summary document from all currently indexed sources. This should be used when existing source material changes and the summary becomes outdated.

*   **Endpoint:** `POST /knowledge/summary/rebuild` [API: knowledge\_summary\_rebuild]
*   **Authorization:** Requires Admin privileges (`require_admin`).
*   **Process:** Triggers `Knowledge.build_project_summary()`.
*   **Response:** Returns the newly generated summary and project name.

### Delete Summary File (Admin Only)
Deletes the persisted physical summary file from the disk, ensuring that the next rebuild operation starts completely fresh.

*   **Endpoint:** `DELETE /knowledge/summary` [API: knowledge\_summary\_delete]
*   **Authorization:** Requires Admin privileges (`require_admin`).
*   **Process:** Manually removes the summary file path on the filesystem.

### Keyword Search and Extraction
Endpoints for managing metadata keywords associated with documentation.

1.  **Extract Tags (Synchronous):**
    *   **Endpoint:** `POST /knowledge/keywords` [API: knowledge\_extract\_tag]
    *   **Payload:** Requires a document object (`Document`) to be analyzed.
    *   **Action:** Runs the extraction process (`codx_junior_session.extract_tags(doc=doc)`), enriching the document with keyword metadata.

2.  **Search Keywords (Filtered List):**
    *   **Endpoint:** `GET /knowledge/keywords` [API: knowledge\_get\_keywords]
    *   **Parameters (Query Params):**
        *   `query`: Optional search term to filter displayed keywords.
    *   **Purpose:** Retrieves a list of existing, indexed keyword tags matching optional search criteria.

## ⚙️ Background Processing Handlers (SocketIO)**

The following functions handle long-running or asynchronous operations using SocketIO events, allowing the application front-end to remain responsive.

### Stream Knowledge Indexing
This handler processes and indexes multiple files provided by a client over time (`codx-junior-index-knowledge`).

*   **Endpoint:** `sio_on("codx-junior-index-knowledge")` [Socket: index\_knowledge]
*   **Expected Data Payload (`data`):** Contains an array of file paths (`file_paths`) and the project path (`codx_path`).
*   **Progress Reporting:** Emits progress events through `progress_callback`:
    *   `codx-junior-index-progress-started`: Signals the start, providing total files.
    *   `codx-junior-index-progress-document-processing`: Updates on per-file status (e.g., "Reloading X...").
    *   `codx-junior-index-progress-completed`: Indicates all paths have been processed successfully.
    *   `codx-junior-index-error`: Signals any failure during processing.

### Stream Agent Search Execution
Allows running the resource planning task asynchronously, preventing client timeouts during complex searches.

*   **Endpoint:** `sio_on("codx-junior-agent-search")` [Socket: agent\_search]
*   **Expected Data Payload (`data`):**
    *   `request`: The natural language task description.
    *   `max_iterations`: Maximum search cycles (default 3).
*   **Progress Signaling:** The function continuously sends progress updates via `SessionChannel.send_event("codx-junior-agent-search-progress", ...)` during the iterative search phase.
*   **Completion Event:** Upon successful generation of the plan, it emits:
    *   `codx-junior-agent-search-complete`: Carries the full `AgentResourcePlan` object.
*   **Error Handling:** Emits `codx-junior-agent-search-error` upon failure.

## Dependencies
**Imports from:** codx/junior/model/model.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/api/__init__.py, codx/junior/engine/session.py, codx/junior/engine/progress_callback.py, codx/junior/sio/session_channel.py, codx/junior/sio/sio.py
**Imported by:** codx/junior/app.py