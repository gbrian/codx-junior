import asyncio
import logging
import time
from datetime import datetime, timedelta
from threading import Thread, Lock
from typing import Dict

from codx.junior.ai import AIManager
from codx.junior.changes.change_manager import ChangeManager
from codx.junior.globals import (
    CODX_JUNIOR_API_BACKGROUND,
)
from codx.junior.project.project_discover import (
    find_all_projects
)
from codx.junior.settings import read_global_settings

# Setup logging
logger = logging.getLogger(__name__)

# A global tracking dictionary to manage files currently being processed
FILES_CHECKING = {}
FILES_CHECKING_LOCK = Lock()
CHECK_TIMEOUT = timedelta(minutes=1)

# Quarantine settings
QUARANTINE_TRACKER: Dict[str, Dict] = {}
QUARANTINE_LOCK = Lock()
QUARANTINE_DELAYS = [0, 1, 10, 30, 120]  # Minutes

def start_background_services(app) -> None:
    """
    Function to start background services for project watching and processing.
    """
    if not CODX_JUNIOR_API_BACKGROUND:
        return
    logger.info("*** Starting background processes ***")
    reload_models()

    # Start the project checking in a separate thread
    Thread(target=check_projects, args=(True,)).start()

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


def is_project_in_quarantine(project_name: str) -> bool:
    """
    Determine if a project is in quarantine based on its last check time and the delay.
    """
    quarantine_info = QUARANTINE_TRACKER.get(project_name)
    if not quarantine_info:
        return False

    delay_minutes = QUARANTINE_DELAYS[min(quarantine_info["fail_count"], len(QUARANTINE_DELAYS) - 1)]
    next_allowed_check = quarantine_info["last_checked"] + timedelta(minutes=delay_minutes)
    return datetime.now() < next_allowed_check


def update_quarantine_status(project_name: str, success: bool) -> None:
    """
    Update the quarantine status of a project depending on whether the check was successful.
    """
    with QUARANTINE_LOCK:
        quarantine_info = QUARANTINE_TRACKER.setdefault(project_name, {"fail_count": 0, "last_checked": datetime.min})

        if success:
            quarantine_info["fail_count"] = 0  # Reset on success
        else:
            quarantine_info["fail_count"] += 1
            logger.info(f'Adding project to quarantine: {project_name} - error count: {quarantine_info["fail_count"]}')

        quarantine_info["last_checked"] = datetime.now()


def check_projects(mention_only = False) -> None:
    """
    Continuously checks for updates in all projects.
    """

    async def check_project(project) -> None:
        """
        Process and handle the changes in a project asynchronously.
        """
        try:
            session = ChangeManager(settings=project)
            #if not session.settings.metrics:
            project.metrics = session.update_project_metrics()
            await session.process_project_changes(mention_only)
            update_quarantine_status(project.project_name, success=True)
        except Exception as ex:
            update_quarantine_status(project.project_name, success=False)
            project.last_error = str(ex)
            logger.exception(f"Error processing project changes: {project.project_name}\n{ex}")

    while True:
        try:
            projects = find_all_projects()
            for project in projects.values():
                if is_project_in_quarantine(project.project_name):
                    continue

                try:
                    asyncio.run(check_project(project=project))
                except Exception as ex:
                    logger.error(f"Unhandled exception during project checking: {ex}")
        except Exception as ex:
            logger.exception(f"Error checking projects: {ex}")
        time.sleep(0.1)

