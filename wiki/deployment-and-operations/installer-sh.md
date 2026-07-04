# Deployment and Operations: Codx-Junior Installer

The `codx-junior` project provides a bash-based installation script to automate the building and deployment of a containerized instance.

## Overview
The installer manages the configuration, container image building, and environment setup required to run a `codx-junior` instance. It relies on `docker-compose` to manage the container lifecycle.

## Usage
To deploy the application, execute the installer script. The script accepts optional arguments to customize environment variables for the instance:

*   `-g, --user-gid`: Sets the environment variable `USER_GID`.
*   `-u, --user-uid`: Sets the environment variable `USER_UID`.
*   `-p, --port`: Sets the environment variable `CODX_JUNIOR_WEB_PORT`.

## Installation Process
The deployment workflow consists of the following steps:

1.  **Image Construction**: The script executes `docker-compose up codx-junior-build` to compile the required image.
2.  **Network Setup**: A bridge network named `codx-junior-network` is created to facilitate communication for the instance.
3.  **Instance Execution**: The script launches the application instance in detached mode using `docker-compose up -d`.

***

### References
*   [Deployment and Operations] - `codx-junior` project installer documentation.