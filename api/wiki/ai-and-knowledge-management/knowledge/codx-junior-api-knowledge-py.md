# Knowledge Base API Reference

This section details the endpoints available for managing, querying, and enhancing the project's knowledge base. It supports status checks, content enrichment, general search (Q&A), agent-based planning, and background indexing processes.

## 📘 Status, Maintenance, and File Management

### Fetching Knowledge Status
*   **GET `/api/knowledge/status`**: Returns the current knowledge base status for the project by calling `codx_junior_session.check_knowledge_status()`.
*   **GET `/api/knowledge/files`**: Retrieves a list of files currently indexed in the knowledge base using `codx_junior_session.get_knowledge_files()`.

### Reloading and Deleting Sources
*   **POST `/api/knowledge/reload-path`**: Triggers a reload for specific source paths, useful when content changes outside the deployment cycle. Requires providing the path via the request body (`KnowledgeReloadPath`).
*   **GET `/api/knowledge/reload`**: Checks the general knowledge base status and triggers an internal check through the session.
*   **POST `/api/knowledge/delete`**: Deletes knowledge documents for specific sources, requiring a list of source paths in the request body (`KnowledgeDeleteSources`).
*   **DELETE `/api/knowledge/delete`**: Executes a full deletion of all indexed knowledge documents for the current project via `codx_junior_session.delete_knowledge()`.

### Project Summary and Metrics
*   **GET `/api/knowledge/summary`**: Generates and returns the project summary as plain Markdown text. The summary is retrieved by calling `get_knowledge().get_project_summary()` and returns a `text/markdown` response type.
*   **GET `/api/knowledge/summary/json`**: Returns the project summary in a structured JSON object format (`{"summary": "..."}`).
*   **POST `/api/knowledge/summary/rebuild`**: (Admin Required) Forces a full rebuild of the Project Summary (`Knowledge.build_project_summary()`). This operation regenerates the markdown document from scratch by reading all currently indexed sources. Requires `admin` permissions and returns the new summary along with the project name.
*   **DELETE `/api/knowledge/summary`**: (Admin Required) Deletes the persisted project summary file on disk. This action forces a clean slate, requiring a subsequent rebuild to generate a new summary.
*   **GET `/api/knowledge/metrics`**: Returns detailed collection-level metrics from the underlying Milvus store, including row count, load state, schema information, index metadata, and partition details.

## ✨ Content Enrichment: Keywords and Tags

### Retrieving Keywords
*   **GET `/api/knowledge/keywords`**: Retrieves keywords matching an optional search query provided via URL parameters (`?query=term`). This uses `codx_junior_session.get_keywords()`.

### Extracting and Storing Tags
*   **POST `/api/knowledge/keywords`**: Extracts and stores keyword tags from a submitted document object (`Document`). The function processes the document content and returns an updated dictionary containing the populated keyword metadata, executing `codx_junior_session.extract_tags(doc=doc)`.

## 🧠 AI Search Capabilities

These endpoints utilize specialized services for advanced knowledge retrieval: natural language question answering and agent-based resource planning.

### 1. General Knowledge Question Answering
*   **GET `/api/knowledge/ai-search`**: Performs an iterative, AI-driven search to answer a user's natural-language question (query).
    *   The system executes multiple cycles, refining queries until the AI determines the documents are sufficient or reaches `max_iterations`.
    *   **Parameters:** Requires `?query=...` and optionally `&max_iterations=N`.
    *   **Returns (`AISearchResult`):** A JSON object containing the original query, the final answer (grounded in retrieved context), all supporting documents, the number of iterations performed (`total_iterations`), and a list of all executed search queries (`queries_used`).

### 2. Agent Resource Planning
*   **POST `/api/knowledge/agent-search`**: Executes an AI-assisted agent task planner identifying necessary resources for fulfilling a user's request. This generates a structured **resource plan**, unlike general Q&A.
    *   The process iterates to gather comprehensive context tailored for development tasks.
    *   **Parameters:** Requires `?request=...` (the natural language objective) and optionally `&max_iterations=N`.
    *   **Returns (`AgentResourcePlan`):** A JSON object detailing the plan, which includes:
        *   `overview`: Narrative description of required steps.
        *   `files_to_read`: Files the agent should inspect for context.
        *   `files_to_modify`: Specific files to edit, with suggested actions and reasons.
        *   `files_to_create`: New file paths that must be created.
        *   `all_relevant_sources`: A flat list of all consulted source paths.

## 🔌 Asynchronous Background Operations (WebSockets)

The system provides background endpoints for long-running, resource-intensive tasks via Signal-Operation over SocketIO (`sio`). These methods run asynchronously and report progress events to the client.

### Knowledge Indexing
*   **`@sio.on("codx-junior-index-knowledge")`**: Handles batch indexing of knowledge files in the background.
    *   **Input Data:** Expected payload includes a list of `file_paths` and the project path (`codx_path`).
    *   **Process:** The process iterates through paths, loads documents (`knowledge.loader.load`), and finally indexes them (`knowledge.index_documents`).
    *   **Progress Reporting:** Emits detailed progress events:
        1.  `codx-junior-index-progress-started`: Indexing has begun.
        2.  `codx-junior-index-progress-document-processing`: Processing a specific document.
        3.  `codx-junior-index-progress-document-enriched`: Document enrichment successful.
        4.  `codx-junior-index-progress-document-indexed`: Document successfully indexed.
        5.  `codx-junior-index-progress-batch-complete`: A batch of documents finished indexing.
        6.  `codx-junior-index-progress-completed`: Full completion status.

### Agent Search Background Run
*   **`@sio.on("codx-junior-agent-search")`**: Executes the sophisticated agent resource planning process asynchronously, preventing connection stalls during long computations.
    *   **Input Data:** Expected payload contains a `request` string and an optional `max_iterations`.
    *   **Progress Event (`codx-junior-agent-search-progress`):** Reports iterative status updates (e.g., documents found, sufficiency check).
    *   **Completion Event (`codx-junior-agent-search-complete`):** Sends the final `AgentResourcePlan`, including a summary of files to read, modify, and create.

## Dependencies
**Imports from:** codx/junior/model/model.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/api/__init__.py, codx/junior/engine/session.py, codx/junior/engine/progress_callback.py, codx/junior/sio/session_channel.py, codx/junior/sio/sio.py
**Imported by:** codx/junior/app.py