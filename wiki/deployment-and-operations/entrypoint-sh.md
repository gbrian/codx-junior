# Deployment and Operations: codx-junior Entrypoint

The `entrypoint.sh` script serves as the primary initialization process for the **codx-junior** project. It handles user permissions, dependency installation, and service execution.

## Initialization and Permissions
Upon startup, the script performs the following synchronization tasks to ensure file system compatibility:
*   It retrieves the current user's ID (`UID`) and group ID (`GID`).
*   It updates the `codx-junior` user and group attributes to match these IDs. This ensures that the container or environment user has the appropriate ownership over files.

## Commands
The entrypoint accepts specific arguments to determine its execution path:

### Installation
If the script is invoked with the `install` argument, it performs the following:
1.  Navigates to the directory located at `${HOME}/codx-junior`.
2.  Executes the `bash codx-junior install` command.
3.  Terminates the process immediately after completion.

### Execution
If no installation command is provided, the script follows these steps:
1.  **Custom Configuration:** It checks for the existence of `/user-entrypoint.sh`. If found, it sources this file to apply user-defined configurations.
2.  **Supervisor:** It initiates the `codx-junior` supervisor process using `sudo -E` to preserve environment variables, running `${HOME}/codx-junior/codx-junior supervisor`.

## References
*   **Project:** codx-junior
*   **Category:** Deployment and Operations