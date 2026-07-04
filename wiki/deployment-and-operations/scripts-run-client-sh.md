# Client Deployment and Operations

The client-side deployment and maintenance of the `codx-junior` project is managed through automated shell scripts designed to ensure the correct environment configuration and application lifecycle management.

## Overview
The deployment process dynamically resolves the project path and ensures all necessary environment variables and dependencies are active before launching the client application.

## Prerequisites and Environment Setup
Before starting the client, the following environment configurations are performed:
* **Path Resolution:** The system automatically identifies the project root directory relative to the script location.
* **Environment Loading:** The script sources `set_env.sh` to initialize project-specific environment variables.
* **Node Version Management:** The script utilizes `nvm` (Node Version Manager) to install and use Node.js version `v24.12.0`. It also loads `nvm` bash completion for shell integration.

## Execution Modes
The application supports two primary operational modes, which are toggled via the `DEBUG` environment variable.

### Debug Mode
When the `DEBUG` variable is set, the system executes in development mode:
* **Dependency Installation:** Runs `npm install` to ensure all packages are up to date.
* **Development Server:** Starts the client using `npm run dev`.

### Production Mode
When the `DEBUG` variable is not set (default), the system executes in production mode:
* **Preview Server:** The client is started using `npm run preview`.

## Operational Logs
Upon execution, the script outputs the following diagnostic information to the console:
* `CODX_JUNIOR_PATH`: The resolved root path of the project.
* `USER`: The system user account executing the process.
* `HOME`: The home directory of the current user.
* Execution mode status (DEBUG vs. PRODUCTION).

***

### References
* [Deployment and Operations] - `scripts/run_client.sh`