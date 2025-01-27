import time
import logging
import asyncio

from typing import Callable, List
from watchfiles import awatch
from threading import Thread, Event

from codx.junior.settings import CODXJuniorSettings

logging.getLogger('watchdog.observers.inotify_buffer').setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

class ProjectWatcher:
    """Project watcher will control project's changes by watching file changes"""

    def __init__(self, callback: Callable[[List[str]], None]):
        self.paths = {}
        self.stop_event = Event()
        self.callback = callback
        self.watch_thread = None
        logger.info(f"ProjectWatcher created")

    def watch_project(self, project_path: str):
        """Watch project changes using watchdog"""
        if not project_path in self.paths:
            logger.info(f"watch_project {project_path}")
            self.paths[project_path] = True
            self.stop_event.set()

        if not self.watch_thread and len(self.paths.keys()):
            self.watch_thread = Thread(target=self.start)
            self.watch_thread.start()

    def stop_watching(self, project_path):
        """Stop watching project changes"""
        del self.paths[project_path]
        self.stop_event.set()

    async def watch_changes(self):
        self.stop_event.clear()
        paths = list(self.paths.keys())
        paths.sort(reverse=True, key=lambda x: len(x))
        def is_child_path (path):
            matches = [p for p in paths if p.startswith(path)]
            if matches and len(path) > len(matches[0]):
                return True
            return False

        parent_folders = [p for p in paths if not is_child_path(p)] 
        logger.info(f"watch_changes folders: {parent_folders}")
        async for changes in awatch(*parent_folders, stop_event=self.stop_event):
            self.callback([c[1] for c in changes])

    def start(self):
        while True:
            asyncio.run(self.watch_changes())
            if not len(self.paths.keys()):
                break
