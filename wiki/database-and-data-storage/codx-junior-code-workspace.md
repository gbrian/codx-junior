# Database and Data Storage Configuration

This project is configured with specific workspace settings to manage database connections and project structure.

## Project Structure
The workspace is organized into the following directories:
* `client`: Project client-side code.
* `api`: Project API-related code.
* `notebooks`: Jupyter or analysis notebooks.
* `.`: Root directory of the project.

## SQLTools Configuration
The environment utilizes the `sqltools` extension for database management with the following settings:

* **Node Runtime**: The extension is configured to use the Node runtime (`sqltools.useNodeRuntime: true`).
* **Connection Details**: A connection named `app-ng-mro` is defined with the following parameters:
    * **Driver**: SQLite
    * **Database Path**: `/shared/app-ng-mro/.vscode/.codx/db/shared-app-ng-mro/chroma.sqlite3`
    * **Preview Limit**: 50 records

### References
* [Document Section: `folders`]: Defines the workspace directory mapping.
* [Document Section: `settings.sqltools`]: Defines the runtime configuration and specific database connection parameters for `app-ng-mro`.