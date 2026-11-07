import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import { API } from '../api/api'

export const namespaced = true

export const state = () => ({
  sessions: [],
  selectedSessionId: null,
  loading: false,
  error: null,
  editingSessionId: null,
  showNewSessionForm: false,
  activityBySession: {},
  costBySession: {},
  loadingActivity: false
})

export const getters = getterTree(state, {
  allSessions: state => state.sessions,

  selectedSession: state => {
    if (!state.selectedSessionId) return null
    return state.sessions.find(s => s.id === state.selectedSessionId)
  },

  sessionById: (state) => (id) => {
    return state.sessions.find(s => s.id === id)
  },

  activityFor: (state) => (sessionId) => {
    return state.activityBySession[sessionId] || []
  },

  costFor: (state) => (sessionId) => {
    return state.costBySession[sessionId] || null
  },

  isLoading: state => state.loading,
  isLoadingActivity: state => state.loadingActivity,
  hasError: state => !!state.error,
  errorMessage: state => state.error
})

export const mutations = mutationTree(state, {
  setSessions(state, sessions) {
    state.sessions = sessions
  },

  addSession(state, session) {
    state.sessions.push(session)
  },

  updateSession(state, session) {
    const index = state.sessions.findIndex(s => s.id === session.id)
    if (index !== -1) {
      state.sessions[index] = session
    }
  },

  deleteSession(state, sessionId) {
    state.sessions = state.sessions.filter(s => s.id !== sessionId)
    if (state.selectedSessionId === sessionId) {
      state.selectedSessionId = null
    }
    delete state.activityBySession[sessionId]
    delete state.costBySession[sessionId]
  },

  selectSession(state, sessionId) {
    state.selectedSessionId = sessionId
  },

  clearSelection(state) {
    state.selectedSessionId = null
  },

  setLoading(state, loading) {
    state.loading = loading
  },

  setLoadingActivity(state, loading) {
    state.loadingActivity = loading
  },

  setError(state, error) {
    state.error = error
  },

  clearError(state) {
    state.error = null
  },

  setEditingSession(state, sessionId) {
    state.editingSessionId = sessionId
  },

  clearEditingSession(state) {
    state.editingSessionId = null
  },

  toggleNewSessionForm(state, show) {
    state.showNewSessionForm = show !== undefined ? show : !state.showNewSessionForm
  },

  setActivity(state, { sessionId, activity }) {
    state.activityBySession = {
      ...state.activityBySession,
      [sessionId]: activity || []
    }
  },

  setCost(state, { sessionId, cost }) {
    state.costBySession = {
      ...state.costBySession,
      [sessionId]: cost || null
    }
  }
})

function notify(type, text) {
  try {
    $storex.ui.addNotification({ text, type })
  } catch (e) {
    // Notifications are best-effort (e.g. when the store boots headless)
  }
}

export const actions = actionTree(
  { state, getters, mutations },
  {
    async loadSessions({ commit }) {
      commit('setLoading', true)
      commit('clearError')
      try {
        const response = await API.browsers.list()
        commit('setSessions', response?.sessions || [])
      } catch (error) {
        commit('setError', error.message || 'Failed to load sessions')
        console.error('[Browsers] Error loading sessions:', error)
      } finally {
        commit('setLoading', false)
      }
    },

    /**
     * Create a browser session.
     *
     * Besides the session identity, the payload carries the **project folder
     * mapping**, decided by the new-session dialog because the folders become
     * bind mounts and cannot change while the container lives:
     *
     *  - `share_project`    mount the whole project at /home/<project_name>
     *  - `share_folders`    project-relative folders to mount instead
     *  - `readonly`         mount those folders read-only
     *  - `downloads_folder` project folder receiving the browser downloads
     */
    async createSession({ commit }, sessionData) {
      commit('clearError')
      try {
        const payload = {
          name: sessionData.name,
          description: sessionData.description || null,
          chat_id: sessionData.chat_id || null,
          initial_url: sessionData.initial_url || sessionData.url || null,
          share_project: sessionData.share_project ?? null,
          share_folders: sessionData.share_folders || null,
          readonly: sessionData.readonly ?? null,
          downloads_folder: sessionData.downloads_folder || null
        }
        const session = await API.browsers.create(payload)
        commit('addSession', session)
        commit('selectSession', session.id)
        commit('toggleNewSessionForm', false)
        notify('success', `Browser session "${session.name}" created`)
        return session
      } catch (error) {
        commit('setError', error.message || 'Failed to create session')
        notify('error', error.message || 'Failed to create session')
        throw error
      }
    },

    async updateSession({ commit }, sessionData) {
      commit('clearError')
      try {
        const session = await API.browsers.update(sessionData.id, {
          name: sessionData.name
        })
        commit('updateSession', session)
        commit('clearEditingSession')
        notify('success', `Browser session "${session.name}" updated`)
        return session
      } catch (error) {
        commit('setError', error.message || 'Failed to update session')
        notify('error', error.message || 'Failed to update session')
        throw error
      }
    },

    async stopSession({ commit }, sessionId) {
      const session = await API.browsers.stop(sessionId)
      commit('updateSession', session)
      notify('success', 'Browser session stopped')
      return session
    },

    async restartSession({ commit }, sessionId) {
      const session = await API.browsers.restart(sessionId)
      commit('updateSession', session)
      notify('success', 'Browser session restarted')
      return session
    },

    async deleteSession({ commit }, sessionId) {
      commit('clearError')
      try {
        await API.browsers.delete(sessionId)
        commit('deleteSession', sessionId)
        notify('success', 'Browser session deleted')
      } catch (error) {
        commit('setError', error.message || 'Failed to delete session')
        notify('error', error.message || 'Failed to delete session')
        throw error
      }
    },

    selectSession({ commit }, sessionId) {
      commit('selectSession', sessionId)
    },

    clearSelection({ commit }) {
      commit('clearSelection')
    },

    toggleNewSessionForm({ commit }, show) {
      commit('toggleNewSessionForm', show)
      if (show) {
        commit('clearEditingSession')
      }
    },

    startEditingSession({ commit }, sessionId) {
      commit('setEditingSession', sessionId)
    },

    stopEditingSession({ commit }) {
      commit('clearEditingSession')
    },

    async runSession({ commit }, sessionId) {
      try {
        const session = await API.browsers.get(sessionId)
        if (!session) throw new Error('Session not found')
        if (!session.vnc_path && session.vnc_url) {
          // Best-effort same-origin path for older persisted sessions.
          try {
            session.vnc_path = new URL(session.vnc_url, window.location.origin).pathname
          } catch (e) {
            session.vnc_path = session.vnc_url
          }
        }

        // Central navigation knows whether we are in desktop mode (dockview
        // panel) or single/mobile mode (route) and does the right thing.
        $storex.$navigation?.browsers?.open(sessionId, session.name)
        return session
      } catch (error) {
        commit('setError', error.message || 'Failed to run session')
        notify('error', error.message || 'Failed to run session')
        throw error
      }
    },

    async loadActivity({ commit }, { sessionId, limit = 100 } = {}) {
      if (!sessionId) return []
      commit('setLoadingActivity', true)
      try {
        const response = await API.browsers.activity(sessionId, limit)
        commit('setActivity', { sessionId, activity: response?.activity || [] })
        return response?.activity || []
      } catch (error) {
        console.error('[Browsers] Error loading activity:', error)
        return []
      } finally {
        commit('setLoadingActivity', false)
      }
    },

    async loadCost({ commit }, sessionId) {
      if (!sessionId) return null
      try {
        const cost = await API.browsers.cost(sessionId)
        commit('setCost', { sessionId, cost })
        return cost
      } catch (error) {
        console.error('[Browsers] Error loading cost:', error)
        return null
      }
    },

    /**
     * Get (or create) the chat linked to a browser session.
     *
     * The endpoint reuses the session's chat when it already has one, otherwise
     * creates it and activates the `browser` profile so the AI can drive the
     * shared page from the browser-sessions view.
     */
    async ensureChat({ commit }, { sessionId, chatId = null, createNew = false } = {}) {
      if (!sessionId) return null
      const response = await API.browsers.createChat(sessionId, chatId, createNew)
      if (response?.session) {
        commit('updateSession', response.session)
      }
      const chat = response?.chat || null
      if (chat?.id) {
        await $storex.chats.loadChat(chat)
      }
      return chat
    },

    async navigate({ dispatch }, { sessionId, url }) {
      const result = await API.browsers.navigate(sessionId, url)
      await dispatch('loadActivity', { sessionId, limit: 50 })
      return result
    },

    async pageAction({ dispatch }, { sessionId, action, payload = {} }) {
      const result = await API.browsers.action(sessionId, { action, ...payload })
      await dispatch('loadActivity', { sessionId, limit: 50 })
      return result
    },

    async screenshot({ dispatch }, { sessionId, fullPage = true } = {}) {
      const result = await API.browsers.screenshot(sessionId, fullPage)
      await dispatch('loadActivity', { sessionId, limit: 50 })
      return result
    }
  }
)