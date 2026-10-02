# Background Service Overview

The background services layer is responsible for asynchronously monitoring, processing changes in projects, and maintaining project-level resources like the Wiki index. These processes run independently (daemon threads) to ensure continuous operation for resource updates and content synchronization.

## ⚙️ Core Functionality

### Project Health Monitoring and Change Detection
Project change detection runs continuously via `check_projects()`. This routine iterates through all discovered projects (`find_all_projects`) to determine if any project requires update processing.

**Execution Details:**
*   **Loop Cycle:** The check operates on a set interval defined by `PROJECT_CHECK_INTERVAL_SECONDS` (3 seconds).
*   **Concurrency:** All eligible projects are submitted to a thread pool executor (`ThreadPoolExecutor`) with a maximum of `MAX_PROJECT_WORKERS` (10) to manage load.
*   **Processing Unit:** Each individual project check runs within an isolated async task using `run_project_check_thread`, ensuring that asynchronous tasks do not conflict across threads.

### Quarantine System Implementation
The system incorporates a robust quarantine mechanism to prevent continuous processing attempts on projects that are consistently failing (e.g., due to code or environment errors).

*   **Detection:** A project's status is checked using `is_project_in_quarantine()` by examining the `QUARANTINE_TRACKER`.
*   **Failure Handling:** If a project fails to process changes, its failure count (`fail_count`) increases. When failure occurs, the system updates the quarantine status via `update_quarantine_status()`.
*   **Retry Logic:** The delay schedule is controlled by `QUARANTINE_DELAYS` (defined as minutes: [0, 1, 10, 30, 120]). The required waiting time before a project can be checked again is determined by the failure count index.

### Wiki Pipeline Management
Wiki rebuilding is handled separately to minimize performance impact on the main change detection loop. This process runs via `check_projects_wiki()`.

*   **Frequency:** A full wiki pipeline rebuild is scheduled to run only once every `WIKI_CHECK_INTERVAL_SECONDS` (600 seconds, or 10 minutes).
*   **Criteria:** Only projects marked with `project_wiki = True` are considered for rebuilds.
*   **Pipeline Steps:** The process executes the full sequence of wiki generation tasks:
    1.  Building dependency graph (`WikiManager().build_dependency_graph`).
    2.  Detecting and gathering domain pages (`WikiManager().build_domains`).
    3.  Final build and indexing of the Wiki index (`WikiManager().build_wiki_index`).

## 🔄 Service Lifecycle Management

### Starting Background Services
Background services are initiated via `start_background_services()`. This function first checks the global switch (`CODX_JUNIOR_API_BACKGROUND`) and, if enabled, proceeds to:
1.  Reload AI models using `reload_models()`, ensuring any updated configurations are applied to the `AIManager`.
2.  Start the project monitoring loop (ProjectCheckLoop).
3.  Start the dedicated Wiki checking loop (WikiCheckLoop).

### Stopping Background Services
To gracefully halt all background activities, the `stop_background_services()` asynchronous function sets the global flag `RUN_BACKGROUND_PROCESSES` to `False`, signaling all running loops to terminate safely.

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/changes/change_manager.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/global_settings.py, codx/junior/wiki/wiki_manager.py
**Imported by:** codx/junior/app.py