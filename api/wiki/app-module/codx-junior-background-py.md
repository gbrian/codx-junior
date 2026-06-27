# Background Services Overview

The background processing system in `codx-api` provides automated project monitoring, change tracking, and wiki pipeline management. It leverages concurrent execution via thread pools to ensure project integrity without blocking the main API event loop.

## Service Management

The system is controlled via the `CODX_JUNIOR_API_BACKGROUND` global setting.

*   **Initialization**: Services are launched using `start_background_services()`. This function initializes AI models via `reload_models()` and spawns two persistent daemon threads:
    *   `ProjectCheckLoop`: Monitors projects for changes.
    *   `WikiCheckLoop`: Manages periodic wiki documentation generation.
*   **Termination**: Services can be shut down gracefully by setting the `RUN_BACKGROUND_PROCESSES` flag to `False` via the `stop_background_services()` function.

## Project Change Monitoring

The system continuously scans projects discovered by `find_all_projects()` and processes them in parallel.

*   **Concurrency**: Uses a `ThreadPoolExecutor` with a configurable `MAX_PROJECT_WORKERS` limit (default: 10) to manage concurrent tasks.
*   **Isolation**: Each task runs `run_project_check_thread()`, which creates a new `asyncio` event loop. This is required because `asyncio` loops are not thread-safe.
*   **Quarantine System**: To protect system resources from failing projects, a quarantine mechanism is implemented:
    *   **Logic**: Uses `is_project_in_quarantine()` to check if a project has exceeded error thresholds.
    *   **Schedule**: `QUARANTINE_DELAYS` define an exponential-style backoff (0, 1, 10, 30, 120 minutes) based on the `fail_count`.
    *   **Management**: The `update_quarantine_status()` function resets the failure counter to zero upon a successful processing cycle.

## Wiki Pipeline Management

The Wiki service periodically regenerates documentation for projects where `project_wiki` is enabled.

*   **Interval**: The process runs every `WIKI_CHECK_INTERVAL_SECONDS` (default: 600 seconds/10 minutes).
*   **Pipeline Stages**: Managed by `WikiManager` via `process_project_wiki()`:
    1.  **Dependency Graph**: Building the internal project structure.
    2.  **Domain Building**: Categorizing pages based on the graph.
    3.  **Indexing**: Constructing the final wiki index.
*   **Execution**: Similar to project checking, the wiki pipeline utilizes a thread pool to perform heavy processing in the background, ensuring the API remains responsive.

## Configuration Constants

| Constant | Default Value | Description |
| :--- | :--- | :--- |
| `PROJECT_CHECK_INTERVAL_SECONDS` | 3 | Sleep time between project scanning cycles. |
| `MAX_PROJECT_WORKERS` | 10 | Concurrent threads available for tasks. |
| `WIKI_CHECK_INTERVAL_SECONDS` | 600 | Time interval for the full wiki rebuild pipeline. |
| `QUARANTINE_DELAYS` | [0, 1, 10, 30, 120] | Delay in minutes before retrying a failed project. |

***

**References:**
*   `start_background_services`, `stop_background_services`
*   `check_projects`, `run_project_check_thread`
*   `is_project_in_quarantine`, `update_quarantine_status`
*   `check_projects_wiki`, `process_project_wiki`

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/changes/change_manager.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/global_settings.py, codx/junior/wiki/wiki_manager.py
**Imported by:** codx/junior/app.py