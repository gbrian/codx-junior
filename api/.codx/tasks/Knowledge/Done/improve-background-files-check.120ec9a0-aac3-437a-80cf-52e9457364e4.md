# [[{"id": "120ec9a0-aac3-437a-80cf-52e9457364e4", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/api/codx/junior/background.py"], "check_lists": [], "profiles": [], "users": ["admin"], "name": "Improve background files check", "description": "The user wants to ensure that files are not checked concurrently in a background service script, unless the process exceeds one minute. I introduced a global dictionary to track files currently being processed, alongside a timestamp. A lock mechanism was implemented to manage concurrent access to this dictionary safely. The code now checks if a file is already being processed and ignores further attempts within the one-minute threshold. These changes effectively manage file processing to prevent duplicate efforts.", "created_at": "2025-07-11 10:56:20.529952", "updated_at": "2025-07-21T19:36:14.326759", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Knowledge", "column": "Done", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Knowledge/In Progress/improve-background-files-check.120ec9a0-aac3-437a-80cf-52e9457364e4.md", "model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "8173d3b2-928e-492e-aac0-b77c0882da82", "role": "user", "task_item": "", "think": "", "hide": false, "improvement": false, "created_at": "2025-07-11 10:56:20.527405", "updated_at": "2025-07-11 10:56:20.527431", "images": [], "files": ["/shared/codx-junior/api/codx/junior/background.py"], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true}]]
@file://background.py
We must keep track of the files been checked to avoid checking same file in multiple times while it's been processes.

Maybe we should keep a global store with the files been checked and the timestamp where they were added, removing after the process is done or fails.

In the case the file process takes longer than 1min (use global variable) we will remove allowing new checks to start the checking process again
## [[{"doc_id": "d08d4fdb-5038-4238-b39e-0d6d02f4d0d8", "role": "assistant", "task_item": "", "think": null, "hide": false, "improvement": false, "created_at": "2025-07-11 10:56:20.527405", "updated_at": "2025-07-11 10:56:20.527431", "images": [], "files": [], "meta_data": {"time_taken": 16.217968225479126, "first_chunk_time_taken": 0.0002455711364746094, "model": "gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false}]]
To implement the requested changes, you need to modify the code to introduce a global store that keeps track of files being processed, along with a timestamp indicating when the process started. This will help ensure that the processing of the same file doesn't happen concurrently unless the processing time exceeds a specified duration (e.g., 1 minute). Here's how you can achieve that:

```python
import logging
import time
import asyncio
import os

from datetime import datetime, timedelta
from threading import Thread, Lock

from codx.junior.engine import (
    CODXJuniorSession,
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
```

### Key Changes Made:
1. Added a global dictionary `FILES_CHECKING` to keep track of files currently being processed, along with a timestamp when they were added.

2. Used a `Lock` to synchronize access to the `FILES_CHECKING` dictionary to prevent race conditions.

3. Introduced a `CHECK_TIMEOUT` to define the maximum duration a file can be on the processing list before allowing a new check to commence.

4. Updated the `project_file_changed` function to either skip processing if a file is recently added or proceed with processing if the duration has elapsed.

This approach ensures that a file is not checked multiple times while being processed, unless the process takes exceedingly long, at which point it can be retried.