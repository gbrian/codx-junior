## Progress Callbacks for Knowledge Operations

This module provides a structured way to report progress during knowledge operations such as indexing or enrichment. It defines abstract callback mechanisms to decouple operation logic from specific transport layers (like sockets or HTTP).

### Components

#### 1. `ProgressEventType`
An enumeration that specifies the various stages and types of events that can occur during indexing to help consumers understand the state of the process.

Events defined include:
*   **`STARTED`**: Indicates the commencement of operations.
*   **`DOCUMENT_PROCESSING`**: Reports progress when a document is undergoing processing.
*   **`DOCUMENT_ENRICHED`**: Signals that a document has been enriched with data.
*   **`DOCUMENT_INDEXED`**: Confirms that a document has been successfully indexed.
*   **`DOCUMENT_ERROR`**: Indicates an error occurring during document handling.
*   **`BATCH_COMPLETE`**: Marks the successful completion of a batch process.
*   **`ITERATION_COMPLETE`**: Reports the completion of individual iterations.
*   **`COMPLETED`**: Signals that all operations are finished successfully.
*   **`ERROR`**: A general error event signal.

#### 2. `ProgressCallback` (Abstract Base Class)
The abstract base class establishes the contract for any progress callback implementation, ensuring a standardized way to report status regardless of the underlying communication channel.

Required methods:

*   `on_progress(self, event_type: ProgressEventType, data: Dict[str, Any])`: Responsible for emitting a progress event.
    *   **Parameters:**
        *   `event_type`: The specific type of progress event.
        *   `data`: A dictionary containing the payload details relevant to the event type.
*   `on_error(self, error: Exception, context: Dict[str, Any])`: Responsible for emitting an explicit error event.
    *   **Parameters:**
        *   `error`: The exception that was thrown.
        *   `context`: Contextual information related to the occurrence of the error.

#### 3. `SocketProgressCallback`
This class provides a concrete implementation of the `ProgressCallback` designed specifically for transmitting progress updates back to a client via **Socket.IO**.

**Functionality:**

*   It requires initialization with a `SessionChannel` instance, which is used to send events across the connected socket channel.
*   When `on_progress` is called, it calculates the elapsed time since the beginning of the operation and builds a structured payload containing:
    *   The event type (`event_type`).
    *   A sequence number tracking progress (`sequence`).
    *   The total time elapsed in seconds (`elapsed_seconds`).
    *   Any additional data provided in the original `data` payload.
    *   The resulting Socket.IO event name is formatted as `codx-junior-index-progress-[event_type.value]`.
*   When `on_error` is called, it emits a standardized error payload via the `"codx-junior-index-error"` socket event, including:
    *   The status (`"error"`).
    *   The type name of the exception that occurred (`error_type`).
    *   A string representation of the exception message (`message`).
    *   The provided contextual information (`context`).

## Dependencies
**Imported by:** codx/junior/api/knowledge.py, codx/junior/knowledge/knowledge_loader.py, codx/junior/knowledge/knowledge_milvus.py