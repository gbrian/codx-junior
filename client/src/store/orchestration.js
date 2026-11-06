import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

/**
 * Orchestration runs (durable long-running tasks).
 *
 * The chat is the anchor: `chat.run_id` is the long-running process id. This
 * store keeps the run detail keyed by that id, so every view of the same chat
 * (desktop panels, mobile, board) sees the same live status.
 *
 * Live updates:
 *   - `codx-junior-orchestration` socket events carry `run_id`, `status` and
 *     `progress`; they patch the cached run and debounce a detail refresh.
 *   - the REST detail remains the source of truth.
 */

export const namespaced = true

const inflightLoads = {}
const refreshTimers = {}

// Detail fields we keep on a socket-only patch. The full plan comes from the
// REST refresh; this makes the status bar correct even before it lands.
const EVENT_PATCH_FIELDS = ['status', 'progress', 'main_chat_id', 'name', 'updated_at']

export const state = () => ({
  runs: {},
  loading: {},
  errors: {}
})

export const getters = getterTree(state, {
  /** Run detail by run id (null when not loaded yet). */
  runById: state => (runId) => (runId ? state.runs[runId] || null : null),
  /** Run detail of the chat's long-running process (`chat.run_id`). */
  runForChat: state => (chat) => {
    const runId = chat?.run_id
    return runId ? state.runs[runId] || null : null
  },
  runLoading: state => (runId) => !!state.loading[runId],
  runError: state => (runId) => state.errors[runId] || null
})

export const mutations = mutationTree(state, {
  setRun(state, run) {
    if (!run?.run_id) return
    const current = state.runs[run.run_id]
    if (current) {
      // Keep the object identity: ChatView and the status bar derive their
      // computed values from it and only re-render when a field changed.
      Object.assign(current, run)
      return
    }
    state.runs = { ...state.runs, [run.run_id]: run }
  },

  patchRun(state, { runId, patch }) {
    const run = state.runs[runId]
    if (!run || !patch) return
    Object.keys(patch).forEach(key => {
      if (run[key] !== patch[key]) run[key] = patch[key]
    })
  },

  setRunLoading(state, { runId, loading }) {
    if (!runId) return
    if (!!state.loading[runId] === !!loading) return
    state.loading = { ...state.loading, [runId]: !!loading }
  },

  setRunError(state, { runId, error }) {
    if (!runId) return
    if (state.errors[runId] === error) return
    state.errors = { ...state.errors, [runId]: error }
  },

  clearRun(state, runId) {
    if (!runId || !state.runs[runId]) return
    const runs = { ...state.runs }
    delete runs[runId]
    state.runs = runs
  }
})

/** API client of the project that owns *chat*. */
function apiForChat(chat) {
  const projectId = chat?.project_id || chat?.owner_project_id
  const project = (projectId && $storex.projects.allProjectsById?.[projectId]) ||
    $storex.projects.activeProject
  return project?.$api || $storex.api
}

function errorMessage(error) {
  return error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    String(error)
}

/** Debounced detail refresh after a burst of socket events. */
function scheduleRefresh(dispatch, runId) {
  clearTimeout(refreshTimers[runId])
  refreshTimers[runId] = setTimeout(() => {
    delete refreshTimers[runId]
    dispatch('loadRun', { runId, force: true }).catch(() => {})
  }, 300)
}

export const actions = actionTree(
  { state, getters, mutations },
  {
    /**
     * Load the run detail.
     *
     * @param {Object} payload
     * @param {string} payload.runId - Long-running process id (`chat.run_id`).
     * @param {Object} [payload.chat] - Chat used to resolve the owning project.
     * @param {boolean} [payload.force] - Refresh even when the detail is cached.
     */
    async loadRun({ state, commit }, { runId, chat, force = false } = {}) {
      if (!runId) return null
      if (!force && state.runs[runId]?.steps) return state.runs[runId]
      if (inflightLoads[runId]) return inflightLoads[runId]

      const api = apiForChat(chat)
      if (!api?.orchestration) return null

      commit('setRunLoading', { runId, loading: true })
      commit('setRunError', { runId, error: null })
      const request = (async () => {
        try {
          const run = await api.orchestration.get(runId)
          commit('setRun', run)
          return state.runs[runId] || run
        } catch (error) {
          commit('setRunError', { runId, error: errorMessage(error) })
          return state.runs[runId] || null
        } finally {
          commit('setRunLoading', { runId, loading: false })
          delete inflightLoads[runId]
        }
      })()

      inflightLoads[runId] = request
      return request
    },

    /**
     * Create (or attach) a run for a chat and register its id on the chat.
     *
     * The backend appends the orchestrator profile and persists
     * `chat.run_id`/`chat.run_status`; the caller only needs to reload the chat.
     */
    async startChat({ commit }, { chat, name, objective, budget, profiles } = {}) {
      if (!chat?.id) throw new Error('Cannot start a run without a persisted chat')
      const api = apiForChat(chat)
      if (!api?.orchestration) throw new Error('Orchestration API is not available')

      const run = await api.orchestration.create({
        main_chat_id: chat.id,
        name: name || chat.name || '',
        objective: objective || '',
        budget_cxjcoins: Number(budget || chat.estimation_cost || 0),
        max_parallel: 2,
        profiles: profiles || ['orchestrator']
      })
      commit('setRun', run)
      return run
    },

    /** Start / resume / reopen the run. */
    async startRun({ commit }, { runId, chat } = {}) {
      if (!runId) return null
      const api = apiForChat(chat)
      const run = await api.orchestration.start(runId)
      commit('setRun', run)
      return run
    },

    /** Pause the run (in-flight turn finishes, then the worker stops). */
    async pauseRun({ commit }, { runId, chat, reason = '' } = {}) {
      if (!runId) return null
      const api = apiForChat(chat)
      const run = await api.orchestration.pause(runId, reason)
      commit('setRun', run)
      return run
    },

    /** Resume a paused/stalled run. */
    async resumeRun({ commit }, { runId, chat } = {}) {
      if (!runId) return null
      const api = apiForChat(chat)
      const run = await api.orchestration.resume(runId)
      commit('setRun', run)
      return run
    },

    /** Stop the run and cancel its in-flight turns. */
    async stopRun({ commit }, { runId, chat, reason = '' } = {}) {
      if (!runId) return null
      const api = apiForChat(chat)
      const run = await api.orchestration.stop(runId, reason)
      commit('setRun', run)
      return run
    },

    /**
     * Apply a `codx-junior-orchestration` socket event.
     *
     * Only runs that are already tracked are refreshed: broadcasts reach every
     * project and every browser session, and a run nobody displays does not
     * need a network round trip.
     */
    onSocketEvent({ state, commit, dispatch }, data) {
      const runId = data?.run_id
      if (!runId) return
      const current = state.runs[runId]
      if (!current) return

      const patch = {}
      EVENT_PATCH_FIELDS.forEach(field => {
        if (data[field] !== undefined) patch[field] = data[field]
      })
      commit('patchRun', { runId, patch })
      scheduleRefresh(dispatch, runId)
    },

    /** Forget a run (e.g. deleted chat). */
    clearRun({ commit }, runId) {
      clearTimeout(refreshTimers[runId])
      delete refreshTimers[runId]
      commit('clearRun', runId)
    }
  }
)
