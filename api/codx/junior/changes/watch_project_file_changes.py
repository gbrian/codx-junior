import os
import time
import asyncio
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from codx.junior.project.project_discover import find_all_projects, find_project_from_file_path

logger = logging.getLogger(__name__)

for log in ['watchdog']:
    logging.getLogger(log).setLevel(logging.ERROR)

class WatchProjectFileChanges:
    def __init__(self, callback):
        self.observers = []
        self.groups = {}
        self.callback = callback
        self._running = False  # To track the running state of the observer thread

    def _create_groups(self, projects):
        """Group all projects by a their root path"""
        groups = {}
        projects = sorted(projects, key=lambda p: len(p.project_path))
        for project in projects:
            path = project.project_path
            key = next((k for k in groups if path.startswith(k)), path)
            if not key in groups:
                groups[key] = [project]
            else:
                groups[key].append(project)
        
        self.groups = groups

        # Log for each root path the list of projects (only their project_name)
        for root_path, projects in self.groups.items():
            project_names = [project.project_name for project in projects]
            logger.info(f"Created group for root path: {root_path} with projects: {project_names}")

    def _get_path_ignores(self, path: str):
        ignore_patterns = set()
        for project in self.groups[path]:
            if project.knowledge_file_ignore:
                ignore_patterns.update(project.knowledge_file_ignore.split(","))
        return list(ignore_patterns)

    def _has_changed(self, projects):
        def get_project_root(project):
            return next((k for k in self.groups if project.project_path.startswith(k)), None)
        return True if next((True for p in projects if get_project_root(p) is None), False) else False

    def _observe_projects(self, all_projects):
        # Clear existing observers
        self.stop_observers()

        # Group all projects
        self._create_groups(all_projects)

        for path in self.groups:
            ignores = self._get_path_ignores(path)
            self._observe_project(path, ignores)

        # Log all root paths for which observers are created
        logger.info(f"Observers created for root paths: {list(self.groups.keys())}")

    def _observe_project(self, project_path, ignore_patterns):
        event_handler = ProjectFileChangeHandler(project_path, ignore_patterns, self.callback)
        observer = Observer()
        observer.schedule(event_handler, path=project_path, recursive=True)
        observer.start()
        self.observers.append(observer)

    def check_for_new_projects(self):
        try:
            all_projects = find_all_projects().values()
            watching_projects = [p for p in all_projects if p.watching]
            logger.info("check_for_new_projects %s", len(watching_projects))
            if self._has_changed(watching_projects):
                logger.info("Rebuilding observers")
                self._observe_projects(watching_projects)
        except Exception as ex:
            logger.exception("Error in check_for_new_projects", ex)

    def stop_observers(self):
        """Stop all observers."""
        logger.info("Stopping all observers...")
        for observer in self.observers:
            observer.stop()
        for observer in self.observers:
            observer.join()
        self.observers.clear()
        logger.info("All observers stopped.")

    def start(self):
        try:
            logger.info("WatchProjectFileChanges [start]")
            self._running = True
            while self._running:
                self.check_for_new_projects()
                time.sleep(30)  # Check for new projects every 30 seconds
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received in main block. Stopping observers...")
            self.stop()

    def stop(self):
        """Public method to stop the watching thread and observers."""
        logger.info("Stopping WatchProjectFileChanges...")
        self._running = False
        self.stop_observers()

class ProjectFileChangeHandler(FileSystemEventHandler):
    def __init__(self, project_path, ignore_patterns, callback):
        self.project_path = project_path
        self.ignore_patterns = set(ignore_patterns)
        self.callback = callback

    async def on_modified(self, event):
        if not event.is_directory and not self._is_ignored(event.src_path):
            logger.info(f"Change detected in project: {self.project_path}, file: {event.src_path}")
            project = find_project_from_file_path(event.src_path)
            if project:
                # Log the file path and the project (project_name) found for the file path
                logger.info(f"File path: {event.src_path} belongs to project: {project.project_name}")
                
                await self.callback(project=project, file_path=event.src_path)

    def _is_ignored(self, file_path):
        return any(pattern in file_path for pattern in self.ignore_patterns)