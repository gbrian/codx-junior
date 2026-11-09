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
  // Image chosen from the standalone library browser, handed to the
  // new-session dialog that opens right after it.
  pendingLibraryImage: null,
  activityBySession: {},
  costBySession: {},
  loadingActivity: false,
  controlLoading: false,
  realtimeReady: false
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

  pendingLibraryImage: state => state.pendingLibraryImage,
  isLoading: state => state.loading,
  isLoadingActivity: state => state.loadingActivity,
  isControlling: state => state.controlLoading,
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

  setPendingLibraryImage(state, image) {
    state.pendingLibraryImage = image || null
  },

  setActivity(state, { sessionId, activity }) {
    state.activityBySession = {
      ...state.activityBySession,
      [sessionId]: activity || []
    }
  },

  appendActivity(state, { sessionId, entry }) {
    if (!sessionId || !entry) return
    const current = state.activityBySession[sessionId] || []
    // Socket.IO can deliver the same entry the REST refresh already returned.
    const key = `${entry.ts || ''}|${entry.actor || ''}|${entry.action || ''}|${entry.url || ''}`
    if (current.some(item => `${item.ts || ''}|${item.actor || ''}|${item.action || ''}|${item.url || ''}` === key)) {
      return
    }
    const next = [...current, entry]
    state.activityBySession = {
      ...state.activityBySession,
      [sessionId]: next.slice(-300)
    }
  },

  setControlLoading(state, loading) {
    state.controlLoading = loading
  },

  setRealtimeReady(state, ready) {
    state.realtimeReady = ready
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
        const response = await API.computers.list()
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
          downloads_folder: sessionData.downloads_folder || null,
          kind: sessionData.kind || 'browser',
          os_version: sessionData.os_version || null,
          image: sessionData.image || null,
          // The image library sends the provider and, for saved computers, the
          // library item id. Without them the backend cannot apply the KasmVNC
          // live-view profile or restore the saved computer/profile.
          image_provider: sessionData.image_provider || null,
          library_item_id: sessionData.library_item_id || null,
          cpu_cores: sessionData.cpu_cores || null,
          ram_size: sessionData.ram_size || null,
          disk_size: sessionData.disk_size || null,
          shm_size: sessionData.shm_size || null,
          extra_env: sessionData.extra_env || null,
          desktop_width: sessionData.desktop_width || null,
          desktop_height: sessionData.desktop_height || null,
          vnc_host: sessionData.vnc_host || null,
          vnc_port: sessionData.vnc_port || null,
          vnc_password: sessionData.vnc_password || null,
          vnc_public_url: sessionData.vnc_public_url || null,
          ssh_host: sessionData.ssh_host || null,
          ssh_port: sessionData.ssh_port || null,
          ssh_user: sessionData.ssh_user || null,
          ssh_key_path: sessionData.ssh_key_path || null,
          ssh_password: sessionData.ssh_password || null
        }
        const session = await API.computers.create(payload)
        commit('addSession', session)
        commit('selectSession', session.id)
        commit('toggleNewSessionForm', false)
        notify('success', `${session.kind_label || "Computer"} session "${session.name}" created`)
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
        const payload = { name: sessionData.name }
        if (sessionData.description !== undefined) {
          payload.description = sessionData.description || null
        }
        // Advanced settings: only send fields the caller actually edited. An
        // empty size/"" image clears the override; extra_env must be an object.
        const advancedKeys = [
          'image', 'cpu_cores', 'ram_size', 'disk_size', 'shm_size',
          'extra_env', 'desktop_width', 'desktop_height'
        ]
        advancedKeys.forEach((key) => {
          if (Object.prototype.hasOwnProperty.call(sessionData, key)) {
            payload[key] = sessionData[key]
          }
        })
        const session = await API.computers.update(sessionData.id, payload)
        commit('updateSession', session)
        commit('clearEditingSession')
        notify('success', `${session.kind_label || "Computer"} session "${session.name}" updated`)
        return session
      } catch (error) {
        commit('setError', error.message || 'Failed to update session')
        notify('error', error.message || 'Failed to update session')
        throw error
      }
    },

    async stopSession({ commit }, sessionId) {
      const session = await API.computers.stop(sessionId)
      commit('updateSession', session)
      notify('success', 'Computer session stopped')
      return session
    },

    async restartSession({ commit }, sessionId) {
      const session = await API.computers.restart(sessionId)
      commit('updateSession', session)
      notify('success', 'Computer session restarted')
      return session
    },

    async deleteSession({ commit }, sessionId) {
      commit('clearError')
      try {
        await API.computers.delete(sessionId)
        commit('deleteSession', sessionId)
        notify('success', 'Computer session deleted')
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

    /** Open the new-session dialog with an image already chosen. */
    openNewSessionFromLibrary({ commit }, image) {
      commit('setPendingLibraryImage', image || null)
      commit('toggleNewSessionForm', true)
      commit('clearEditingSession')
    },

    /** The create dialog consumed the pending library image. */
    clearPendingLibraryImage({ commit }) {
      commit('setPendingLibraryImage', null)
    },

    startEditingSession({ commit }, sessionId) {
      commit('setEditingSession', sessionId)
    },

    stopEditingSession({ commit }) {
      commit('clearEditingSession')
    },

    async runSession({ commit }, sessionId) {
      try {
        const session = await API.computers.get(sessionId)
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

    async loadActivity({ commit }, { sessionId, limit = 100, since = null, actor = null } = {}) {
      if (!sessionId) return []
      commit('setLoadingActivity', true)
      try {
        const response = await API.computers.activity(sessionId, limit, { since, actor })
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
        const cost = await API.computers.cost(sessionId)
        commit('setCost', { sessionId, cost })
        return cost
      } catch (error) {
        console.error('[Browsers] Error loading cost:', error)
        return null
      }
    },

    /**
     * Subscribe once to the browser co-browsing events.
     *
     * Activity and control changes are pushed by the backend, so the live view
     * no longer polls every 7 seconds.  The REST refresh remains the fallback
     * when the socket is not connected.
     */
    initRealtime({ state, commit, dispatch }) {
      if (state.realtimeReady) return
      const socket = $storex.api?.socket
      if (!socket) return
      commit('setRealtimeReady', true)
      socket.on('codx-junior-browser-activity', (payload) => {
        const sessionId = payload?.session_id
        if (!sessionId || !payload?.entry) return
        commit('appendActivity', { sessionId, entry: payload.entry })
        const entry = payload.entry
        const session = state.sessions.find(item => item.id === sessionId)
        if (session) {
          if (entry.url) session.current_url = entry.url
          if (entry.title) session.current_title = entry.title
        }
      })
      socket.on('codx-junior-browser-control', (payload) => {
        if (payload?.session) {
          commit('updateSession', payload.session)
        } else if (payload?.session_id) {
          const session = state.sessions.find(item => item.id === payload.session_id)
          if (session) {
            session.controller = payload.controller
            session.handoff_reason = payload.handoff_reason
            session.user_active_until = payload.user_active_until
          }
        }
      })
    },

    async takeControl({ commit, dispatch }, sessionId) {
      if (!sessionId) return null
      commit('setControlLoading', true)
      try {
        const response = await API.computers.control(sessionId, 'take_control', {
          reason: 'User took control from the live view'
        })
        if (response?.session) commit('updateSession', response.session)
        notify('info', 'You have control. The AI is paused.')
        return response
      } catch (error) {
        notify('error', error.message || 'Could not take control')
        throw error
      } finally {
        commit('setControlLoading', false)
      }
    },

    async giveBackControl({ commit }, sessionId) {
      if (!sessionId) return null
      commit('setControlLoading', true)
      try {
        const response = await API.computers.control(sessionId, 'give_back')
        if (response?.session) commit('updateSession', response.session)
        notify('success', 'Control returned to the AI')
        return response
      } catch (error) {
        notify('error', error.message || 'Could not return control')
        throw error
      } finally {
        commit('setControlLoading', false)
      }
    },

    async requestHandoff({ commit }, { sessionId, reason }) {
      if (!sessionId) return null
      const response = await API.computers.control(sessionId, 'handoff', { reason })
      if (response?.session) commit('updateSession', response.session)
      return response
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
      const response = await API.computers.createChat(sessionId, chatId, createNew)
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
      const result = await API.computers.navigate(sessionId, url)
      await dispatch('loadActivity', { sessionId, limit: 50 })
      return result
    },

    async pageAction({ dispatch }, { sessionId, action, payload = {} }) {
      const result = await API.computers.action(sessionId, { action, ...payload })
      await dispatch('loadActivity', { sessionId, limit: 50 })
      return result
    },

    /**
     * Return a compact context of the current page for "Ask AI about this page".
     *
     * The selection is what the human highlighted in the live view; the active
     * element tells the AI which field the human was editing.
     */
    async pageContext({ state }, sessionId) {
      if (!sessionId) return null
      const session = state.sessions.find(item => item.id === sessionId)
      if (session && session.kind && session.kind !== 'browser') {
        // Desktops have no DOM/snapshot: send the OCR text plus the focused
        // window title so "Ask AI" has the same context a page would give.
        const response = await API.computers.screenshot(sessionId, { include_text: true, max_width: 1280 })
        return {
          url: null,
          title: session.current_title || session.name,
          selection: (response?.data?.text || '').slice(0, 4000),
          active: null,
          kind: session.kind
        }
      }
      const response = await API.computers.action(sessionId, { action: 'snapshot' })
      const snapshot = response?.data?.snapshot || {}
      return {
        url: snapshot.url,
        title: snapshot.title,
        selection: snapshot.selection || '',
        active: snapshot.active || null,
        kind: session?.kind || 'browser'
      }
    },

    async screenshot({ dispatch }, { sessionId, fullPage = true } = {}) {
      const result = await API.computers.screenshot(sessionId, { full_page: fullPage })
      await dispatch('loadActivity', { sessionId, limit: 50 })
      return result
    }
  }
)