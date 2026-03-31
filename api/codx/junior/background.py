import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from threading import Lock, Thread
from typing import Dict, List

from codx.junior.ai import AIManager
from codx.junior.changes.change_manager import ChangeManager
from codx.junior.globals import (
    CODX_JUNIOR_API_BACKGROUND,
)
from codx.junior.project.project_discover import (
    find_all_projects
)
from codx.junior.global_settings import read_global_settings

# Setup logging
logger = logging.getLogger(__name__)

# Quarantine settings
QUARANTINE_TRACKER: Dict[str, Dict] = {}
QUARANTINE_LOCK = Lock()
QUARANTINE_DELAYS: List[int] = [0, 1, 10, 30, 120]  # Minutes

# Background process control flag
RUN_BACKGROUND_PROCESSES: bool = True

# Interval between project check cycles (seconds)
PROJECT_CHECK_INTERVAL_SECONDS: int = 3

# Maximum number of concurrent project-check threads in the pool
MAX_PROJECT_WORKERS: int = 10


def start_background_services(stop_event) -> None:
    """
    Start background services for project watching and processing.

    Args:
        stop_event: A threading event used to signal when services should stop.
    """
    if not CODX_JUNIOR_API_BACKGROUND:
        logger.info("Background services are disabled via CODX_JUNIOR_API_BACKGROUND.")
        return

    global RUN_BACKGROUND_PROCESSES

    RUN_BACKGROUND_PROCESSES = True
    logger.info("*** Starting background processes ***")
    reload_models()

    # Start the project checking loop in a dedicated background thread
    Thread(target=check_projects, name="ProjectCheckLoop", daemon=True).start()


async def stop_background_services() -> None:
    """
    Stop all running background services gracefully.
    """
    if not CODX_JUNIOR_API_BACKGROUND:
        return

    global RUN_BACKGROUND_PROCESSES

    logger.info("Stopping background processes")
    RUN_BACKGROUND_PROCESSES = False


def reload_models() -> None:
    """
    Reload AI models based on the current global settings.
    """
    try:
        AIManager().reload_models(read_global_settings())
        logger.info("AI models reloaded successfully.")
    except Exception as ex:
        logger.exception("Failed to reload AI models: %s", ex)


def is_project_in_quarantine(project_name: str) -> bool:
    """
    Determine if a project is in quarantine based on its last check time and delay schedule.

    Args:
        project_name: The name of the project to check.

    Returns:
        True if the project is currently in quarantine, False otherwise.
    """
    quarantine_info = QUARANTINE_TRACKER.get(project_name)
    if not quarantine_info:
        return False

    delay_index = min(quarantine_info["fail_count"], len(QUARANTINE_DELAYS) - 1)
    delay_minutes = QUARANTINE_DELAYS[delay_index]
    next_allowed_check = quarantine_info["last_checked"] + timedelta(minutes=delay_minutes)
    return datetime.now() < next_allowed_check


def update_quarantine_status(project_name: str, success: bool) -> None:
    """
    Update the quarantine status of a project based on the outcome of the last check.

    Args:
        project_name: The name of the project to update.
        success: True if the last check was successful, False otherwise.
    """
    with QUARANTINE_LOCK:
        quarantine_info = QUARANTINE_TRACKER.setdefault(
            project_name,
            {"fail_count": 0, "last_checked": datetime.min}
        )

        if success:
            quarantine_info["fail_count"] = 0  # Reset failure counter on success
        else:
            quarantine_info["fail_count"] += 1
            logger.info(
                "Adding project to quarantine: %s - error count: %d",
                project_name,
                quarantine_info["fail_count"]
            )

        quarantine_info["last_checked"] = datetime.now()


async def process_project_changes(project) -> None:
    """
    Asynchronously process and handle changes for a single project.

    Args:
        project: The project settings object containing project metadata.
    """
    try:
        session = ChangeManager(settings=project)
        logger.info(">>>>> Checking project: %s", project.project_name)
        await session.process_project_changes()
        update_quarantine_status(project.project_name, success=True)
    except (OSError, RuntimeError, ValueError) as ex:
        update_quarantine_status(project.project_name, success=False)
        project.last_error = str(ex)
        logger.exception("Error processing project changes for %s: %s", project.project_name, ex)


def run_project_check_thread(project) -> None:
    """
    Entry point for a per-project worker in the thread pool.
    Runs the async project change processing in its own isolated event loop,
    since each thread needs its own loop (asyncio loops are not thread-safe).

    Args:
        project: The project settings object to process.
    """
    logger.debug("Thread started for project: %s", project.project_name)
    try:
        # Each thread gets its own event loop to safely run async code
        asyncio.run(process_project_changes(project=project))
    except RuntimeError as ex:
        logger.error(
            "Unhandled runtime error in thread for project %s: %s",
            project.project_name,
            ex
        )
    logger.debug("Thread finished for project: %s", project.project_name)


def check_projects() -> None:
    """
    Continuously checks all projects for updates in parallel using a ThreadPoolExecutor.

    Each non-quarantined project is submitted as a task to the pool, which runs
    `run_project_check_thread` concurrently up to MAX_PROJECT_WORKERS at a time.
    The cycle waits for all submitted tasks to complete before sleeping and repeating.

    """
    while RUN_BACKGROUND_PROCESSES:
        try:
            projects = find_all_projects()
            eligible_projects = [
                project for project in projects.values()
                if not is_project_in_quarantine(project.project_name)
            ]

            skipped = len(projects) - len(eligible_projects)
            if skipped:
                logger.debug("Skipping %d quarantined project(s) this cycle.", skipped)

            if not eligible_projects:
                logger.debug("No eligible projects to check this cycle.")
            else:
                logger.info(
                    "Submitting %d project(s) to thread pool (max_workers=%d).",
                    len(eligible_projects),
                    MAX_PROJECT_WORKERS
                )

                # Use a pool so we don't spin up unlimited threads when there are many projects
                with ThreadPoolExecutor(
                    max_workers=MAX_PROJECT_WORKERS,
                    thread_name_prefix="ProjectCheck"
                ) as pool:
                    # Submit one task per eligible project
                    future_to_project = {
                        pool.submit(run_project_check_thread, project): project
                        for project in eligible_projects
                    }

                    # Iterate over futures as they complete to log results promptly
                    for future in as_completed(future_to_project):
                        project = future_to_project[future]
                        try:
                            future.result()  # Re-raise any unhandled exception from the worker
                            logger.debug(
                                "Project check completed successfully: %s",
                                project.project_name
                            )
                        except (OSError, RuntimeError, ValueError) as ex:
                            logger.error(
                                "Project check raised an exception for %s: %s",
                                project.project_name,
                                ex
                            )

        except (OSError, RuntimeError, ValueError) as ex:
            logger.exception("Error during project check cycle: %s", ex)

        time.sleep(PROJECT_CHECK_INTERVAL_SECONDS)

# Made with ❤️ by codx-junior