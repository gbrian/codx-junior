from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

class ProgressEventType(Enum):
    """Event types emitted during indexing operations."""
    STARTED = "started"
    DOCUMENT_PROCESSING = "document_processing"
    DOCUMENT_ENRICHED = "document_enriched"
    DOCUMENT_INDEXED = "document_indexed"
    DOCUMENT_ERROR = "document_error"
    BATCH_COMPLETE = "batch_complete"
    ITERATION_COMPLETE = "iteration_complete"
    COMPLETED = "completed"
    ERROR = "error"


class ProgressCallback(ABC):
    """
    Abstract base for progress callbacks during knowledge operations.
    
    Allows indexing/enrichment operations to report progress without
    tight coupling to specific transport layers (socket, HTTP, etc).
    """

    @abstractmethod
    async def on_progress(
        self,
        event_type: ProgressEventType,
        data: Dict[str, Any],
    ) -> None:
        """
        Emit a progress event.
        
        Args:
            event_type: Type of progress event.
            data: Event payload (varies by event type).
        """
        pass

    @abstractmethod
    async def on_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """
        Emit an error event.
        
        Args:
            error: Exception that occurred.
            context: Contextual information about the error.
        """
        pass


class SocketProgressCallback(ProgressCallback):
    """
    Socket.IO implementation of progress callbacks.
    
    Emits events back to a connected client via the Socket.IO channel.
    """

    def __init__(self, channel: "SessionChannel"):
        """
        Initialize with a Socket.IO session channel.
        
        Args:
            channel: SessionChannel instance for event emission.
        """
        self.channel = channel
        self.event_count = 0
        self.start_time = None

    async def on_progress(
        self,
        event_type: ProgressEventType,
        data: Dict[str, Any],
    ) -> None:
        """Emit progress event via Socket.IO."""
        import time
        
        self.event_count += 1
        if not self.start_time:
            self.start_time = time.time()
        
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        payload = {
            "event_type": event_type.value,
            "sequence": self.event_count,
            "elapsed_seconds": round(elapsed, 2),
            **data,
        }
        
        # Map event types to Socket.IO event names
        socket_event = f"codx-junior-index-progress-{event_type.value}"
        self.channel.send_event(socket_event, payload)

    async def on_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Emit error event via Socket.IO."""
        self.channel.send_event("codx-junior-index-error", {
            "status": "error",
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context,
        })