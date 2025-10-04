# [[{"id": "046fb35a-8dd2-4f9a-8c3d-8feb1ae8b526", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/api/codx/junior/background.py"], "check_lists": [], "profiles": [], "users": ["admin"], "name": "Quarentine failing projects", "description": "In this conversation, a Python script was provided to manage background services for project updates, featuring a logging setup. A request was made to implement a quarantine system for projects that cause errors, introducing increasing delays before rechecking these projects based on consecutive failures. A potential solution was provided, introducing a quarantine tracking dictionary to manage fail counts and last checked times. The quarantine delays increase from 1 minute to 120 minutes, depending on the number of failures. The updated code includes functions to check and update quarantine statuses, and integrates these into the project checking routine.", "created_at": "2025-07-15 09:30:58.675902", "updated_at": "2025-07-21T19:36:14.339326", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Knowledge", "column": "Done", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Knowledge/In Progress/quarentine-failing-projects.046fb35a-8dd2-4f9a-8c3d-8feb1ae8b526.md", "model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "b9cd482a-50c3-4ac3-a3a5-4e94b7492efd", "role": "user", "task_item": "", "think": "", "hide": false, "improvement": false, "created_at": "2025-07-15 09:30:58.674082", "updated_at": "2025-07-15 09:30:58.674109", "images": [], "files": ["/shared/codx-junior/api/codx/junior/background.py", "/shared/codx-junior/api/codx/junior/background.py"], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true}]]
@file://background.py
We must put project that are causing errors when checking changes into quarentine to avoid overload logs with error messages. I recommend a increasing delay in re-check them, so if they fail we put them in quarentine for 1min, 10min if fial count is 2, 30min if fail count is 3 and 120min if 4 or more, reseting count once it works fine  
## [[{"doc_id": "b08ca5a7-3be8-4a8f-90f3-a43acefb52d1", "role": "assistant", "task_item": "", "think": null, "hide": false, "improvement": false, "created_at": "2025-07-15 09:30:58.674082", "updated_at": "2025-07-15 09:30:58.674109", "images": [], "files": [], "meta_data": {"time_taken": 14.174602031707764, "first_chunk_time_taken": 0.00026869773864746094, "model": "gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false}]]
Sure, here's how you can modify your code to implement a quarantine system for projects that have errors during checking:

```python /shared/codx-junior/api/codx/junior/background.py
/shared/codx-junior/api/codx/junior/background.py
import logging
import time
import asyncio
from datetime import datetime, timedelta
from threading import Thread, Lock
from typing import List, Dict

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

        quarantine_info["last_checked"] = datetime.now()

def check_projects() -> None:
    """
    Continuously checks for updates in all projects.
    """
    async def check_project(project) -> None:
        """
        Process and handle the changes in a project asynchronously.
        """
        session = CODXJuniorSession(settings=project)
        try:
            await session.process_project_changes()
            await session.process_wiki_changes()
            update_quarantine_status(project.project_name, success=True)
        except Exception as ex:
            update_quarantine_status(project.project_name, success=False)
            project.last_error = str(ex)
            logger.error(f"Error processing project changes: {project.project_name}\n{ex}")

    while True:
        try:
            projects = find_all_projects()
            for project in projects.values():
                if is_project_in_quarantine(project.project_name):
                    logger.info(f"Skipping project (in quarantine): {project.project_name}")
                    continue

                try:
                    asyncio.run(check_project(project=project))
                except Exception as ex:
                    logger.error(f"Unhandled exception during project checking: {ex}")
        except Exception as ex:
            logger.exception(f"Error checking projects: {ex}")
        time.sleep(0.1)

```

This modified code introduces a quarantine system where projects that cause errors are temporarily put on hold from being checked based on the number of consecutive failures. The `QUARANTINE_TRACKER` dictionary keeps track of the fail count and the last checked time for each project, and this information is used to determine if a project should be checked or skipped in the next cycle. The fail count is reset upon a successful check.