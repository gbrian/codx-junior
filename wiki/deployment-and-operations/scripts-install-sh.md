# Deployment and Operations: Installation Script

The installation script facilitates the deployment and maintenance of the `codx-junior` project by automating user environment configuration and application installation.

## Prerequisites
Before executing the script, the environment variables must be loaded using the `set_env.sh` script located in the `CODX_JUNIOR_PATH`.

## Functionality

### User Identity Management
The script ensures that the `codx-junior` system user and group IDs align with the environment configuration:
* **User ID**: If `USER_ID` is defined, the script updates the user ID for `codx-junior`.
* **Group ID**: If `USER_GROUP` is defined, the script updates the group ID for `codx-junior`.
* **Permissions**: Ownership of the home directory and the API virtual environment (`CODX_JUNIOR_API_VENV`) is recursively assigned to the `codx-junior` user.

### Application Installation
The script iterates through the apps defined in the `CODX_JUNIOR_APPS` variable and executes the corresponding installation logic:

* **client**: Executes `install_client` by running `scripts/install_client.sh`.
* **api**: Executes `install_api` by running `scripts/install_api.sh`.
* **Other**: Any undefined application name results in an "Unknown app" warning.

## Error Handling
* The script is configured to stop execution immediately if any command fails (`set -e`).
* Logging is provided via standard `log_info` and `log_error` helper functions to track the installation progress.

## Initialization
The script initiates the process by displaying the project logo via `scripts/logo.sh` and logs the status of the installation to the console.