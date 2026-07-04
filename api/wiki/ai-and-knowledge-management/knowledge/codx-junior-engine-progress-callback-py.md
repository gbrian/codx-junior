# Progress Callback System

The progress callback system provides an abstract mechanism to report the status of knowledge operations (such as indexing, document enrichment, and code splitting) without coupling the core logic to specific transport layers like WebSockets or HTTP.

## Overview

The architecture utilizes an abstract base class, `ProgressCallback`, which defines the interface for reporting progress and errors. Implementations of this class can be swapped depending on how the system needs to communicate status updates back to the client or monitoring service.

## Core Components

### ProgressEventType
An enumeration representing the lifecycle of an indexing operation:
* `STARTED`: The operation has begun.
* `DOCUMENT_PROCESSING`: Active processing of a document.
* `DOCUMENT_ENRICHED`: Enrichment steps are complete.
* `DOCUMENT_INDEXED`: Document successfully indexed.
* `DOCUMENT_ERROR`: An error occurred during document handling.
* `BATCH_COMPLETE`: A batch of documents has finished processing.
* `ITERATION_COMPLETE`: A full iteration cycle is complete.
* `COMPLETED`: The entire operation has finished.
* `ERROR`: A global or fatal error occurred.

### ProgressCallback (Abstract Base)
Defines the required interface for all callback handlers:
* `on_progress(event_type, data)`: Emits a progress update with the associated event type and payload.
* `on_error(error, context)`: Reports exceptions encountered during the operation along with contextual information.

## Implementations

### SocketProgressCallback
The `SocketProgressCallback` handles communication via a `SessionChannel` (e.g., Socket.IO). 

* **Event Emission**: When `on_progress` is called, it automatically tracks:
    * `sequence`: The incrementing count of events sent.
    * `elapsed_seconds`: The time passed since the first event was emitted.
    * `event_type`: The string value of the triggered event.
* **Socket Routing**: Events are routed through the socket channel using the naming convention: `codx-junior-index-progress-{event_type}`.
* **Error Handling**: Errors are emitted through a dedicated `codx-junior-index-error` event, capturing the error type, message, and relevant context.

## Integration
To implement a custom transport layer, developers must subclass `ProgressCallback` and implement the `on_progress` and `on_error` methods. This ensures that the engine's core indexing logic remains decoupled from the infrastructure-specific delivery mechanisms.

---
### References
* [ProgressEventType](#progresseventtype)
* [ProgressCallback](#progresscallback-abstract-base)
* [SocketProgressCallback](#socketprogresscallback)

## Dependencies
**Imported by:** codx/junior/api/knowledge.py, codx/junior/knowledge/knowledge_loader.py, codx/junior/knowledge/knowledge_milvus.py