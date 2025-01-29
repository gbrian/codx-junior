import logging
import time
import asyncio

from datetime import datetime
from threading import Thread

from codx.junior.engine import (
    CODXJuniorSession,
    find_project_from_file_path,
    find_all_projects
)

from codx.junior.project_watcher import ProjectWatcher
from codx.junior.knowledge.knowledge_milvus import Knowledge


logger = logging.getLogger(__name__)

def start_background_services(app):

    def on_project_watcher_changes(changes:[str]):
        for file_path in changes:
            project_file_changed(file_path)

    FILES_CHECKING = {}
    PROJECT_WATCHER = ProjectWatcher(callback=on_project_watcher_changes)


    def check_file_worker(file_path: str):
        settings = find_project_from_file_path(file_path=file_path)
        if not settings.is_valid_project_file(file_path=file_path):
            return
        async def worker():
            FILES_CHECKING[file_path] = True
            try:
                # Check mentions
                codx_junior_session = CODXJuniorSession(settings=settings)
                res = await codx_junior_session.check_file_for_mentions(file_path=file_path)
                codx_junior_session.log_info(f"Check file {file_path} for mentions: {res}")
                # Reload knowledge 
                if settings.watching:
                    knowledge = Knowledge(settings=settings)
                    file_changes = knowledge.detect_changes()
                    if file_path in file_changes:
                        knowledge.reload_path(path=file_path)
            except Exception as ex:
                logger.exception(f"Error processing file changes {file_path}: {ex}")

            del FILES_CHECKING[file_path]
        asyncio.run(worker())

    def project_file_changed(file_path: str):
        settings = find_project_from_file_path(file_path)
        if not settings:
            return
        file_key = f"{settings.project_name}:{file_path}"
        if FILES_CHECKING.get(file_path):
            return
        if not Knowledge(settings=settings).is_valid_project_file(file_path=file_path):
            return
        logger.info(f"project_file_changed processing event. {file_key} - {settings.project_name}")
        Thread(target=check_file_worker, args=(file_path,)).start()

    # Load all projects and watch
    def check_projects():
        async def check(project):
            await CODXJuniorSession(settings=project).process_project_changes()
        while True:
            try:
                for project in find_all_projects():
                    # Watch project changes
                    PROJECT_WATCHER.watch_project(
                        project_path=project.project_path)

                    asyncio.run(check(project=project))
            except Exception as ex:
                logger.error(f"Erroor checking project {ex}")
            time.sleep(1)

    logger
    Thread(target=check_projects).start()
