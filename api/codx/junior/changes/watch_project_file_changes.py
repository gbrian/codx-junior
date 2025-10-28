import os
import time
import asyncio
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .change_manager import ChangeManager
from codx.junior.project.project_discover import find_all_projects, find_project_from_file_path

logger = logging.getLogger(__name__)

def get_common_path_and_merged_ignores(projects):
    # Find the shortest common path
    common_path = os.path.commonpath([p.project_path for p in projects])
    # Merge all ignore patterns
    merged_ignores = set()
    for project in projects:
        merged_ignores.update(project.knowledge_file_ignore)
    return common_path, merged_ignores

class WatchProjectFileChanges:
    def __init__(self):
        self.projects = set()  # Set to store unique project paths
        self.observers = []  # List to keep track of observers

    def add_project(self, project_path, ignore_patterns):
        if not self._is_subproject(project_path):
            if project_path not in self.projects:
                self.projects.add(project_path)

    def _observe_projects(self):
        # Clear existing observers
        for observer in self.observers:
            observer.stop()
            observer.join()
        self.observers.clear()

        # Group projects by their common path
        project_groups = {}
        for project in find_all_projects().values():
            common_path, merged_ignores = get_common_path_and_merged_ignores([project])
            if common_path not in project_groups:
                project_groups[common_path] = (set(), set())
            project_groups[common_path][0].add(project)
            project_groups[common_path][1].update(merged_ignores)

        # Create observers for each group
        for common_path, (projects, ignores) in project_groups.items():
            self._observe_project(common_path, ignores)

    def _observe_project(self, project_path, ignore_patterns):
        event_handler = ProjectFileChangeHandler(project_path, ignore_patterns)
        observer = Observer()
        observer.schedule(event_handler, path=project_path, recursive=True)
        observer.start()
        self.observers.append(observer)

    def _is_subproject(self, project_path):
        for existing_project in self.projects:
            if project_path.startswith(existing_project):
                return True
        return False

    def check_for_new_projects(self):
        current_projects = find_all_projects().values()
        current_project_paths = {p.project_path for p in current_projects}

        # Add new projects
        for project in current_projects:
            if project.project_path not in self.projects:
                self.add_project(project.project_path, project.knowledge_file_ignore)

        # Remove observers for projects that no longer exist
        for observer in self.observers[:]:
            if observer.event_handler.project_path not in current_project_paths:
                logger.info(f"Project removed from observer: {observer.event_handler.project_path}")
                observer.stop()
                observer.join()
                self.observers.remove(observer)
                self.projects.remove(observer.event_handler.project_path)

        # Re-observe projects with new configuration
        self._observe_projects()

    def start(self):
        try:
            while True:
                self.check_for_new_projects()
                time.sleep(30)  # Check for new projects every 30 seconds
        except KeyboardInterrupt:
            for observer in self.observers:
                observer.stop()
            for observer in self.observers:
                observer.join()

class ProjectFileChangeHandler(FileSystemEventHandler):
    def __init__(self, project_path, ignore_patterns):
        self.project_path = project_path
        self.ignore_patterns = set(ignore_patterns)

    async def on_modified(self, event):
        if not event.is_directory and not self._is_ignored(event.src_path):
            logger.info(f"Change detected in project: {self.project_path}, file: {event.src_path}")
            project = find_project_from_file_path(event.src_path)
            if project:
                change_manager = ChangeManager(settings={"project_path": project.project_path})
                await change_manager.process_project_mentions(file_path=event.src_path)

    def _is_ignored(self, file_path):
        return any(pattern in file_path for pattern in self.ignore_patterns)

# Example usage:
# watcher = WatchProjectFileChanges()
# watcher.start()
