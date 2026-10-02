# Codx Junior Core

## Overview
The **Codx Junior Core** domain serves as the structural foundation for the Codx Junior API. It is responsible for managing critical background operations, facilitating system-wide data persistence, and maintaining the integrity of configuration settings. 

This domain provides the necessary infrastructure to track architectural modifications through its change management system and acts as the central hub for administrative maintenance, including model reloading and the management of AI-model lifecycles. It also hosts the internal documentation required to support consistent database and storage configurations across the application.

## Files in Domain
- `/home/codx-junior/codx-junior/api/wiki/database-and-data-storage/readme-md.md`: Documentation concerning database schemas, storage architectures, and persistence strategies.
- `/home/codx-junior/codx-junior/api/codx/junior/changes/change_manager.py`: Core logic for tracking, logging, and managing system changes and configuration updates.
- `/home/codx-junior/codx-junior/api/codx/junior/background.py`: Execution layer for asynchronous background tasks, including system heartbeat monitors and periodic service maintenance.

## Dependencies
This domain currently operates as the primary architectural layer and does not list explicit internal domain dependencies. It relies on the underlying system runtime and configured environment variables to execute background services and persistent storage operations.

## Used By
This domain functions as a core provider for the broader Codx Junior ecosystem. It is utilized by higher-level modules requiring:
* Background task execution (e.g., quarantine-schedule and quarantine-status).
* Access to global system settings.
* Model management (via the AIManager for tasks like `reload-models`).
* Documentation and configuration standards for storage management.

## Entry Points
- **/home/codx-junior/codx-junior/api/wiki/database-and-data-storage/readme-md.md**: The primary reference point for developers to understand storage constraints and database architecture.
- **/home/codx-junior/codx-junior/api/codx/junior/changes/change_manager.py**: The interface used by administrative tools to record and audit systemic changes.
- **/home/codx-junior/codx-junior/api/codx/junior/background.py**: The trigger point for initiating and monitoring long-running background services.