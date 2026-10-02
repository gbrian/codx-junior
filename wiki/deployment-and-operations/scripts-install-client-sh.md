# Client Deployment and Operations

The client installation process is managed through a automated script designed to configure the environment and prepare the application for production.

## Environment Configuration
The deployment process initializes the environment using the following steps:
* **Path Definition**: The `CODX_JUNIOR_PATH` is dynamically set to the parent directory of the script location.
* **Environment Sourcing**: The script executes `set_env.sh` to load required variables.
* **Dependency Setup**: Calls `codx nodejs` and configures the Node Version Manager (NVM) by sourcing `$NVM_DIR/nvm.sh` and `bash_completion`.

## Compilation Process
To ensure a clean build environment, the script performs the following operations within the `client` directory:
1. **Cleanup**: Removes existing `node_modules` and `dist` directories to prevent mapping issues.
2. **Node Versioning**: Installs and switches to Node.js version `v24.12.0`.
3. **Build**: Executes `npm i` to install dependencies followed by `npm run build-only` to generate the production build.

### References
* **Category**: Deployment and Operations
* **Keywords**: deployment, operations, scripts, maintenance