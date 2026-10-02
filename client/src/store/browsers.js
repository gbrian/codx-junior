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
  showNewSessionForm: false
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

  isLoading: state => state.loading,
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
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async loadSessions({ commit }) {
      commit('setLoading', true)
      commit('clearError')
      try {
        const { sessions } = await API.browsers.list()
        commit('setSessions', sessions || [])
      } catch (error) {
        commit('setError', error.message || 'Failed to load sessions')
        console.error('[Browsers] Error loading sessions:', error)
      } finally {
        commit('setLoading', false)
      }
    },

    async createSession({ commit }, sessionData) {
      commit('clearError')
      try {
        const session = await API.browsers.create(sessionData)
        commit('addSession', session)
        commit('toggleNewSessionForm', false)
        $storex.ui.addNotification({
          text: `Browser session "${session.name}" created`,
          type: 'success'
        })
        return session
      } catch (error) {
        commit('setError', error.message || 'Failed to create session')
        $storex.ui.addNotification({
          text: error.message || 'Failed to create session',
          type: 'error'
        })
        throw error
      }
    },

    async updateSession({ commit }, sessionData) {
      commit('clearError')
      try {
        const session = await API.browsers.update(sessionData.id, sessionData)
        commit('updateSession', session)
        commit('clearEditingSession')
        $storex.ui.addNotification({
          text: `Browser session "${session.name}" updated`,
          type: 'success'
        })
        return session
      } catch (error) {
        commit('setError', error.message || 'Failed to update session')
        $storex.ui.addNotification({
          text: error.message || 'Failed to update session',
          type: 'error'
        })
        throw error
      }
    },

    async deleteSession({ commit }, sessionId) {
      commit('clearError')
      try {
        await API.browsers.delete(sessionId)
        commit('deleteSession', sessionId)
        $storex.ui.addNotification({
          text: 'Browser session deleted',
          type: 'success'
        })
      } catch (error) {
        commit('setError', error.message || 'Failed to delete session')
        $storex.ui.addNotification({
          text: error.message || 'Failed to delete session',
          type: 'error'
        })
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

        // Open session in AppWindow
        $storex.ui.showApp({
          tabId: `browser-${sessionId}`,
          name: session.name,
          component: 'browser-viewer',
          params: {
            sessionId: sessionId,
            session: session
          }
        })

        return session
      } catch (error) {
        commit('setError', error.message || 'Failed to run session')
        $storex.ui.addNotification({
          text: error.message || 'Failed to run session',
          type: 'error'
        })
        throw error
      }
    }
  }
)