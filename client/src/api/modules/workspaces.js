/**
 * Workspaces API module
 *
 * Covers all workspace-related API operations:
 *   - CRUD (list, get, create, update, delete)
 *   - Templates
 *   - Lifecycle (start, stop, status, logs)
 *   - Workspace files (list, read, write)
 *
 * Mirrors the backend router defined in:
 *   codx/junior/api/workspaces.py
 *
 * @typedef {import('../model/workspace.js').Workspace}              Workspace
 * @typedef {import('../model/workspace.js').WorkspaceApp}           WorkspaceApp
 * @typedef {import('../model/workspace.js').WorkspaceResources}     WorkspaceResources
 * @typedef {import('../model/workspace.js').WorkspaceStatus}        WorkspaceStatus
 * @typedef {import('../model/workspace.js').WorkspaceStatusResponse} WorkspaceStatusResponse
 * @typedef {import('../model/workspace.js').WorkspaceLogsResponse}  WorkspaceLogsResponse
 * @typedef {import('../model/workspace.js').WorkspaceFileReadResponse} WorkspaceFileReadResponse
 * @typedef {import('../model/workspace.js').WorkspaceFileWriteResponse} WorkspaceFileWriteResponse
 * @typedef {import('../model/workspace.js').WorkspaceDeleteResponse} WorkspaceDeleteResponse
 */

export const workspacesModule = (API) => ({

  // ── CRUD ─────────────────────────────────────────────────────────────────

  /**
   * List all workspaces accessible to the authenticated user.
   * Admins receive all workspaces; regular users only see public ones
   * or those where their username appears in user_ids.
   * @returns {Promise<Workspace[]>}
   */
  list() {
    return API.get('/api/workspaces')
  },

  /**
   * Fetch a single workspace by id.
   * Returns 403 if the authenticated user lacks access.
   * @param {string} workspaceId
   * @returns {Promise<Workspace>}
   */
  get(workspaceId) {
    return API.get(`/api/workspaces/${workspaceId}`)
  },

  /**
   * Create a new workspace (admin only).
   *
   * ``folder_path`` is required and must be unique.
   * ``id`` is always assigned server-side — any supplied value is ignored.
   *
   * @param {Workspace} workspace
   * @returns {Promise<Workspace>}
   */
  create(workspace) {
    return API.post('/api/workspaces', workspace)
  },

  /**
   * Replace workspace metadata (admin only).
   * Send the full Workspace object; the workspace must already exist
   * (identified by its ``id``).
   *
   * @param {Workspace} workspace
   * @returns {Promise<Workspace>}
   */
  update(workspace) {
    return API.put('/api/workspaces', workspace)
  },

  /**
   * Delete a workspace (admin only).
   * Removes the workspace file from disk.
   *
   * @param {string} workspaceId
   * @returns {Promise<WorkspaceDeleteResponse>}
   */
  delete(workspaceId) {
    return API.del(`/api/workspaces/${workspaceId}`)
  },

  // ── Templates ─────────────────────────────────────────────────────────────

  templates: {
    /**
     * Return all available workspace starter templates (admin only).
     * Pass template.id as Workspace.template when creating a workspace.
     * @returns {Promise<Object[]>}
     */
    list() {
      return API.get('/api/workspaces/templates')
    },
  },

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  lifecycle: {
    /**
     * Start all services defined in the workspace's docker-compose.yaml
     * (docker compose up -d).
     * Returns updated Workspace with status "running" on success or "error" on failure.
     * Prerequisite: a valid docker-compose.yaml must exist — upload one first via files.write().
     *
     * @param {string} workspaceId
     * @returns {Promise<Workspace>}
     */
    start(workspaceId) {
      return API.post(`/api/workspaces/${workspaceId}/start`, {})
    },

    /**
     * Stop all running containers in the workspace (docker compose stop).
     * Data volumes are preserved.
     *
     * @param {string} workspaceId
     * @returns {Promise<Workspace>}
     */
    stop(workspaceId) {
      return API.post(`/api/workspaces/${workspaceId}/stop`, {})
    },

    /**
     * Return the live container status by querying docker compose ps.
     * Unlike Workspace.status (persisted), this always reflects real Docker state.
     * Possible values: stopped | starting | running | error
     *
     * @param {string} workspaceId
     * @returns {Promise<WorkspaceStatusResponse>}
     */
    status(workspaceId) {
      return API.get(`/api/workspaces/${workspaceId}/status`)
    },

    /**
     * Return the last ``tail`` lines of combined container logs (admin only).
     * Aggregates stdout + stderr from all services (docker compose logs --tail=N).
     *
     * @param {string} workspaceId
     * @param {number} [tail=200] - Number of log lines (1–5000)
     * @returns {Promise<WorkspaceLogsResponse>}
     */
    logs(workspaceId, tail = 200) {
      return API.get(`/api/workspaces/${workspaceId}/logs?tail=${tail}`)
    },
  },

  // ── Workspace files ───────────────────────────────────────────────────────

  files: {
    /**
     * List files and folders in a workspace directory.
     * Returns an object with 'files' and 'folders' lists.
     *
     * @param {string} workspaceId
     * @param {string} [path=''] - Relative path within workspace (default: root)
     * @returns {Promise<{ files: string[], folders: string[] }>}
     */
    list(workspaceId, path = '') {
      const qs = path ? `?path=${encodeURIComponent(path)}` : ''
      return API.get(`/api/workspaces/${workspaceId}/files${qs}`)
    },

    /**
     * Read a file from the workspace directory.
     * ``filePath`` must be relative to the workspace root.
     * Path traversal is blocked server-side — escaping the directory returns 400.
     *
     * @param {string} workspaceId
     * @param {string} filePath  - Relative path, e.g. "docker-compose.yaml"
     * @returns {Promise<WorkspaceFileReadResponse>}
     */
    // CHANGED: switched from GET /api/workspaces/{id}/file?path=... (query param)
    //          to GET /api/workspaces/{id}/files/{file_path} (path param), matching backend route
    read(workspaceId, filePath) {
      return API.get(`/api/workspaces/${workspaceId}/files/${filePath}`)
    },

    /**
     * Write (create or overwrite) a file in the workspace directory.
     * Missing parent directories are created automatically.
     * Path traversal is blocked server-side — escaping the workspace root returns 400.
     *
     * @param {string} workspaceId
     * @param {string} filePath  - Relative path to write, e.g. "docker-compose.yaml"
     * @param {string} content   - Full UTF-8 text content
     * @returns {Promise<WorkspaceFileWriteResponse>}
     */
    // CHANGED: switched from POST /api/workspaces/{id}/file?path=... (query param)
    //          to POST /api/workspaces/{id}/files/{file_path} (path param), matching backend route
    write(workspaceId, filePath, content) {
      return API.post(`/api/workspaces/${workspaceId}/files/${filePath}`, { content })
    },
  },
})