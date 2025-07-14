import logging
import time
import asyncio
from datetime import datetime, timedelta
from threading import Thread, Lock
from typing import List

from codx.junior.engine import CODXJuniorSession
from codx.junior.globals import (
  CODX_JUNIOR_API_BACKGROUND,
  find_all_projects
)
from codx.junior.settings import read_global_settings

from codx.junior.ai import AIManager

# Setup logging
logger = logging.getLogger(__name__)

# A global tracking dictionary to manage files currently being processed
FILES_CHECKING = {}
FILES_CHECKING_LOCK = Lock()
CHECK_TIMEOUT = timedelta(minutes=1)

def start_background_services(app) -> None:
    """
    Function to start background services for project watching and processing.
    """
    if not CODX_JUNIOR_API_BACKGROUND:
        return
    logger.info("*** Starting background processes ***")
    reload_models()

    # Start the project checking in a separate thread
    Thread(target=check_projects).start()

def reload_models() -> None:
    """
    Reload AI models based on the current global settings.
    """
    try:
        AIManager().reload_models(read_global_settings())
        logger.info("AI models reloaded successfully.")
    except Exception as ex:
        logger.exception(f"Failed to reload AI models: {ex}")

def check_projects() -> None:
    """
    Continuously checks for updates in all projects.
    """
    async def check_project(project) -> None:
        """
        Process and handle the changes in a project asynchronously.
        """
        settings = CODXJuniorSession(settings=project)
        try:
            await settings.process_project_changes()
            await settings.process_wiki_changes()
        except Exception as ex:
            settings.last_error = str(ex)

    while True:
        try:
            projects = find_all_projects()
            for project in projects.values():
                try:
                    asyncio.run(check_project(project=project))
                except Exception as ex:
                    logger.error(f"Unhandled exception during project checking: {ex}")
        except Exception as ex:
            logger.exception(f"Error checking projects: {ex}")
        time.sleep(0.1)
