# Knowledge Core
## Overview

The Knowledge Core serves as the foundational intelligence layer for the API, acting as an orchestration layer that transforms unstructured or raw data into highly structured, interconnected knowledge bases. This module moves beyond simple data storage by actively modeling relationships and operational lifecycles within the application ecosystem.

At its heart, it manages the instantiation and maintenance of a sophisticated **Knowledge Graph**. This graph allows the system to not only store facts but also understand complex relationships between entities (derived from defined wiki domains), enabling context-aware processing and sophisticated querying that mimics deep domain knowledge.

Key responsibilities include:
1.  **Structured Mapping:** Taking input data streams and mapping them onto a formal schema derived from defined source domains.
2.  **Graph Construction:** Building and updating the persistent relationships within the Knowledge Graph (`knowledge_graph.py`).
3.  **AI Processing Integration:** Handling complex, stateful AI logic, such as simulating cancellation tokens or tracking multi-step processing (managed in `cancellation.py`).
4.  **Scope Management:** Ensuring all generated knowledge adheres to predefined boundaries defined by the accepted wiki domains (`wiki_domains.py`).

---

## Files in Domain

| File Path | Purpose | Description |
| :--- | :--- | :--- |
| `.dockerignore` | **Environment Config** | Specifies files and directories to be excluded from Docker build contexts, optimizing deployment size and ensuring secure container builds. |
| `ai/cancellation.py` | **AI Logic & State Management** | Implements complex operational logic for AI processes, particularly handling cancellation tokens. This module allows the system to gracefully manage half-completed or stateful asynchronous tasks, crucial for reliability in large-scale API interactions. |
| `knowledge/knowledge_graph.py` | **Core Graph Engine** | Contains the core classes and methods responsible for defining the nodes (entities) and edges (relationships) of the Knowledge Graph. This is the primary engine for structuring domain knowledge. |
| `wiki/wiki_domains.py` | **Domain Definition Scope** | Acts as the single source of truth for acceptable data domains within the system. It defines the structural boundaries, schemas, and available vocabularies for any new module generating knowledge, ensuring consistency and quality control from ingestion to storage. |

## Dependencies

The Knowledge Core relies on several architectural concepts and external components rather than specific direct file dependencies (as its role is systemic). Conceptually, it depends on:

*   **API Services:** Requires input data streams from primary API endpoints for processing.
*   **Asynchronous Processing Frameworks:** Heavily utilizes tools that manage concurrency and state to support AI lifecycle management.
*   **Serialization Libraries:** Essential for persisting the structured knowledge graph into a usable storage format (e.g., Neo4j, RDF store).

## Used By

The Knowledge Core is consumed by virtually every high-level service or API module that requires deep contextual understanding or needs to save complex, relational state. It is effectively used *by* any component requiring:

*   **Advanced Querying:** Beyond simple key-value lookups.
*   **Contextual Awareness:** The ability to understand how one piece of information relates to another over time.
*   **Atomic Transaction Processing:** State management that must survive operational interruptions (leveraging `cancellation.py`).

## Entry Points

All files within this domain are configured as necessary entry points, reflecting their critical role in system operation. Developers interact with the following paths when executing or testing core knowledge generation procedures:

*   `/home/.../api/codx/junior/ai/cancellation.py`: Used for initiating and simulating complex AI workflow states.
*   `/home/.../api/codx/junior/knowledge/knowledge_graph.py`: The main instantiation point for building and querying the knowledge graph structure.
*   `/home/.../api/codx/junior/wiki/wiki_domains.py`: Utilized during initialization to validate schemas and domains before data ingestion begins.