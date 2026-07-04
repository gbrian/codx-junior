# Background Service Management Guide

The platform uses extensive background services to maintain data synchronization, manage project health, and update internal knowledge bases (Wiki). These services run asynchronously to ensure that long-running tasks do not affect primary request responsiveness.

## System Overview

Background processes are controlled by a global flag (`CODX_JUNIOR_API_BACKGROUND`). Services must be started explicitly through the `start_background_services` function and can be gracefully stopped via `stop_background_services`.

### 1. Project Change Watching (Synchronization)

This service is responsible for monitoring all associated projects to detect and process changes within their configurations or content.

*   **Purpose:** To run project-specific update pipelines using the `ChangeManager` class, ensuring internal data reflects external source state.
*   **Execution Loop:** The check runs continuously in a dedicated thread at a fixed interval (`PROJECT_CHECK_INTERVAL_SECONDS`, currently set to 3 seconds).
*   **Concurrency:** Instead of sequential processing, all eligible projects are submitted concurrently to a `ThreadPoolExecutor` (limited by `MAX_PROJECT_WORKERS`). This design maximizes throughput for simultaneous check cycles.

### 2. Project Quarantine Mechanism

To protect the stability of the core system from projects that consistently fail checks, a quarantine mechanism is enforced.

*   **Detection:** If a project fails its processing cycle (`process_project_changes`), its failure counter increases, and it may be quarantined.
*   **Quarantine State:** A quarantined project will have its subsequent background check attempts blocked.
*   **Delay Schedule:** The service uses an escalating delay schedule defined in `QUARANTINE_DELAYS` (e.g., 0, 1, 10, 30, 120 minutes). This means the required wait time between consecutive failures increases with each failure count (`fail_count`).
*   **Recovery:** A project must pass a full check cycle to reset its failure counter and exit quarantine.

### 3. Wiki Pipeline Management (Content Indexing)

This service is dedicated to maintaining the interconnected knowledge base accessible via the Wiki feature. It runs independently of general project changes but relies on project content for data sourcing.

*   **Functionality:** The full wiki pipeline (`process_project_wiki`) involves three major, asynchronous stages:
    1.  Building the dependency graph (identifying related pages and structures).
    2.  Detecting and building domain-specific pages.
    3.  Creating and indexing the comprehensive Wiki index.
*   **Execution Loop:** This service runs on a separate background loop (`check_projects_wiki`) and is configured to rebuild the entire Wiki only after an interval of `WIKI_CHECK_INTERVAL_SECONDS` (currently 600 seconds, or 10 minutes), even if the project's general check cycle initiates.

### 4. Model Management and Lifecycle

*   **AI Model Reloading:** The system supports explicit reloading of advanced AI models using `AIManager().reload_models()`, which reads configuration from global settings to ensure components are always running against the latest ruleset.
*   **Start/Stop Hooks:** Background services can be initialized (`start_background_services`) or shut down gracefully (`stop_background_services`), allowing for controlled deployment and maintenance cycles.

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/changes/change_manager.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/global_settings.py, codx/junior/wiki/wiki_manager.py
**Imported by:** codx/junior/app.py