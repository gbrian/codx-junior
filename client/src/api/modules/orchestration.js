/**
 * Orchestration API module.
 *
 * Durable, board-native runs (see api/docs/orchestration.md). The API process
 * never executes a turn: `create`/`start`/`pause`/`stop` write intent and
 * return the persisted run; the background worker advances it.
 *
 * The run detail (`get`) is the source of truth for the UI. Live status arrives
 * on the `codx-junior-orchestration` socket event.
 */

const runUrl = (runId) => `/api/orchestration/${encodeURIComponent(runId)}`

export const orchestrationModule = (API) => ({
  /**
   * List the project's runs (newest first).
   * @param {string} [status] - Optional run status filter.
   */
  list(status) {
    const qs = status ? `?status=${encodeURIComponent(status)}` : ''
    return API.get(`/api/orchestration${qs}`)
  },

  /**
   * Create a run.
   *
   * Pass `main_chat_id` to promote an existing root task to the run dashboard.
   * Without it the backend creates a new main task on the run board.
   */
  create(payload) {
    return API.post('/api/orchestration', payload || {})
  },

  /** Full run detail: plan, results, budget, cards, worker presence. */
  get(runId) {
    return API.get(runUrl(runId))
  },

  /** Add one step to the plan. */
  addStep(runId, step) {
    return API.post(`${runUrl(runId)}/steps`, step || {})
  },

  /** Mark a run completed and publish its delivery report. */
  finish(runId, summary) {
    return API.post(`${runUrl(runId)}/finish`, { summary })
  },

  /**
   * Start / resume / reopen a run.
   *
   * This is the UI's "Start" action: active runs are returned unchanged, paused
   * and stalled runs resume, stopped/failed runs are reopened.
   */
  start(runId) {
    return API.post(`${runUrl(runId)}/start`, {})
  },

  /** Pause a run (the in-flight turn finishes, then the worker stops). */
  pause(runId, reason = '') {
    return API.post(`${runUrl(runId)}/pause`, { reason })
  },

  /** Resume a paused run (kept for callers that want explicit resume). */
  resume(runId) {
    return API.post(`${runUrl(runId)}/resume`, {})
  },

  /** Stop a run and cancel its in-flight turns. */
  stop(runId, reason = '') {
    return API.post(`${runUrl(runId)}/stop`, { reason })
  },

  /** Ask the background worker to advance the run now (admin). */
  wake(runId) {
    return API.post(`${runUrl(runId)}/tick`, {})
  }
})
