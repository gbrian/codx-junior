# Background Processing System

The background processing system in `codx-api` manages automated tasks such as project monitoring and wiki pipeline maintenance. These services operate asynchronously to ensure the system remains responsive while handling intensive tasks.

## Service Management
Background services are controlled by the `CODX_JUNIOR_API_BACKGROUND` global configuration. 
- **Start-up:** The `start_background_services` function initializes AI models via `reload_models` and launches the project checking loop in a dedicated background thread.
- **Graceful Shutdown:** `stop_background_services` can be invoked to set the `RUN_BACKGROUND_PROCESSES` flag to `False`, safely halting active loops.

## Project Monitoring
The system performs continuous project synchronization using a thread-managed architecture:
- **`check_projects`:** Runs a continuous loop that identifies active, non-quarantined projects. It utilizes a `ThreadPoolExecutor` (configured with `MAX_PROJECT_WORKERS`) to process multiple projects concurrently.
- **Concurrency Model:** Since `asyncio` event loops are not thread-safe, `run_project_check_thread` isolates each project task by creating a dedicated event loop for each worker thread.
- **Quarantine Logic:** To prevent system strain from failing projects, `update_quarantine_status` tracks failure counts. Projects are excluded from checks based on the `QUARANTINE_DELAYS` schedule (0, 1, 10, 30, and 120 minutes), which increases back-off times as failure counts rise.

## Wiki Pipeline
The system includes a secondary, lower-frequency process for managing project wikis:
- **`check_projects_wiki`:** Designed to run every 10 minutes (`WIKI_CHECK_INTERVAL_SECONDS`), this service checks for wiki-enabled projects that require a full pipeline rebuild.
- **Pipeline Stages:** The `process_project_wiki` function executes three primary steps:
    1. Building the dependency graph.
    2. Detecting and building domain pages.
    3. Indexing the wiki content.
- **Status:** Note that currently, the Wiki check loop is disabled by default to manage high AI consumption.

## Configuration and Tuning
- **Intervals:** Project monitoring occurs every 3 seconds (`PROJECT_CHECK_INTERVAL_SECONDS`).
- **Concurrency Limits:** `MAX_PROJECT_WORKERS` limits the system to 10 concurrent project processing threads.
- **Global Settings:** The system relies on `read_global_settings` to synchronize AI model configurations during the initialization phase.

***

### References
- [Project Checking and Thread Management]: `check_projects`, `run_project_check_thread`
- [Quarantine Mechanism]: `is_project_in_quarantine`, `update_quarantine_status`
- [Wiki Pipeline]: `process_project_wiki`, `check_projects_wiki`
- [Lifecycle Control]: `start_background_services`, `stop_background_services`

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/changes/change_manager.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/global_settings.py, codx/junior/wiki/wiki_manager.py
**Imported by:** codx/junior/app.py