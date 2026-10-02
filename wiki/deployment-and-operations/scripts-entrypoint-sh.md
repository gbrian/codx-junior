# Deployment and Operations: Entrypoint Script

This script serves as the primary initialization process for the CODX Junior environment. It ensures the environment is properly configured, dependencies are installed, and core services are maintained.

## Initialization and Environment Setup
Upon execution, the script dynamically establishes the base directory for the application:

*   **Path Configuration:** The `CODX_JUNIOR_PATH` is automatically set to the parent directory of the script location.
*   **User Environment:** It switches to the current user context and sources the environment variables defined in `${CODX_JUNIOR_PATH}/set_env.sh`.
*   **Visual Branding:** The script triggers the logo display via `scripts/logo.sh` to signify startup.

## Installation Logic
The script checks for the existence of an installation marker file (`codx-junior.installed`) to manage the deployment state:

1.  **Initial Setup:** If the marker file does not exist, it runs the `codx-junior install` command and creates the marker file to prevent redundant installations.
2.  **Application Deployment:** If the `CODX_APPS` environment variable is defined, the script iterates through the comma-separated list of applications and executes the `codx <app>` command for each to ensure all requested modules are installed.

## Runtime Maintenance
After the initialization and installation phases are complete, the script enters a persistent loop:

*   **Supervisor Mode:** While the script contains a commented-out call to `codx-junior supervisor`, the active process currently utilizes a `while true` loop with a 10-second sleep interval to keep the container or service process alive.

---

### Reference
*   **Project:** codx-junior
*   **Category:** Deployment and Operations