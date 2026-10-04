import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

export const state = () => ({
  // Active meet sessions: { meetId: { meetId, name, initiator, participants, startedAt, duration, status, chatId, localStream, remoteStreams } }
  activeMeets: {},
  
  // Incoming meet invitations: { meetId: { meetId, from, fromName, fromAvatar, timestamp } }
  incomingInvitations: {},
  
  // Meet history
  meetHistory: [],
  
  // Current active meet ID (the meet this client is actively in)
  currentMeetId: null,
  meetStatus: 'idle', // 'idle' | 'ringing' | 'connecting' | 'active' | 'ending'
  
  // Available audio/video devices
  availableDevices: {
    microphones: [],
    speakers: [],
    cameras: []
  },
  
  // Mute states
  isMuted: false,
  isAudioTestActive: false,
  
  // Mock mode for UI development without real WebRTC/socket
  _mockMode: true,
  _mockDurationTimers: {},
  _mockStreams: {}
})

export const getters = getterTree(state, {
  allActiveMeets: (state) => Object.values(state.activeMeets),
  currentMeet: (state) => state.currentMeetId ? state.activeMeets[state.currentMeetId] : null,
  allIncomingInvitations: (state) => Object.values(state.incomingInvitations),
  isInMeet: (state) => state.currentMeetId !== null && state.meetStatus === 'active',
  recentMeetHistory: (state) => state.meetHistory.slice(-10),
  activeMeetCount: (_, getters) => getters.allActiveMeets.length,
  incomingInvitationCount: (_, getters) => getters.allIncomingInvitations.length,
  meetForId: (state) => (meetId) => state.activeMeets[meetId] || null,
  deviceCount: (state) => {
    return {
      microphones: state.availableDevices.microphones.length,
      speakers: state.availableDevices.speakers.length,
      cameras: state.availableDevices.cameras.length
    }
  }
})

export const mutations = mutationTree(state, {
  addActiveMeet(state, meet) {
    state.activeMeets = {
      ...state.activeMeets,
      [meet.meetId]: {
        meetId: meet.meetId,
        name: meet.name || `Meet ${meet.meetId.slice(0, 8)}`,
        initiator: meet.initiator,
        participants: meet.participants || [meet.initiator],
        startedAt: meet.startedAt || new Date().getTime(),
        duration: 0,
        status: meet.status || 'connecting',
        chatId: meet.chatId || null,
        isMuted: false,
        localStream: null,
        remoteStreams: {}
      }
    }
  },

  updateMeetStatus(state, { meetId, status }) {
    if (state.activeMeets[meetId]) {
      state.activeMeets[meetId].status = status
    }
  },

  updateMeetDuration(state, { meetId, duration }) {
    if (state.activeMeets[meetId]) {
      state.activeMeets[meetId].duration = duration
    }
  },

  setMeetMuted(state, { meetId, muted }) {
    if (state.activeMeets[meetId]) {
      state.activeMeets[meetId].isMuted = muted
    }
    state.isMuted = muted
  },

  addParticipantToMeet(state, { meetId, userId }) {
    if (state.activeMeets[meetId] && !state.activeMeets[meetId].participants.includes(userId)) {
      state.activeMeets[meetId].participants = [...state.activeMeets[meetId].participants, userId]
    }
  },

  removeParticipantFromMeet(state, { meetId, userId }) {
    if (state.activeMeets[meetId]) {
      state.activeMeets[meetId].participants = state.activeMeets[meetId].participants.filter(p => p !== userId)
    }
  },

  endActiveMeet(state, meetId) {
    const meet = state.activeMeets[meetId]
    if (meet) {
      // Cleanup streams
      if (meet.localStream) {
        meet.localStream.getTracks().forEach(track => track.stop())
      }
      Object.values(meet.remoteStreams).forEach(stream => {
        stream.getTracks().forEach(track => track.stop())
      })

      state.meetHistory = [...state.meetHistory, { ...meet, endedAt: new Date().getTime(), status: 'ended' }]
      const updated = { ...state.activeMeets }
      delete updated[meetId]
      state.activeMeets = updated
      if (state.currentMeetId === meetId) {
        state.currentMeetId = null
        state.meetStatus = 'idle'
        state.isMuted = false
      }
    }
  },

  addIncomingInvitation(state, invitation) {
    state.incomingInvitations = {
      ...state.incomingInvitations,
      [invitation.meetId]: {
        meetId: invitation.meetId,
        from: invitation.from,
        fromName: invitation.fromName,
        fromAvatar: invitation.fromAvatar,
        timestamp: new Date().getTime(),
        status: 'pending'
      }
    }
  },

  removeIncomingInvitation(state, meetId) {
    const updated = { ...state.incomingInvitations }
    delete updated[meetId]
    state.incomingInvitations = updated
  },

  setCurrentMeet(state, meetId) {
    state.currentMeetId = meetId
  },

  setMeetStatus(state, status) {
    state.meetStatus = status
  },

  setIsMuted(state, muted) {
    state.isMuted = muted
  },

  setAvailableDevices(state, devices) {
    state.availableDevices = devices
  },

  setAudioTestActive(state, active) {
    state.isAudioTestActive = active
  },

  setMockMode(state, enabled) {
    state._mockMode = enabled
  },

  setMockTimer(state, { meetId, timer }) {
    if (timer === null) {
      const updated = { ...state._mockDurationTimers }
      delete updated[meetId]
      state._mockDurationTimers = updated
    } else {
      state._mockDurationTimers = { ...state._mockDurationTimers, [meetId]: timer }
    }
  },

  setMockStream(state, { meetId, stream }) {
    if (stream === null) {
      const updated = { ...state._mockStreams }
      delete updated[meetId]
      state._mockStreams = updated
    } else {
      state._mockStreams = { ...state._mockStreams, [meetId]: stream }
    }
  },

  clearAllMeets(state) {
    Object.values(state._mockDurationTimers).forEach(t => clearInterval(t))
    state.activeMeets = {}
    state.incomingInvitations = {}
    state.currentMeetId = null
    state.meetStatus = 'idle'
    state.isMuted = false
    state._mockDurationTimers = {}
    state._mockStreams = {}
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    /**
     * Initialize meets module - enumerate devices
     */
    async init() {
      await $storex.meets.enumerateDevices()
    },

    /**
     * Enumerate available audio/video devices
     */
    async enumerateDevices() {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
          console.warn('[meets] enumerateDevices not supported')
          return { success: false, error: 'Not supported' }
        }

        const devices = await navigator.mediaDevices.enumerateDevices()
        const microphones = []
        const speakers = []
        const cameras = []

        devices.forEach(device => {
          const label = device.label || `${device.kind} ${device.deviceId}`
          switch (device.kind) {
            case 'audioinput':
              microphones.push({ deviceId: device.deviceId, label, kind: 'audioinput' })
              break
            case 'audiooutput':
              speakers.push({ deviceId: device.deviceId, label, kind: 'audiooutput' })
              break
            case 'videoinput':
              cameras.push({ deviceId: device.deviceId, label, kind: 'videoinput' })
              break
          }
        })

        $storex.meets.setAvailableDevices({ microphones, speakers, cameras })
        return { microphones, speakers, cameras, success: true }
      } catch (error) {
        console.error('[meets] Failed to enumerate devices:', error)
        return { 
          microphones: [], 
          speakers: [], 
          cameras: [], 
          success: false,
          error: error.message
        }
      }
    },

    /**
     * Test audio output with a 1kHz tone
     */
    async testAudioOutput({ frequency = 1000, duration = 1000 } = {}) {
      try {
        $storex.meets.setAudioTestActive(true)
        const audioContext = new (window.AudioContext || window.webkitAudioContext)()
        const oscillator = audioContext.createOscillator()
        const gainNode = audioContext.createGain()

        oscillator.connect(gainNode)
        gainNode.connect(audioContext.destination)

        oscillator.frequency.value = frequency
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
        oscillator.start()

        return new Promise(resolve => {
          setTimeout(() => {
            oscillator.stop()
            $storex.meets.setAudioTestActive(false)
            resolve({ success: true })
          }, duration)
        })
      } catch (error) {
        console.error('[meets] Audio test failed:', error)
        $storex.meets.setAudioTestActive(false)
        return { success: false, error: error.message }
      }
    },

    /**
     * Request microphone permission and get audio stream
     */
    async requestMicrophone({ deviceId = 'default' } = {}) {
      try {
        const constraints = {
          audio: deviceId === 'default'
            ? true
            : { deviceId: { exact: deviceId } },
          video: false
        }

        const stream = await navigator.mediaDevices.getUserMedia(constraints)
        return { stream, success: true }
      } catch (error) {
        console.error('[meets] Failed to get microphone:', error)
        const errorType = error.name === 'NotAllowedError' 
          ? 'permission_denied'
          : error.name === 'NotFoundError'
          ? 'device_not_found'
          : 'unknown_error'
        
        return { 
          stream: null, 
          success: false,
          errorType,
          error: error.message
        }
      }
    },

    /**
     * Initiate a new meet session.
     * Mock: immediately transitions to active after a short delay.
     */
    async initiateMeet({ state, commit }, { meetId, name, participants, chatId }) {
      if (!meetId) throw new Error('Meet ID is required')

      const currentUser = $storex.users.user
      const initiator = currentUser?.username || 'me'
      const allParticipants = [initiator, ...(participants || []).filter(p => p !== initiator)]

      commit('addActiveMeet', {
        meetId,
        name,
        initiator,
        participants: allParticipants,
        status: 'connecting',
        chatId
      })
      commit('setCurrentMeet', meetId)
      commit('setMeetStatus', 'connecting')

      if (!state._mockMode) {
        $storex.session.emit({
          event: 'meet-initiate',
          data: {
            meetId,
            from: initiator,
            fromName: initiator,
            fromAvatar: currentUser?.avatar,
            participants: allParticipants,
            timestamp: new Date().getTime()
          }
        })
      }

      if (state._mockMode) {
        return new Promise((resolve) => {
          setTimeout(() => {
            commit('updateMeetStatus', { meetId, status: 'active' })
            commit('setMeetStatus', 'active')
            $storex.meets._startMockDurationTimer(meetId)
            resolve(meetId)
          }, 1200)
        })
      }

      return meetId
    },

    /**
     * Join an existing meet session.
     */
    async joinMeet({ state, commit }, { meetId, chatId }) {
      if (!meetId) throw new Error('Meet ID is required')

      const currentUser = $storex.users.user
      const username = currentUser?.username || 'me'

      if (state.activeMeets[meetId]) {
        commit('addParticipantToMeet', { meetId, userId: username })
      } else {
        commit('addActiveMeet', {
          meetId,
          initiator: username,
          participants: [username],
          status: 'connecting',
          chatId
        })
      }

      commit('setCurrentMeet', meetId)
      commit('setMeetStatus', 'connecting')

      if (!state._mockMode) {
        $storex.session.emit({
          event: 'meet-join',
          data: { meetId, userId: username, timestamp: new Date().getTime() }
        })
      }

      if (state._mockMode) {
        return new Promise((resolve) => {
          setTimeout(() => {
            commit('updateMeetStatus', { meetId, status: 'active' })
            commit('setMeetStatus', 'active')
            $storex.meets._startMockDurationTimer(meetId)
            resolve(meetId)
          }, 800)
        })
      }
    },

    /**
     * Leave the current meet without ending it for others.
     */
    async leaveMeet({ state, commit }, { meetId }) {
      const currentUser = $storex.users.user
      const username = currentUser?.username || 'me'

      commit('removeParticipantFromMeet', { meetId, userId: username })

      if (state.currentMeetId === meetId) {
        commit('setCurrentMeet', null)
        commit('setMeetStatus', 'idle')
      }

      $storex.meets._stopMockDurationTimer(meetId)

      if (!state._mockMode) {
        $storex.session.emit({
          event: 'meet-leave',
          data: { meetId, userId: username, timestamp: new Date().getTime() }
        })
      }
    },

    /**
     * End the meet entirely for all participants.
     */
    async endMeet({ state, commit }, meetId) {
      const currentUser = $storex.users.user

      $storex.meets._stopMockDurationTimer(meetId)
      commit('endActiveMeet', meetId)
      commit('setMeetStatus', 'idle')

      if (!state._mockMode) {
        $storex.session.emit({
          event: 'meet-end',
          data: {
            meetId,
            endedBy: currentUser?.username,
            timestamp: new Date().getTime()
          }
        })
      }
    },

    /**
     * Toggle microphone mute state.
     */
    async toggleMute({ state, commit }, { meetId }) {
      const newMutedState = !state.isMuted
      commit('setIsMuted', newMutedState)

      if (meetId && state.activeMeets[meetId]) {
        commit('setMeetMuted', { meetId, muted: newMutedState })
      }

      if (!state._mockMode) {
        $storex.session.emit({
          event: 'meet-mute-toggle',
          data: {
            meetId,
            muted: newMutedState,
            userId: $storex.users.user?.username,
            timestamp: new Date().getTime()
          }
        })
      }
    },

    /**
     * Handle incoming meet invitation from socket.
     */
    handleIncomingInvitation({ commit }, invitation) {
      commit('addIncomingInvitation', invitation)
    },

    /**
     * Accept a meet invitation.
     */
    async acceptInvitation({ state, commit }, { meetId, chatId }) {
      const invitation = state.incomingInvitations[meetId]
      if (!invitation) return

      const currentUser = $storex.users.user
      const username = currentUser?.username || 'me'

      commit('addActiveMeet', {
        meetId,
        initiator: invitation.from,
        participants: [invitation.from, username],
        status: 'connecting',
        chatId
      })
      commit('setCurrentMeet', meetId)
      commit('setMeetStatus', 'connecting')
      commit('removeIncomingInvitation', meetId)

      if (!state._mockMode) {
        $storex.session.emit({
          event: 'meet-accept',
          data: { meetId, acceptedBy: username, timestamp: new Date().getTime() }
        })
      }

      if (state._mockMode) {
        return new Promise((resolve) => {
          setTimeout(() => {
            commit('updateMeetStatus', { meetId, status: 'active' })
            commit('setMeetStatus', 'active')
            $storex.meets._startMockDurationTimer(meetId)
            resolve(meetId)
          }, 800)
        })
      }
    },

    /**
     * Reject a meet invitation.
     */
    async rejectInvitation({ state, commit }, meetId) {
      const invitation = state.incomingInvitations[meetId]
      if (!invitation) return

      const currentUser = $storex.users.user
      commit('removeIncomingInvitation', meetId)

      if (!state._mockMode) {
        $storex.session.emit({
          event: 'meet-reject',
          data: { meetId, rejectedBy: currentUser?.username, timestamp: new Date().getTime() }
        })
      }
    },

    /**
     * Update meet status (used by socket events).
     */
    updateMeetStatus({ commit }, { meetId, status }) {
      commit('updateMeetStatus', { meetId, status })
    },

    /**
     * Add participant to meet (used by socket events).
     */
    addParticipantToMeet({ commit }, { meetId, userId }) {
      commit('addParticipantToMeet', { meetId, userId })
    },

    /**
     * End active meet from socket event.
     */
    endActiveMeet({ commit }, meetId) {
      $storex.meets._stopMockDurationTimer(meetId)
      commit('endActiveMeet', meetId)
    },

    /**
     * Update meet duration manually.
     */
    updateDuration({ commit }, { meetId, duration }) {
      commit('updateMeetDuration', { meetId, duration })
    },

    // ─────────────────────────────────────────────────
    // MOCK HELPERS
    // ─────────────────────────────────────────────────

    /**
     * Enable/disable mock mode.
     */
    setMockMode({ commit }, enabled) {
      commit('setMockMode', enabled)
    },

    /**
     * Start the duration ticker for a mock meet.
     */
    _startMockDurationTimer({ state, commit }, meetId) {
      if (state._mockDurationTimers[meetId]) return

      const timer = setInterval(() => {
        const meet = state.activeMeets[meetId]
        if (!meet) {
          clearInterval(timer)
          commit('setMockTimer', { meetId, timer: null })
          return
        }
        const duration = Math.floor((Date.now() - meet.startedAt) / 1000)
        commit('updateMeetDuration', { meetId, duration })
      }, 1000)

      commit('setMockTimer', { meetId, timer })
    },

    /**
     * Stop the duration ticker for a meet.
     */
    _stopMockDurationTimer({ state, commit }, meetId) {
      const timer = state._mockDurationTimers[meetId]
      if (timer) {
        clearInterval(timer)
        commit('setMockTimer', { meetId, timer: null })
      }
    },

    /**
     * Simulate an incoming invitation for testing.
     */
    mockIncomingInvitation({ commit }, { meetId, fromName }) {
      const names = ['alice', 'bob', 'charlie', 'diana']
      const name = fromName || names[Math.floor(Math.random() * names.length)]

      commit('addIncomingInvitation', {
        meetId: meetId || `meet_${Date.now()}`,
        from: name,
        fromName: name.charAt(0).toUpperCase() + name.slice(1),
        fromAvatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${name}`,
        timestamp: new Date().getTime()
      })
    },

    /**
     * Clear all meets (e.g. on logout).
     */
    clearMeets({ commit }) {
      commit('clearAllMeets')
    }
  }
)