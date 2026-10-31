/**
 * ============================================================================
 * Management dashboard API module — cross-project view for management.
 * ----------------------------------------------------------------------------
 * Thin client over `/api/management/*`. Every method is one request: the server
 * owns the aggregation (metrics, attention, forecast, team load, cost), so the
 * view never reduces a page into totals.
 *
 * BACKEND CONTRACT
 * ----------------
 *   GET   /api/management/overview?from&to&project_id&project_ids     → overview()
 *   POST  /api/management/tasks/query                                 → tasks()
 *   GET   /api/management/blockers?from&to&project_id&project_ids     → blockers()
 *   GET   /api/management/delivery?from&to&board_id&project_ids       → delivery()
 *   GET   /api/management/team-load?from&to&project_ids               → team()
 *   GET   /api/management/cost?from&to&project_id&model&project_ids   → cost()
 *   PUT   /api/management/tasks/{id}                                  → updateTask()
 *   POST  /api/management/assistant                                   → ask()
 *
 * PROJECT SCOPE
 * -------------
 * The dashboard can be scoped to a SET of projects (multi-select in the header).
 * The scope travels as:
 *   • `project_id`  — the legacy single-project parameter, still sent whenever
 *                     exactly ONE project is selected (an older server only
 *                     understands this one), and
 *   • `project_ids` — a comma separated list of project ids, sent for any
 *                     selection (including a single one).
 * The sentinel `-` means "no project selected": it matches nothing, so the
 * aggregates come back empty instead of silently falling back to every project.
 *
 * `PUT` is used instead of `PATCH` because the HTTP layer of `api.js`
 * (`_send`) implements GET / DEL / POST / PUT / DELETE only; the router exposes
 * both verbs on the same handler.
 *
 * No caching is requested: the dashboard reloads a section right after a write
 * (`patchTask`), and a short TTL would serve the pre-write numbers back.
 * Identical in-flight calls are still de-duplicated by `api.js`.
 * ============================================================================
 */

const BASE = '/api/management'

/** `project_ids` value meaning "there is no project to show". */
export const NO_PROJECT = '-'

/**
 * Build a query string, skipping empty values.
 * Arrays are sent comma separated (`project_ids=a,b`), which is what the
 * backend parses; an empty array is skipped entirely.
 * @param {Object} params - Plain object of query parameters.
 * @returns {string} `?a=1&b=2`, or `''` when nothing is set.
 */
function toQuery(params = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    if (Array.isArray(value)) {
      if (!value.length) return
      search.set(key, value.join(','))
      return
    }
    search.set(key, String(value))
  })
  const query = search.toString()
  return query ? `?${query}` : ''
}

/**
 * Severity of each attention reason, higher = worse.
 *
 * Kept in sync with `SEVERITY` in `api/codx/junior/management_manager.py`: the
 * server sorts the queue, this constant is exported for UI hints (dot colour,
 * badge tone) without hard-coding numbers in the templates.
 */
export const SEVERITY = {
  blocked: 4,
  overdue: 3,
  due_today: 2,
  unassigned_high: 1.5,
  stalled: 1
}

export const managementModule = (API) => ({
  /**
   * Everything the Pulse section draws, in one round trip.
   * @param {{from?: string, to?: string, project_id?: string,
   *          project_ids?: string|string[]}} query ISO range (default: last 7 days).
   */
  overview({ from, to, project_id, project_ids } = {}) {
    return API.get(`${BASE}/overview${toQuery({ from, to, project_id, project_ids })}`)
  },

  /**
   * Paginated, filtered task list across every project (the Work section).
   * @param {Object} body `{ from, to, project_id, project_ids, board_id,
   *        statuses, priorities, assignees, search, sort, page, page_size }`
   */
  tasks(body = {}) {
    return API.post(`${BASE}/tasks/query`, body)
  },

  /**
   * Attention queue (the Blockers section).
   * @param {{from?: string, to?: string, project_id?: string,
   *          project_ids?: string|string[]}} query
   */
  blockers({ from, to, project_id, project_ids } = {}) {
    return API.get(`${BASE}/blockers${toQuery({ from, to, project_id, project_ids })}`)
  },

  /**
   * Forecast per board plus the burndown of the selected one.
   * @param {{from?: string, to?: string, board_id?: string,
   *          project_ids?: string|string[]}} query
   */
  delivery({ from, to, board_id, project_ids } = {}) {
    return API.get(`${BASE}/delivery${toQuery({ from, to, board_id, project_ids })}`)
  },

  /**
   * Capacity and workload per assignee (humans and AI agents).
   * @param {{from?: string, to?: string, project_ids?: string|string[]}} query
   */
  team({ from, to, project_ids } = {}) {
    return API.get(`${BASE}/team-load${toQuery({ from, to, project_ids })}`)
  },

  /**
   * AI consumption and budget (the Cost & AI section).
   * @param {{from?: string, to?: string, project_id?: string, model?: string,
   *          project_ids?: string|string[]}} query
   */
  cost({ from, to, project_id, model, project_ids } = {}) {
    return API.get(`${BASE}/cost${toQuery({ from, to, project_id, model, project_ids })}`)
  },

  /**
   * Update one task in the project that owns it and return the fresh row.
   *
   * `blocked: false` unblocks (the server maps it to a status change, since a
   * chat has no blocked field).
   *
   * @param {string} id Task id.
   * @param {{status?: string, priority?: string, due_date?: string|null,
   *          progress?: number, assignees?: string[], blocked?: boolean}} patch
   * @returns {Promise<Object>} The updated task.
   */
  async updateTask(id, patch = {}) {
    const response = await API.put(`${BASE}/tasks/${encodeURIComponent(id)}`, patch)
    return response?.task || response
  },

  /**
   * Ask about the current window. The answer is computed server-side from the
   * same numbers the screen renders, and `sources` names the sections used.
   * @param {{question: string, from?: string, to?: string,
   *          project_id?: string, project_ids?: string|string[]}} body
   */
  ask({ question, from, to, project_id, project_ids } = {}) {
    return API.post(`${BASE}/assistant`, { question, from, to, project_id, project_ids })
  },

  /**
   * Kept for API compatibility with the view (`resetMock`).
   *
   * There is no client-side dataset to regenerate now that the dashboard reads
   * the backend: the caller reloads the section instead.
   */
  reset() {}
})

export default managementModule
