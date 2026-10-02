# codx-junior Deployment and Operations Guide

This document provides instructions for managing the deployment and operation of the `codx-junior` application using the provided CLI script.

## CLI Usage

The application is managed through a central CLI interface. To view available commands, run:

```bash
./app.cli help
```

### Commands

| Command | Description |
| :--- | :--- |
| `help` | Displays the help message with available commands. |
| `install` | Executes the installation process by invoking `scripts/install.sh`. |
| `run` / `start` | Starts the application by invoking the API and client run scripts. Note: This command automatically triggers `stop` before starting to ensure a clean state. |
| `stop` | Stops all running application components (API, client, and supervisor processes). |
| `status` | Checks the health of the application by inspecting PIDs stored in the `./pids/` directory. |
| `logs [type]` | Displays the last 100 lines of a specified log file. |
| `supervisor` | Initializes the supervisor process using the configuration at `supervisor.conf`. |

## Operations

### Starting and Stopping
The `start_codx` function performs a safe start by calling `stop_codx` first. This ensures that any existing instances of the API or client are terminated before new ones are launched via `run_api.sh` and `run_client.sh`.

### Monitoring Status
The `status` command iterates through all `.pid` files located in the `./pids/` folder. It verifies if the processes associated with these PIDs are currently active via the system `ps` command.

### Accessing Logs
To view logs, use the `logs` command followed by the log type:
*   `api`: Displays `codx-junior-api.log`.
*   `client`: Displays `codx-junior-web.log`.
*   `supervisor`: Displays `supervisord.log`.

Logs are tracked using the `tail -f` command, allowing for real-time monitoring of application output.

### Process Management
The system includes robust termination logic:
1.  **Standard Kill**: Attempts to stop processes gracefully.
2.  **Forced Kill**: If a process remains active after a standard `kill`, the script escalates to `kill -9`.
3.  **Supervisor**: The supervisor can be run as root if the environment requires it; otherwise, it executes under the current user context.

---

### References
*   **Deployment and Operations**: Primary script logic for installation, execution, and monitoring (`app.cli`).
*   **Process Management**: `kill_pid` and `kill_apps` functions handling lifecycle operations.
*   **Environment Configuration**: `set_env.sh` (sourced at runtime to load necessary variables).