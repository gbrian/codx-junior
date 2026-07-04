# CODX-Junior Deployment and Operations

The `codx-junior` project provides a command-line interface (CLI) script to manage the deployment, execution, and maintenance of the application.

## Overview
The script serves as the primary management tool for the API, client, and supervisor services. It ensures environment variables are loaded via `set_env.sh` and manages processes based on a project structure rooted in the `CODX_JUNIOR_PATH`.

## Commands
The CLI supports the following commands, accessible via `app.cli [command]`:

| Command | Description |
| :--- | :--- |
| `help` | Displays the help message containing available commands. |
| `install` | Executes the installation process by triggering `scripts/install.sh`. |
| `start` | Stops existing instances and runs the application (API and client). |
| `stop` | Stops the API, client, and supervisor processes. |
| `status` | Checks and reports the running status of processes based on PID files located in `./pids/`. |
| `logs` | Displays the tail of specific log files. |
| `supervisor` | Initializes and runs the supervisor service using `supervisor.conf`. |

## Operations

### Process Management
The management of application processes is handled through:
- **`stop_codx` / `kill_apps`**: Locates and terminates processes related to the API, client, and supervisor using `pgrep`. It includes a fallback to `kill -9` if a standard `kill` fails to terminate the process.
- **`run_codx_apps`**: Launches the API and client components using defined shell scripts in the `scripts/` directory, redirecting output to log files.

### Monitoring
- **Status Check**: The `status` command iterates through files in the `./pids/` directory. It confirms if a process is active by checking the corresponding PID against the current system processes.
- **Log Viewing**: Users can monitor logs by specifying a service type:
    - `api`: Shows `codx-junior-api.log`.
    - `client`: Shows `codx-junior-web.log`.
    - `supervisor`: Shows `supervisord.log`.

### Supervisor Execution
The `run_supervisor` function manages the `supervisord` service. It ensures the necessary log folder is created and checks for root privileges. If not running as root, it attempts to switch context or execution mode; otherwise, it executes `supervisord` using the project's `supervisor.conf`.

---
### References
- **Deployment and Operations Scripts**: The provided shell script document.