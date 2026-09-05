/**
 * Logs API module
 * Handles AI request/response log retrieval and management
 */

/**
 * Build a query string from logs filter params.
 * Omits undefined/null values and converts camelCase to snake_case.
 */
function _buildLogsQS(params) {
  const keyMap = {
    startDate: 'start_date',
    endDate: 'end_date',
    username: 'username',
    project: 'project',
    model: 'model',
    provider: 'provider',
    direction: 'direction',
    sessionId: 'session_id',
    page: 'page',
    pageSize: 'page_size',
  }
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${keyMap[k] || k}=${encodeURIComponent(v)}`)
  return parts.length ? `?${parts.join('&')}` : ''
}

export const logsModule = (API) => ({
  // ── Application logs ───────────────────────────────────────────────────

  /**
   * Read a specific application log file.
   * @param {string} logName - The log file name
   * @param {number} size - Number of bytes to read
   * @returns {Promise<object>} Log file content
   */
  read(logName, size) {
    return API.get(`/api/logs/${logName}?log_size=${size}`)
  },

  /**
   * List all available application log files.
   * @returns {Promise<object>} List of log files
   */
  list() {
    return API.get('/api/logs')
  },

  // ── System logs ────────────────────────────────────────────────────────

  system: {
    /**
     * Read a specific system log file.
     * @param {string} logName - The log file name
     * @param {number} size - Number of bytes to read
     * @returns {Promise<object>} Log file content
     */
    read(logName, size) {
      return API.get(`/api/system/logs/${logName}?log_size=${size}`)
    },

    /**
     * List all available system log files.
     * @returns {Promise<object>} List of log files
     */
    list() {
      return API.get('/api/system/logs')
    },
  },

  // ── AI logs (request/response) ─────────────────────────────────────────

  ai: {
    /**
     * Get recent AI request/response log entries for the authenticated user.
     * @param {number} [limit=10] - Number of most recent logs to return (max 100)
     * @returns {Promise<object>} Object with username, recent_logs array, and count
     */
    me(limit = 10) {
      return API.get(`/api/logs/me?limit=${Math.min(limit, 100)}`)
    },

    /**
     * Get paginated list of AI request/response log entries for the authenticated user.
     * Results are sorted by timestamp descending (most recent first).
     * @param {object} opts
     * @param {string}  [opts.startDate]   - Inclusive start date YYYY-MM-DD
     * @param {string}  [opts.endDate]     - Inclusive end date YYYY-MM-DD
     * @param {string}  [opts.project]     - Filter by project name
     * @param {string}  [opts.model]       - Filter by model name
     * @param {string}  [opts.provider]    - Filter by provider name
     * @param {string}  [opts.direction]   - Filter by direction ('request' or 'response')
     * @param {string}  [opts.sessionId]   - Filter by session id
     * @param {number}  [opts.page=1]      - Page number (1-based)
     * @param {number}  [opts.pageSize=50] - Items per page (max 500)
     * @returns {Promise<object>} RawLogListResponse with paginated results
     */
    list({ startDate, endDate, project, model, provider, direction, sessionId, page = 1, pageSize = 50 } = {}) {
      const qs = _buildLogsQS({ startDate, endDate, project, model, provider, direction, sessionId, page, pageSize })
      return API.get(`/api/logs/list${qs}`)
    },

    /**
     * Get a specific log entry with full payload.
     * @param {string} logId - The synthetic log id (YYYY-MM-DD:line_index)
     * @returns {Promise<object>} Full RawLogRecord with complete payload
     */
    get(logId) {
      return API.get(`/api/logs/${encodeURIComponent(logId)}`)
    },

    // ── Admin endpoints ────────────────────────────────────────────────────

    admin: {
      /**
       * Get paginated list of AI request/response log entries across all users (admin only).
       * Results are sorted by timestamp descending (most recent first).
       * @param {object} opts
       * @param {string}  [opts.startDate]   - Inclusive start date YYYY-MM-DD
       * @param {string}  [opts.endDate]     - Inclusive end date YYYY-MM-DD
       * @param {string}  [opts.username]    - Filter by username
       * @param {string}  [opts.project]     - Filter by project name
       * @param {string}  [opts.model]       - Filter by model name
       * @param {string}  [opts.provider]    - Filter by provider name
       * @param {string}  [opts.direction]   - Filter by direction ('request' or 'response')
       * @param {string}  [opts.sessionId]   - Filter by session id
       * @param {number}  [opts.page=1]      - Page number (1-based)
       * @param {number}  [opts.pageSize=50] - Items per page (max 500)
       * @returns {Promise<object>} RawLogListResponse with paginated results
       */
      list({ startDate, endDate, username, project, model, provider, direction, sessionId, page = 1, pageSize = 50 } = {}) {
        const qs = _buildLogsQS({ startDate, endDate, username, project, model, provider, direction, sessionId, page, pageSize })
        return API.get(`/api/logs/admin/list${qs}`)
      },

      /**
       * Get any specific log entry with full payload (admin only).
       * @param {string} logId - The synthetic log id (YYYY-MM-DD:line_index)
       * @returns {Promise<object>} Full RawLogRecord with complete payload
       */
      get(logId) {
        return API.get(`/api/logs/admin/${encodeURIComponent(logId)}`)
      },

      /**
       * Delete a specific log entry (admin only).
       * @param {string} logId - The synthetic log id (YYYY-MM-DD:line_index)
       * @returns {Promise<object>} {ok: true, deleted: 1}
       */
      delete(logId) {
        return API.delete(`/api/logs/admin/${encodeURIComponent(logId)}`)
      },

      /**
       * Bulk delete log entries matching filters (admin only).
       * At least one filter must be provided to prevent accidental deletion of all logs.
       * @param {object} opts
       * @param {string}  [opts.startDate] - Start date filter YYYY-MM-DD
       * @param {string}  [opts.endDate]   - End date filter YYYY-MM-DD
       * @param {string}  [opts.username]  - Username filter
       * @param {string}  [opts.project]   - Project name filter
       * @param {string}  [opts.model]     - Model name filter
       * @param {string}  [opts.provider]  - Provider name filter
       * @returns {Promise<object>} {ok: true, deleted: <count>}
       */
      purge({ startDate, endDate, username, project, model, provider } = {}) {
        return API.post('/api/logs/admin/purge', {
          start_date: startDate || null,
          end_date: endDate || null,
          username: username || null,
          project: project || null,
          model: model || null,
          provider: provider || null,
        })
      }
    }
  }
})