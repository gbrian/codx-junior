## Knowledge Operation Progress Callback System

The progress callback system provides a mechanism for knowledge operations (such as indexing or enrichment) to report their status without creating tight coupling to specific transport layers, such as sockets or HTTP requests.

### Event Lifecycle Types (`ProgressEventType`)

This enumeration defines the standard stages and events that occur during an indexing operation:

*   `STARTED`: Indicates that the operation has begun.
*   `DOCUMENT_PROCESSING`: Signals that a document is currently being processed.
*   `DOCUMENT_ENRICHED`: Indicates that a document has been successfully enriched.
*   `DOCUMENT_INDEXED`: Shows that a document has completed indexing.
*   `DOCUMENT_ERROR`: Reports an error encountered during document handling.
*   `BATCH_COMPLETE`: Signals the successful completion of a batch operation.
*   `ITERATION_COMPLETE`: Indicates the end of one iteration cycle.
*   `COMPLETED`: Marks the overall completion of the process.
*   `ERROR`: Utility event for general operational errors.

### Abstract Progress Callback (`ProgressCallback`)

The `ProgressCallback` is an Abstract Base Class (ABC) that defines the required interface for all progress reporting mechanisms. Because it is abstract, concrete implementations must define how progress events and errors are transmitted (`<document>Abstract base for progress callbacks during knowledge operations.</document>`).

#### Methods:

*   **`on_progress(event_type: ProgressEventType, data: Dict[str, Any])`**:
    Emitted to report a general progress event. It takes the specific `ProgressEventType` and an arbitrary payload (`data`) relevant to that event type.
*   **`on_error(error: Exception, context: Dict[str, Any])`**:
    Emitted when an error occurs during the operation. It requires the Exception object and a dictionary providing contextual information about the error ($\text{<document>Contextual information about the error.</document>}$).

### Socket-Based Progress Reporting (`SocketProgressCallback`)

The `SocketProgressCallback` provides a concrete implementation of progress tracking specifically designed for real-time communication using **Socket.IO**.

#### Initialization:
Requires a `SessionChannel` instance upon initialization ($\text{<document>Initialize with a Socket.IO session channel.</document>}$):
*   **`__init__(self, channel: "SessionChannel")`**: Sets up the necessary channel and initializes tracking variables like `event_count` and `start_time`.

#### Implementation Details:

*   **`on_progress(event_type: ProgressEventType, data: Dict[str, Any])`**:
    1.  Increments an internal event counter (`self.event_count`).
    2.  Calculates the elapsed time since the operation started.
    3.  Constructs a payload that includes all progress details (event type value, sequence number, elapsed time, and custom data).
    4.  Sends the compiled payload via the Socket.IO channel using an event name derived from the `ProgressEventType` (e.g., `"codx-junior-index-progress-{event_type.value}"`).

*   **`on_error(error: Exception, context: Dict[str, Any])`**:
    Emits a standardized error message through the Socket.IO channel using the fixed event name `"codx-junior-index-error"`. The payload contains details including the status ("error"), the exception type (`type(error).__name__`), the error message, and the provided context.$\text{<document>Send error payload via Socket.IO.</document>}$

## Dependencies
**Imported by:** codx/junior/api/knowledge.py, codx/junior/knowledge/knowledge_loader.py, codx/junior/knowledge/knowledge_milvus.py