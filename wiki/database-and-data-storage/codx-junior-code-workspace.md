# Database and Data Storage Documentation

## Overview
The project environment is structured to support multi-layered development, encompassing client-side code, API services, and data analysis notebooks. Database connectivity is managed through the SQLTools extension settings.

## Project Structure
The workspace is organized into the following directories:
* **client**: Contains client-side application logic.
* **api**: Contains server-side API implementations.
* **notebooks**: Dedicated space for data analysis and experimentation.
* **Root**: The base directory of the project.

## Database Configuration
Database interactions are configured via the `sqltools` settings to ensure seamless integration with the development environment.

### Connection Details
The project utilizes a SQLite database for data storage. The configuration includes the following parameters:
* **Connection Name**: `app-ng-mro`
* **Driver**: SQLite
* **Database Path**: `/shared/app-ng-mro/.vscode/.codx/db/shared-app-ng-mro/chroma.sqlite3`
* **Preview Limit**: 50 records

### Extension Settings
* **Node Runtime**: The `sqltools.useNodeRuntime` setting is enabled (`true`) to facilitate the execution of the SQLTools extension within the workspace.

## References
* **Folders Configuration**: Defined in the `folders` array of the workspace configuration.
* **Database Settings**: Defined in the `settings.sqltools.connections` array.
* **Runtime Settings**: Defined in `settings.sqltools.useNodeRuntime`.