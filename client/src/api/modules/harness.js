/**
 * Harness API module.
 *
 * Observability and audit surface of the native codx-junior harness:
 * the append-only audit journal (`.codx/harness/audit.jsonl`) and the
 * worker/watchdog health of the project.
 *
 * Read-only: the journal is written by the orchestration runtime, the chat
 * engine and the harness watchdog, never through HTTP.
 */

export const harnessModule = (API) => ({
  /**
   * Read the harness audit journal (newest first).
   *
   * Entries register every piece of harness work: `task_requested`, run
   * lifecycle (`run_created` ... `run_completed`), step dispatches and
   * finishes, notifications and worker supervision (`worker_stalled` /
   * `worker_restarted` / `worker_recovered`).
   *
   * @param {object} [params] - { limit, offset, event }
   */
  audit(params = {}) {
    const query = new URLSearchParams()
    if (params.limit) query.set('limit', String(params.limit))
    if (params.offset) query.set('offset', String(params.offset))
    if (params.event) query.set('event', params.event)
    const qs = query.toString()
    return API.get(`/api/harness/audit${qs ? `?${qs}` : ''}`)
  },

  /**
   * Harness health: worker presence, active runs and watchdog state.
   */
  status() {
    return API.get('/api/harness/status')
  }
})
