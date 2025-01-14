import time
import logging
from typing import Callable
from watchdog.events import (
  FileSystemEvent,
  PatternMatchingEventHandler,
  EVENT_TYPE_MOVED,
  EVENT_TYPE_DELETED,
  EVENT_TYPE_CREATED,
  EVENT_TYPE_MODIFIED,
  EVENT_TYPE_CLOSED,
  EVENT_TYPE_CLOSED_NO_WRITE,
  EVENT_TYPE_OPENED
)
from watchdog.observers import Observer

from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

class ProjectWatcher:
    """Project watcher will control project's changes by watching file changes"""

    def __init__(self):
        self.observers = {}

    def watch_project(self, settings: CODXJuniorSettings, callback: Callable[[str], None]):
        """Watch project changes using watchdog"""
        project_path = settings.project_path
        if not self.is_watching_project(settings):
            event_handler = self._create_event_handler(callback)
            observer = Observer()
            observer.schedule(event_handler, project_path, recursive=True)
            observer.start()
            self.observers[project_path] = observer
            logger.info(f"Started watching project at: {project_path}")

    def is_watching_project(self, settings: CODXJuniorSettings):
        """Check if we have an observer for the project"""
        project_path = settings.project_path
        return True if project_path in self.observers else False

    def stop_watching(self, settings: CODXJuniorSettings):
        """Stop watching project changes"""
        project_path = settings.project_path
        observer = self.observers.pop(project_path, None)
        if observer:
            observer.stop()
            observer.join()
            logger.info(f"Stopped watching project at: {project_path}")

    @staticmethod
    def _create_event_handler(callback: Callable[[str], None]) -> PatternMatchingEventHandler:
        class CustomEventHandler(PatternMatchingEventHandler):
            def __init__(self):
                super().__init__(
                    ignore_patterns=[".git"],
                    ignore_directories=True
                )

            def on_any_event(self, event: FileSystemEvent):
                if not event.is_directory and event.event_type == EVENT_TYPE_MODIFIED:
                    logger.info(f"FileSystemEventHandler {event}")
                    callback(event.src_path)
        
        return CustomEventHandler()

# Singletone
PROJECT_WATCHER = ProjectWatcher()
