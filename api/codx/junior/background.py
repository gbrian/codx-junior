import logging
import time
import asyncio
import os

from datetime import datetime, timedelta
from threading import Thread, Lock

from codx.junior.engine import (
    CODXJuniorSession
)

from codx.junior.globals import (
    find_project_from_file_path,
    find_all_projects
)

from codx.junior.project_watcher import ProjectWatcher
from codx.junior.knowledge.knowledge_milvus import Knowledge

from codx.junior.ai import AIManager

from codx.junior.settings import (
  read_global_settings
)

logger = logging.getLogger(__name__)

# Global store to keep track of files being checked
FILES_CHECKING = {}
FILES_CHECKING_LOCK = Lock()
CHECK_TIMEOUT = timedelta(minutes=1)

def start_background_services(app):
    logger.info("*** Starting background processes ***")
    AIManager().reload_models(read_global_settings())

    def on_project_watcher_changes(changes: [str]):
        for file_path in changes:
            project_file_changed(file_path)

    PROJECT_WATCHER = ProjectWatcher(callback=on_project_watcher_changes)

    def check_file_worker(file_path: str):
        settings = find_project_from_file_path(file_path=file_path)
        if not settings.is_valid_project_file(file_path=file_path):
            return

        async def worker():
            try:
                with FILES_CHECKING_LOCK:
                    FILES_CHECKING[file_path] = datetime.now()

                # Check mentions
                codx_junior_session = CODXJuniorSession(settings=settings)
                codx_junior_session.check_file(file_path=file_path)
            except Exception as ex:
                logger.exception(f"Error processing file changes {file_path}: {ex}")
            finally:
                with FILES_CHECKING_LOCK:
                    del FILES_CHECKING[file_path]

        asyncio.run(worker())

    def project_file_changed(file_path: str):
        settings = find_project_from_file_path(file_path)
        if not settings:
            return
        
        current_time = datetime.now()
        with FILES_CHECKING_LOCK:
            if file_path in FILES_CHECKING:
                started_time = FILES_CHECKING[file_path]
                if current_time - started_time < CHECK_TIMEOUT:
                    return
        
        file_key = f"{settings.project_name}:{file_path}"
        if not settings.project_path or \
                not Knowledge(settings=settings).is_valid_project_file(file_path=file_path):
            return
        logger.info(f"project_file_changed processing event. {file_key} - {settings.project_name}")
        Thread(target=check_file_worker, args=(file_path,)).start()

    # Load all projects and watch
    def check_projects():
        async def check(project):
            settings = CODXJuniorSession(settings=project)
            try:
                await settings.process_project_changes()
                await settings.process_wiki_changes()
            except Exception as ex:
                settings.last_error = str(ex)

        while True:
            try:
                for project in find_all_projects().values():
                    try:
                        asyncio.run(check(project=project))
                    except:
                        pass
            except Exception as ex:
                logger.exception(f"Error checking project {ex}")
            time.sleep(0.1)

    Thread(target=check_projects).start()
