# Deployment and Operations: Installation Script

The installation script is designed to automate the deployment and maintenance processes for the codx-junior project. It ensures the environment is correctly configured and that the specified applications are installed.

## Prerequisites
Before executing the script, the environment must be configured. The script relies on the `set_env.sh` file, which is sourced at the beginning of the process to load necessary `.env` variables.

## User and Group Configuration
The script includes functionality to synchronize system user and group IDs to ensure file permissions are correctly maintained within the deployment environment:

* **User ID:** If the `$USER_ID` variable is provided, the script updates the `codx-junior` user ID using `usermod`.
* **Group ID:** If the `$USER_GROUP` variable is provided, the script updates the `codx-junior` group ID using `groupmod`.
* **Permissions:** Once the IDs are set, the script recursively updates ownership of the user's home directory and the API virtual environment (`$CODX_JUNIOR_API_VENV`) to the `codx-junior` user.

## Installation Process
The script initializes by displaying a project logo, then proceeds to install applications based on the `$CODX_JUNIOR_APPS` variable.

### Supported Applications
The script iterates through the list defined in `$CODX_JUNIOR_APPS` and triggers the corresponding installation script for each recognized application:

* **client:** Executes `install_client.sh` to install the web client.
* **api:** Executes `install_api.sh` to install the API.

If an entry in `$CODX_JUNIOR_APPS` does not match these categories, the script logs an "Unknown app" error.

## Operational Safety
* **Error Handling:** The script is configured with `set -e`, meaning it will terminate execution immediately if any command returns a non-zero exit status.
* **Logging:** Standardized logging functions (`log_info` and `log_error`) are available for monitoring the progress and debugging potential issues during the installation process.

---
### References
* [codx-junior/scripts/install.sh](https://github.com/codx-junior/scripts/install.sh)