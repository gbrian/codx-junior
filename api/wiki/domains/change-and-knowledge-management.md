# Change and Knowledge Management

## Overview
The **Change and Knowledge Management** module cluster serves as the backbone for project oversight and institutional memory within the system. It is designed to orchestrate system changes while simultaneously managing a robust, structured knowledge base. By integrating procedural update tracking with a comprehensive information storage framework, this module ensures that project documentation remains accurate, accessible, and synchronized with evolving technical requirements.

Key capabilities include the management of project-related changes, the maintenance of structured knowledge entries, and the support for advanced retrieval mechanisms (such as BM25 and vector-based search) to facilitate efficient information discovery.

## Files in Domain
- `/home/codx-junior/codx-junior/api/codx/junior/changes/change_manager.py`: Handles the tracking, processing, and orchestration of system changes and project-related events.
- `/home/codx-junior/codx-junior/api/codx/junior/knowledge/knowledge_db.py`: Manages the storage, retrieval, and schema structure for the knowledge base, utilizing modern database indexing techniques.

## Dependencies
This module currently operates as an independent cluster within the `codx-junior` architecture. It leverages external infrastructure components including:
- **Milvus:** For high-performance vector search and indexing.
- **Async Frameworks:** For non-blocking operations during database I/O and process orchestration.
- **Search Engines:** Support for BM25 and sparse-vector indexing for enhanced search capabilities.

## Used By
*This section is currently empty. The domain provides foundational services used across the broader `codx-junior` platform, but direct consumer tracking is currently under development.*

## Entry Points
- `/home/codx-junior/codx-junior/api/codx/junior/changes/change_manager.py`: Serves as the primary gateway for triggering change events and managing project workflows.
- `/home/codx-junior/codx-junior/api/codx/junior/knowledge/knowledge_db.py`: Acts as the interface for knowledge-base operations, including database connection, collection management, and query execution.

***

### Key Concepts & Technical References
*   [Milvus Documentation: Vector Database](https://milvus.io/docs)
*   [BM25 Algorithm Overview](https://en.wikipedia.org/wiki/Okapi_BM25)
*   [Asynchronous Python Programming](https://docs.python.org/3/library/asyncio.html)