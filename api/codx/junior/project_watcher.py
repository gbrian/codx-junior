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

logging.getLogger('watchdog.observers.inotify_buffer').setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)


class ProjectWatcher:
    """Project watcher will control project's changes by watching file changes"""

    def __init__(self):
        self.observers = {}     

    def watch_project(self, settings: CODXJuniorSettings, callback: Callable[[str], None]):
        """Watch project changes using watchdog"""
        project_path = settings.project_path
        if not self.is_watching_project(settings):
            ignore_patterns = settings.get_ignore_patterns()
            logger.info(f"_create_event_handler {ignore_patterns}")
            
            event_handler = self._create_event_handler(ignore_patterns, callback)
            observer = Observer()
            observer.schedule(event_handler, project_path, recursive=True)
            observer.start()
            self.observers[project_path] = observer
            logger.info(f"Started watching project at: {project_path}")

    def is_watching_project(self, settings: CODXJuniorSettings):
        """Check if we have an observer for the project"""
        project_path = settings.project_path
        return project_path in self.observers

    def stop_watching(self, settings: CODXJuniorSettings):
        """Stop watching project changes"""
        project_path = settings.project_path
        self.stop_observer(project_path)

    def stop_observer(self, project_path: str):
        observer = self.observers.pop(project_path, None)
        if observer:
            observer.stop()
            observer.join()
            logger.info(f"Stopped watching project at: {project_path}")

    @staticmethod
    def _create_event_handler(ignore_patterns: [str], callback: Callable[[str], None]) -> PatternMatchingEventHandler:
        class CustomEventHandler(PatternMatchingEventHandler):
            def __init__(self):
                super().__init__(
                    ignore_patterns=ignore_patterns,
                    ignore_directories=True
                )

            def on_any_event(self, event: FileSystemEvent):
                if not event.is_directory and event.event_type == EVENT_TYPE_MODIFIED:
                    if not [p for p in self.ignore_patterns if p in event.src_path]:
                        callback(event.src_path)
        
        return CustomEventHandler()

# Singletone
PROJECT_WATCHER = ProjectWatcher()
