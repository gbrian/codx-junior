/**
 * API logs (performance) module
 * Handles querying the per-request API metrics recorded by the backend.
 *
 * Backend: api/codx/junior/api/api_logs.py (router prefix /api/api-logs).
 * Each recorded event is one HTTP call: method, route template, status,
 * duration, user and project. The aggregation endpoints below are what the
 * ApiMonitoring view reads — no client-side sampling is involved.
 *
 * User-scoped routes return metrics filtered to the authenticated user;
 * everything under `admin` requires the `admin` role and covers every user.
 */

/**
 * Build a query string from API-log filter params.
 * Omits undefined/null/empty values and maps camelCase to snake_case.
 */
function _buildApiLogsQS(params = {}) {
  const keyMap = {
    startDate: 'start_date',
    endDate: 'end_date',
    statusCode: 'status_code',
    minDurationSeconds: 'min_duration_seconds',
    errorsOnly: 'errors_only',
    projectName: 'project_name',
    projectId: 'project_id',
    grouping: 'grouping',
    limit: 'limit',
    username: 'username',
    path: 'path',
    method: 'method',
  }
  const parts = Object.entries(params || {})
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => `${keyMap[key] || key}=${encodeURIComponent(value)}`)
  return parts.length ? `?${parts.join('&')}` : ''
}

/**
 * API logs module factory.
 * @param {object} API The codx-junior API instance (see src/api/api.js).
 */
export function apiLogsModule(API) {
  const get = (path) => API.get(path)

  /**
   * Builds one endpoint group for a given route prefix.
   * @param {string} prefix e.g. '/api/api-logs' or '/api/api-logs/admin'
   */
  const scope = (prefix) => ({
    /**
     * ISO dates (YYYY-MM-DD) with recorded calls.
     * @returns {Promise<string[]>}
     */
    dates() {
      return get(`${prefix}/dates`)
    },

    /**
     * Aggregated metrics: calls, errors, error_rate, total/avg/min/max/p95
     * durations.
     * @param {object} [filters]
     * @returns {Promise<object>}
     */
    summary(filters = {}) {
      return get(`${prefix}/summary${_buildApiLogsQS(filters)}`)
    },

    /**
     * Per-period buckets. `grouping` is a bucket SIZE: 1s | 5s | 10s | 15s |
     * 30s | minute | 5m | 15m | hour | day (any <n>s/<n>m/<n>h/<n>d works).
     * @param {object} [filters] May include `grouping`.
     * @returns {Promise<Array<object>>}
     */
    daily(filters = {}) {
      return get(`${prefix}/daily${_buildApiLogsQS(filters)}`)
    },

    /**
     * Metrics grouped by endpoint (route template).
     * @param {object} [filters]
     * @returns {Promise<object>} map path → metrics
     */
    byEndpoint(filters = {}) {
      return get(`${prefix}/by-endpoint${_buildApiLogsQS(filters)}`)
    },

    /**
     * Metrics grouped by HTTP status code.
     * @param {object} [filters]
     * @returns {Promise<object>} map status → metrics
     */
    byStatus(filters = {}) {
      return get(`${prefix}/by-status${_buildApiLogsQS(filters)}`)
    },

    /**
     * Slowest calls, ordered by duration descending.
     * @param {object} [filters] May include `limit`.
     * @returns {Promise<Array<object>>}
     */
    slowest(filters = {}) {
      return get(`${prefix}/slowest${_buildApiLogsQS({ limit: 20, ...filters })}`)
    },

    /**
     * Failed calls (error or status >= 500), newest first.
     * @param {object} [filters] May include `limit`.
     * @returns {Promise<Array<object>>}
     */
    errors(filters = {}) {
      return get(`${prefix}/errors${_buildApiLogsQS({ limit: 100, ...filters })}`)
    }
  })

  return {
    // ── User-scoped (own metrics) ─────────────────────────────────────────
    ...scope('/api/api-logs'),

    // ── Admin (all users) ─────────────────────────────────────────────────
    admin: {
      ...scope('/api/api-logs/admin'),

      /**
       * Metrics grouped by username.
       * @param {object} [filters]
       * @returns {Promise<object>}
       */
      byUser(filters = {}) {
        return get(`/api/api-logs/admin/by-user${_buildApiLogsQS(filters)}`)
      },

      /**
       * Metrics grouped by project name.
       * @param {object} [filters]
       * @returns {Promise<object>}
       */
      byProject(filters = {}) {
        return get(`/api/api-logs/admin/by-project${_buildApiLogsQS(filters)}`)
      }
    }
  }
}

export default apiLogsModule