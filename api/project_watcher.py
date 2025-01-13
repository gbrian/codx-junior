import time
import logging
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

class ProjectWatcher:
    def __init__(self):
        self.observer = None

    def start_watching(self, project_path: str, callback):
        """Start watching the given project path for changes and invoke the callback with the changed files."""
        event_handler = self._create_event_handler(callback)
        self.observer = Observer()
        self.observer.schedule(event_handler, project_path, recursive=True)
        self.observer.start()

    def stop_watching(self):
        """Stop watching the project path."""
        if self.observer:
            self.observer.stop()
            self.observer.join()

    def _create_event_handler(self, callback):
        """Create a file system event handler that calls the callback on any event."""
        class CustomEventHandler(FileSystemEventHandler):
            def on_any_event(self, event: FileSystemEvent) -> None:
                logger.info("FileSystemEventHandler {event}")
                # callback(event.src_path)

        return CustomEventHandler()