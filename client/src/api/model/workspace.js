/**
 * Workspace API — client-side model definitions.
 *
 * Mirrors the backend Pydantic models defined in:
 *   codx/junior/api/workspace_models.py
 *   codx/junior/workspaces/model.py
 *
 * Model hierarchy
 * ---------------
 *  Workspace
 *  ├── id              string        Server-assigned UUID
 *  ├── name            string        Display name
 *  ├── description     string
 *  ├── template        string        "custom" | "static-site" | "dev-stack" | …
 *  ├── folder_path     string        Unique folder under WORKSPACES_ROOT
 *  ├── project_ids     string[]      Projects mounted into the workspace
 *  ├── user_ids        string[]      Allowed usernames (empty = public)
 *  ├── apps            WorkspaceApp[]
 *  ├── env             Record<string,string>   Extra env vars for compose
 *  ├── resources       WorkspaceResources
 *  ├── use_sysbox      boolean       Run with sysbox-runc
 *  ├── status          WorkspaceStatus  (server-managed)
 *  └── updated_at      string|null   ISO-8601 timestamp (server-managed)
 *
 * WorkspaceApp
 *  ├── id      string
 *  ├── name    string
 *  ├── path    string        Plain path prefix OR full external URL
 *  ├── port    number|null   Container port (docker-label routing)
 *  ├── scheme  "http"|"https"
 *  └── roles   string[]      RBAC: empty = all roles
 *
 * WorkspaceResources
 *  ├── cpus     string|null   e.g. "2"
 *  ├── memory   string|null   e.g. "4g"
 *  └── shm_size string        default "512m"
 *
 * WorkspaceStatus
 *  One of: "stopped" | "starting" | "running" | "error"
 */

/**
 * @typedef {'stopped'|'starting'|'running'|'error'} WorkspaceStatus
 */

/**
 * @typedef {Object} WorkspaceResources
 * @property {string|null} cpus      - CPU limit, e.g. "2"
 * @property {string|null} memory    - Memory limit, e.g. "4g"
 * @property {string}      shm_size  - Shared memory size, default "512m"
 */

/**
 * @typedef {Object} WorkspaceApp
 * @property {string}   id      - Unique app identifier
 * @property {string}   name    - Display name
 * @property {string}   path    - Path prefix or full external URL
 * @property {number|null} port - Container port (used for docker-label routing)
 * @property {'http'|'https'} scheme - Protocol scheme
 * @property {string[]} roles   - RBAC roles; empty means all roles allowed
 */

/**
 * @typedef {Object} Workspace
 * @property {string}             id          - Server-assigned UUID
 * @property {string}             name        - Human-readable display name
 * @property {string}             description - Optional description
 * @property {string}             template    - Template id used at creation time
 * @property {string}             folder_path - Unique folder name under WORKSPACES_ROOT
 * @property {string[]}           project_ids - Project IDs mounted into the workspace
 * @property {string[]}           user_ids    - Allowed usernames; empty = accessible by all
 * @property {WorkspaceApp[]}     apps        - Exposed applications
 * @property {Record<string,string>} env      - Extra env vars forwarded to docker-compose
 * @property {WorkspaceResources} resources   - CPU / memory / shm constraints
 * @property {boolean}            use_sysbox  - Whether to run containers with sysbox-runc
 * @property {WorkspaceStatus}    status      - Current lifecycle status (server-managed)
 * @property {string|null}        updated_at  - ISO-8601 last-modified timestamp (server-managed)
 */

// ── Request / response schemas ──────────────────────────────────────────────

/**
 * Body for POST /api/workspaces/{id}/file
 * @typedef {Object} WorkspaceFileWriteRequest
 * @property {string} content - Full UTF-8 text to write to the file
 */

/**
 * Response for GET /api/workspaces/{id}/file
 * @typedef {Object} WorkspaceFileReadResponse
 * @property {string} path    - Relative path inside the workspace directory
 * @property {string} content - Full UTF-8 text content of the file
 */

/**
 * Response for POST /api/workspaces/{id}/file
 * @typedef {Object} WorkspaceFileWriteResponse
 * @property {string} path   - Relative path that was written
 * @property {string} status - Always "saved" on success
 */

/**
 * Response for GET /api/workspaces/{id}/status
 * @typedef {Object} WorkspaceStatusResponse
 * @property {WorkspaceStatus} status - Live container status from docker compose ps
 */

/**
 * Response for GET /api/workspaces/{id}/logs
 * @typedef {Object} WorkspaceLogsResponse
 * @property {string} logs - Raw combined stdout+stderr from all containers
 */

/**
 * Response for DELETE /api/workspaces/{id}
 * @typedef {Object} WorkspaceDeleteResponse
 * @property {string} status - Always "deleted" on success
 */

/**
 * Factory — create a blank Workspace with safe defaults.
 * Use this when building a new workspace in the UI before POSTing to the API.
 *
 * @param {Partial<Workspace>} overrides
 * @returns {Workspace}
 */
export function createWorkspace(overrides = {}) {
  return {
    id: '',
    name: '',
    description: '',
    template: 'custom',
    folder_path: '',
    project_ids: [],
    user_ids: [],
    apps: [],
    env: {},
    resources: createWorkspaceResources(),
    use_sysbox: false,
    status: 'stopped',
    updated_at: null,
    ...overrides,
  }
}

/**
 * Factory — create a blank WorkspaceApp with safe defaults.
 *
 * @param {Partial<WorkspaceApp>} overrides
 * @returns {WorkspaceApp}
 */
export function createWorkspaceApp(overrides = {}) {
  return {
    id: '',
    name: '',
    path: '',
    port: null,
    scheme: 'http',
    roles: [],
    ...overrides,
  }
}

/**
 * Factory — create a blank WorkspaceResources with safe defaults.
 *
 * @param {Partial<WorkspaceResources>} overrides
 * @returns {WorkspaceResources}
 */
export function createWorkspaceResources(overrides = {}) {
  return {
    cpus: null,
    memory: null,
    shm_size: '512m',
    ...overrides,
  }
}

/** All valid workspace status values. */
export const WORKSPACE_STATUSES = /** @type {WorkspaceStatus[]} */ (['stopped', 'starting', 'running', 'error'])