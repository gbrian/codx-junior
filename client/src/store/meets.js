import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import { API } from '../api/api'
import { normalizeMeetCode, generateMeetCode } from '../utils/meetCode'

export const namespaced = true

// ─────────────────────────────────────────────────────────────────────────────
// NON-REACTIVE WebRTC STATE
//
// MediaStream / RTCPeerConnection instances are deliberately kept OUT of the
// Vuex state: they are large, non-serializable objects that are never rendered
// directly. Only the remote MediaStreams that must be bound to <video> elements
// are mirrored into the state through `setRemoteStream`.
// ─────────────────────────────────────────────────────────────────────────────

// { [meetId]: { [peerId]: RTCPeerConnection } }
const peerConnections = {}
// { [meetId]: { [peerId]: RTCIceCandidateInit[] } }
// ICE candidates can arrive before the offer/answer → buffered until the remote
// description is set.
const pendingCandidates = {}
// { [meetId]: MediaStream } – local mic + camera stream published to peers
const localStreams = {}
// { [meetId]: evt[] } – signals received before the meet was registered locally
const pendingSignals = {}
// { [meetId]: intervalId } – duration ticker
const durationTimers = {}

// Public STUN servers used for NAT traversal. The meets API does not expose a
// TURN/SFU endpoint yet, so peer-to-peer media works on most networks but not
// behind symmetric NATs. Call `setIceServers` to inject a TURN when available.
let iceServers = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' }
]

// Input level (0–100) at/above which the local microphone is considered to be
// picking up speech. Shared with the mic level monitor (src/utils/audioLevel.js)
// so the "speaking" pulse agrees with the boolean the UI reads.
const MIC_SPEAKING_THRESHOLD = 12

// ─────────────────────────────────────────────────────────────────────────────
// DEVICE IDENTITY (multi-device support)
//
// One *account* can be connected from several devices at the same time (e.g. a
// desktop and a phone). Because both sessions share the same username, a
// username alone cannot identify a peer: keying the rooms by username made the
// client treat the second device as "itself" — it was filtered out of the
// participant tiles and its WebRTC signals were ignored, so a phone could never
// see the desktop's camera.
//
// Every session is therefore identified by a composite key: the username plus a
// per-session discriminator. We prefer the remote socket id (`fromSid`, already
// present in the signalling payloads) and fall back to a locally generated,
// per-tab `deviceId`. The username is kept untouched for display only.
// ─────────────────────────────────────────────────────────────────────────────

function readDeviceId() {
  try {
    const key = 'codx-meet-device-id'
    let id = sessionStorage.getItem(key)
    if (!id) {
      id = Math.random().toString(36).slice(2) + Date.now().toString(36)
      sessionStorage.setItem(key, id)
    }
    return id
  } catch (e) {
    return `dev-${Math.random().toString(36).slice(2)}`
  }
}

// Stable per-tab device id: two tabs/devices of the same user get distinct ids.
const deviceId = readDeviceId()

/**
 * Build the composite, device-scoped peer key.
 *
 * @param {string} username - participant username (used for display too)
 * @param {string} [sid]    - session discriminator (socket id / device id). When
 *                            missing we degrade to the plain username, which
 *                            keeps the legacy single-device behaviour working.
 * @returns {string}
 */
function peerIdOf(username, sid) {
  const who = username || 'guest'
  return sid ? `${who}::${sid}` : who
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function currentUsername() {
  return $storex.users?.user?.username || 'guest'
}

function userProfile() {
  const u = $storex.users?.user || {}
  return {
    username: u.username || 'guest',
    name: u.name || u.username || 'guest',
    avatar: u.avatar || ''
  }
}

function normalizeParticipants(list) {
  return (list || [])
    .map(p => (typeof p === 'string' ? p : p?.username))
    .filter(Boolean)
}

/**
 * Resolve a user-entered meeting code (or a legacy meet id) to a meet id.
 */
function resolveMeetId(input) {
  if (!input) return ''
  return normalizeMeetCode(input)
}

/**
 * Map a backend Meet object (snake_case) to the client's meet shape.
 */
function meetToClient(meet, fallback = {}) {
  const meetId = meet?.meet_id || meet?.meetId || fallback.meetId
  const participants = normalizeParticipants(meet?.participants)
  return {
    meetId,
    name: meet?.name || fallback.name || `Meet ${String(meetId || '').slice(0, 8)}`,
    initiator: meet?.initiator || fallback.initiator || currentUsername(),
    participants: participants.length ? participants : (fallback.participants || [currentUsername()]),
    status: meet?.status === 'ended' ? 'ended' : 'active',
    chatId: fallback.chatId || null,
    startedAt: meet?.created_at ? new Date(meet.created_at).getTime() : (fallback.startedAt || Date.now()),
    duration: 0
  }
}

/**
 * Get (or lazily create) the RTCPeerConnection towards a remote *session*.
 *
 * `peerId` is the device-scoped key (see `peerIdOf`) so two devices logged in
 * with the same account get independent connections instead of sharing one.
 */
function ensurePeer(ctx, meetId, peerId, username = '') {
  peerConnections[meetId] = peerConnections[meetId] || {}
  const existing = peerConnections[meetId][peerId]
  if (existing) {
    if (username) existing._username = username
    return existing
  }

  const pc = new RTCPeerConnection({ iceServers })
  // Remember the display name so `ontrack` can label the remote stream even
  // though the map key is a device-scoped id.
  pc._username = username || peerId

  pc.onicecandidate = (event) => {
    if (!event.candidate) return
    // Echo the candidate back through the REST signalling endpoint.
    API.meets.addIceCandidate({ meetId, candidate: event.candidate, to: username || peerId })
      .catch(err => console.warn('[meets] failed to send ICE candidate', err))
  }

  pc.ontrack = (event) => {
    const [stream] = event.streams
    if (stream) {
      ctx.commit('setRemoteStream', { meetId, peerId, username: pc._username, stream })
    }
  }

  // Publish the local media we already have when the peer is created.
  const stream = localStreams[meetId]
  if (stream) {
    stream.getTracks().forEach(track => {
      try { pc.addTrack(track, stream) } catch (e) { /* already added */ }
    })
  }

  peerConnections[meetId][peerId] = pc
  return pc
}

function closePeer(ctx, meetId, peerId) {
  const pc = peerConnections[meetId]?.[peerId]
  if (pc) {
    try { pc.close() } catch (e) { /* ignore */ }
    delete peerConnections[meetId][peerId]
  }
  if (pendingCandidates[meetId]) {
    delete pendingCandidates[meetId][peerId]
  }
  ctx.commit('removeRemoteStream', { meetId, peerId })
}

function closeAllPeers(ctx, meetId) {
  const peers = peerConnections[meetId] || {}
  Object.keys(peers).forEach(peerId => closePeer(ctx, meetId, peerId))
  delete peerConnections[meetId]
  delete pendingCandidates[meetId]
}

async function flushCandidates(meetId, peerId, pc) {
  const buffered = pendingCandidates[meetId]?.[peerId] || []
  if (pendingCandidates[meetId]) pendingCandidates[meetId][peerId] = []
  for (const candidate of buffered) {
    try {
      await pc.addIceCandidate(new RTCIceCandidate(candidate))
    } catch (e) {
      console.warn('[meets] buffered addIceCandidate failed', e)
    }
  }
}

/**
 * Keep every peer connection in sync with the current local media: replace the
 * sender tracks that exist, add the new ones and silence the removed kinds.
 */
async function syncLocalTracks(meetId) {
  const stream = localStreams[meetId]
  const peers = peerConnections[meetId] || {}
  for (const peerId of Object.keys(peers)) {
    const pc = peers[peerId]
    for (const kind of ['audio', 'video']) {
      const track = stream ? stream.getTracks().find(t => t.kind === kind) : null
      const sender = pc.getSenders().find(s => s.track?.kind === kind)
      try {
        if (track && sender) {
          await sender.replaceTrack(track)
        } else if (track && !sender) {
          pc.addTrack(track, stream)
        } else if (!track && sender) {
          await sender.replaceTrack(null)
        }
      } catch (e) {
        console.warn('[meets] sync local track failed', e)
      }
    }
  }
}

export const state = () => ({
  // Active meet sessions: { meetId: { meetId, name, initiator, participants, startedAt, duration, status, chatId, localStream, remoteStreams } }
  activeMeets: {},

  // Incoming meet invitations: { meetId: { meetId, from, fromName, fromAvatar, timestamp } }
  incomingInvitations: {},

  // Active meets advertised by the backend (used to discover meets to join):
  // [ { meetId, name, initiator, participants, ... } ]
  serverMeets: [],

  // Incoming "knock" requests waiting for approval, keyed by "meetId:from":
  // { [key]: { meetId, from, fromName, fromAvatar, timestamp } }
  joinRequests: {},

  // Outgoing knocks we are waiting on: { [meetId]: { meetId, status, ts } }
  outgoingJoins: {},

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

  // Whether the LOCAL camera is currently on. Kept independently of any active
  // meet so the UI (e.g. the Meet panel tab icon) can reflect the camera even
  // before joining — the pre-join lobby has no meet in `activeMeets` yet.
  localCameraEnabled: false,

  // Whether the LOCAL microphone is currently capturing, together with the
  // latest input level (0–100). Like the camera flag this is meet-independent so
  // the mic indicator (Meet panel tab, call controls, participant list, …) works
  // everywhere — including the pre-join lobby.
  localMicEnabled: false,
  micLevel: 0
})

export const getters = getterTree(state, {
  allActiveMeets: (state) => Object.values(state.activeMeets),
  currentMeet: (state) => state.currentMeetId ? state.activeMeets[state.currentMeetId] : null,
  allIncomingInvitations: (state) => Object.values(state.incomingInvitations),
  isInMeet: (state) => state.currentMeetId !== null && state.meetStatus === 'active',
  recentMeetHistory: (state) => state.meetHistory.slice(-10),
  activeMeetCount: (_, getters) => getters.allActiveMeets.length,
  incomingInvitationCount: (_, getters) => getters.allIncomingInvitations.length,
  // Local camera on/off, independent of any active meet (works pre-join).
  isLocalCameraOn: (state) => state.localCameraEnabled,
  // Local microphone on/off, independent of any active meet (works pre-join).
  isLocalMicOn: (state) => state.localMicEnabled,
  // True only while the mic is capturing AND audio above the threshold is
  // detected — this drives the "speaking" pulse on the mic indicator.
  isMicSpeaking: (state) => state.localMicEnabled && state.micLevel >= MIC_SPEAKING_THRESHOLD,
  meetForId: (state) => (meetId) => state.activeMeets[meetId] || null,
  // Remote streams are keyed by the device-scoped peer id.
  remoteStreamsFor: (state) => (meetId) => state.activeMeets[meetId]?.remoteStreams || {},
  // Remote peers as an array of { peerId, username, stream } entries — one per
  // session (so two devices of the same user appear separately).
  remotePeersFor: (state) => (meetId) =>
    Object.values(state.activeMeets[meetId]?.remoteStreams || {}),
  deviceCount: (state) => {
    return {
      microphones: state.availableDevices.microphones.length,
      speakers: state.availableDevices.speakers.length,
      cameras: state.availableDevices.cameras.length
    }
  },
  // Active meets fetched from the backend.
  activeServerMeets: (state) => state.serverMeets,
  // Meets that can be joined right away because the current user is already a
  // participant (or the backend did not report participants at all, in which
  // case we let the user try).
  joinableMeets: (state) => {
    const me = currentUsername()
    return state.serverMeets.filter(meet => {
      const participants = meet.participants || []
      return participants.length === 0 || participants.includes(me)
    })
  },
  // Incoming knock requests as an array (with a stable key for rendering).
  joinRequestsList: (state) =>
    Object.entries(state.joinRequests).map(([key, req]) => ({ key, ...req })),
  joinRequestCount: (state) => Object.keys(state.joinRequests).length
})

export const mutations = mutationTree(state, {
  addActiveMeet(state, meet) {
    const prev = state.activeMeets[meet.meetId]
    state.activeMeets = {
      ...state.activeMeets,
      [meet.meetId]: {
        meetId: meet.meetId,
        name: meet.name || `Meet ${String(meet.meetId).slice(0, 8)}`,
        initiator: meet.initiator,
        participants: meet.participants || [meet.initiator],
        startedAt: meet.startedAt || new Date().getTime(),
        duration: prev?.duration || 0,
        status: meet.status || 'connecting',
        chatId: meet.chatId || prev?.chatId || null,
        isMuted: false,
        localStream: prev?.localStream || null,
        remoteStreams: prev?.remoteStreams || {}
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

  setChatId(state, { meetId, chatId }) {
    if (state.activeMeets[meetId]) {
      state.activeMeets[meetId].chatId = chatId
    }
  },

  setLocalStream(state, { meetId, stream }) {
    if (state.activeMeets[meetId]) {
      state.activeMeets[meetId].localStream = stream || null
    }
  },

  // remoteStreams is keyed by the *device-scoped* peer id so that two devices
  // logged in with the same account stay separate entries.
  setRemoteStream(state, { meetId, peerId, username, stream }) {
    if (!state.activeMeets[meetId]) return
    state.activeMeets[meetId].remoteStreams = {
      ...state.activeMeets[meetId].remoteStreams,
      [peerId]: { peerId, username: username || peerId, stream }
    }
  },

  removeRemoteStream(state, { meetId, peerId }) {
    if (!state.activeMeets[meetId]) return
    const streams = { ...state.activeMeets[meetId].remoteStreams }
    delete streams[peerId]
    state.activeMeets[meetId].remoteStreams = streams
  },

  setParticipants(state, { meetId, participants }) {
    if (state.activeMeets[meetId]) {
      state.activeMeets[meetId].participants = normalizeParticipants(participants)
    }
  },

  setMeetMuted(state, { meetId, muted }) {
    if (state.activeMeets[meetId]) {
      state.activeMeets[meetId].isMuted = muted
    }
    state.isMuted = muted
  },

  addParticipantToMeet(state, { meetId, userId }) {
    if (state.activeMeets[meetId] && userId && !state.activeMeets[meetId].participants.includes(userId)) {
      state.activeMeets[meetId].participants = [...state.activeMeets[meetId].participants, userId]
    }
  },

  removeParticipantFromMeet(state, { meetId, userId }) {
    if (state.activeMeets[meetId]) {
      state.activeMeets[meetId].participants = state.activeMeets[meetId].participants.filter(p => p !== userId)
    }
  },

  setServerMeets(state, meets) {
    state.serverMeets = meets || []
  },

  addJoinRequest(state, request) {
    const key = `${request.meetId}:${request.from}`
    state.joinRequests = {
      ...state.joinRequests,
      [key]: {
        meetId: request.meetId,
        from: request.from,
        fromName: request.fromName || request.from,
        fromAvatar: request.fromAvatar || '',
        timestamp: request.timestamp || Date.now()
      }
    }
  },

  removeJoinRequest(state, key) {
    const updated = { ...state.joinRequests }
    delete updated[key]
    state.joinRequests = updated
  },

  clearJoinRequestsFor(state, meetId) {
    const updated = { ...state.joinRequests }
    Object.keys(updated)
      .filter(key => key.startsWith(`${meetId}:`))
      .forEach(key => delete updated[key])
    state.joinRequests = updated
  },

  setOutgoingJoin(state, { meetId, status }) {
    state.outgoingJoins = {
      ...state.outgoingJoins,
      [meetId]: { meetId, status: status || 'pending', ts: Date.now() }
    }
  },

  removeOutgoingJoin(state, meetId) {
    const updated = { ...state.outgoingJoins }
    delete updated[meetId]
    state.outgoingJoins = updated
  },

  endActiveMeet(state, meetId) {
    const meet = state.activeMeets[meetId]
    if (meet) {
      // Cleanup streams
      if (meet.localStream) {
        meet.localStream.getTracks().forEach(track => track.stop())
      }
      Object.values(meet.remoteStreams || {}).forEach(entry => {
        // Entries are { peerId, username, stream }; tolerate the legacy shape
        // (a bare MediaStream) so an in-flight upgrade never throws.
        const stream = entry?.stream || entry
        if (stream?.getTracks) stream.getTracks().forEach(track => track.stop())
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

  // Mirror the local camera on/off flag so it can be observed globally (e.g. by
  // the Meet panel tab) even when no meet is active yet.
  setLocalCameraEnabled(state, enabled) {
    state.localCameraEnabled = !!enabled
  },

  // Mirror the local microphone on/off flag globally (works pre-join too).
  setLocalMicEnabled(state, enabled) {
    state.localMicEnabled = !!enabled
    if (!enabled) state.micLevel = 0
  },

  // Latest local microphone input level (0–100), used to derive "speaking".
  setMicLevel(state, level) {
    state.micLevel = Math.max(0, Math.min(100, Number(level) || 0))
  },

  clearAllMeets(state) {
    state.activeMeets = {}
    state.incomingInvitations = {}
    state.serverMeets = []
    state.joinRequests = {}
    state.outgoingJoins = {}
    state.currentMeetId = null
    state.meetStatus = 'idle'
    state.isMuted = false
    state.localCameraEnabled = false
    state.localMicEnabled = false
    state.micLevel = 0
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
     * Configure the ICE servers used by every peer connection. Call this once a
     * TURN server becomes available (the meets API does not serve one yet).
     */
    setIceServers(_, servers) {
      if (Array.isArray(servers) && servers.length) {
        iceServers = servers
      }
    },

    // ─────────────────────────────────────────────────
    // LOCAL MEDIA
    // ─────────────────────────────────────────────────

    /**
     * Publish the local (mic + camera) stream to every connected peer. Pass a
     * null stream to silence/stop everything.
     */
    async setLocalStream(ctx, { meetId, stream } = {}) {
      if (!meetId) return
      if (stream) {
        localStreams[meetId] = stream
        ctx.commit('setLocalStream', { meetId, stream })
      } else {
        delete localStreams[meetId]
        ctx.commit('setLocalStream', { meetId, stream: null })
      }
      await syncLocalTracks(meetId)
    },

    // ─────────────────────────────────────────────────
    // DISCOVERY & CODES
    // ─────────────────────────────────────────────────

    /**
     * Fetch the list of active meets from the backend so users can discover
     * meets they may (re)join. Results are normalised and cached in state.
     */
    async loadActiveMeets(ctx) {
      try {
        const result = await API.meets.listActiveMeets()
        const meets = (result?.meets || result || [])
          .map(m => meetToClient(m))
          .filter(m => !!m.meetId)
        ctx.commit('setServerMeets', meets)
        return meets
      } catch (error) {
        console.warn('[meets] loadActiveMeets failed', error)
        return ctx.state.serverMeets
      }
    },

    /**
     * Join a meet by its shareable code (or a legacy meet id). If other people
     * are already in the meet we "knock" and wait for approval; otherwise we
     * join directly so an empty/unknown room never deadlocks.
     */
    async joinByCode(ctx, { code } = {}) {
      const meetId = resolveMeetId(code)
      if (!meetId) {
        throw new Error('Enter a valid meeting code')
      }

      // Try to discover the meet so we know whether approval is required.
      if (!ctx.state.serverMeets.length) {
        await ctx.dispatch('loadActiveMeets').catch(() => {})
      }

      const meet = ctx.state.serverMeets.find(m => m.meetId === meetId)
      const me = currentUsername()
      const hasOthers = !!meet && (meet.participants || []).some(p => p !== me)

      if (hasOthers && !(meet.participants || []).includes(me)) {
        return ctx.dispatch('askToJoin', { meetId })
      }
      return ctx.dispatch('joinMeet', { meetId })
    },

    /**
     * Send a "knock" (join request) for a meet and wait for a participant to
     * approve. Approval/rejection arrives as a socket `codx-junior-meet` event.
     */
    askToJoin(ctx, { meetId } = {}) {
      if (!meetId) return
      const profile = userProfile()
      ctx.commit('setOutgoingJoin', { meetId, status: 'pending' })
      API.socket?.emit('codx-junior-meet', {
        type: 'join-request',
        meetId,
        from: profile.username,
        fromName: profile.name,
        fromAvatar: profile.avatar,
        timestamp: Date.now()
      })
      $storex.session.onInfo('Waiting for the host to admit you…')
      return { pending: true, meetId }
    },

    /**
     * Approve (admit) a pending join request and tell the requester.
     */
    approveJoinRequest(ctx, { meetId, from } = {}) {
      if (!meetId || !from) return
      API.socket?.emit('codx-junior-meet', {
        type: 'join-approved',
        meetId,
        from: currentUsername(),
        to: from,
        timestamp: Date.now()
      })
      ctx.commit('removeJoinRequest', `${meetId}:${from}`)
      ctx.commit('addParticipantToMeet', { meetId, userId: from })
      $storex.session.onInfo(`Admitted ${from}`)
    },

    /**
     * Reject (deny) a pending join request and tell the requester.
     */
    rejectJoinRequest(ctx, { meetId, from } = {}) {
      if (!meetId || !from) return
      API.socket?.emit('codx-junior-meet', {
        type: 'join-rejected',
        meetId,
        from: currentUsername(),
        to: from,
        timestamp: Date.now()
      })
      ctx.commit('removeJoinRequest', `${meetId}:${from}`)
      $storex.session.onInfo(`Declined ${from}`)
    },

    // ─────────────────────────────────────────────────
    // LIFECYCLE (REST)
    // ─────────────────────────────────────────────────

    /**
     * Initiate a new meet session. Creates it on the backend (REST) and starts
     * the local session. If no `meetId` is supplied a shareable code is
     * generated, so the meet can be joined by code.
     */
    async initiateMeet(ctx, { meetId, name, participants, chatId } = {}) {
      const profile = userProfile()
      const invites = normalizeParticipants(participants)
      const id = meetId || generateMeetCode()

      let serverMeet = null
      try {
        const result = await API.meets.initiateMeet({ meetId: id, name, participants: invites })
        serverMeet = result?.meet || null
      } catch (error) {
        console.error('[meets] initiateMeet failed', error)
        throw error
      }

      const client = meetToClient(serverMeet, {
        meetId: serverMeet?.meet_id || id,
        name,
        chatId,
        initiator: profile.username,
        participants: [profile.username, ...invites.filter(u => u !== profile.username)],
        startedAt: Date.now()
      })

      ctx.commit('addActiveMeet', client)
      ctx.commit('setCurrentMeet', client.meetId)
      ctx.commit('setMeetStatus', 'active')

      await ctx.dispatch('_startDurationTimer', client.meetId)
      ctx.dispatch('_flushPendingSignals', client.meetId)
      return client.meetId
    },

    /**
     * Join an existing meet session (REST). The backend registers us as a
     * participant; existing peers will offer us a connection.
     */
    async joinMeet(ctx, { meetId, chatId } = {}) {
      if (!meetId) throw new Error('Meet ID is required')

      let serverMeet = null
      try {
        const result = await API.meets.joinMeet({ meetId })
        serverMeet = result?.meet || null
      } catch (error) {
        console.error('[meets] joinMeet failed', error)
        throw error
      }

      const client = meetToClient(serverMeet, { meetId, chatId, startedAt: Date.now() })
      ctx.commit('addActiveMeet', client)
      // Register the *normalised* id as the current meet so the view can open
      // the room even when the backend returns its own `meet_id`.
      ctx.commit('setCurrentMeet', client.meetId)
      ctx.commit('setMeetStatus', 'active')

      await ctx.dispatch('_startDurationTimer', client.meetId)
      ctx.dispatch('_flushPendingSignals', client.meetId)
      return client.meetId
    },

    /**
     * Leave the current meet without ending it for others.
     */
    async leaveMeet(ctx, { meetId } = {}) {
      if (!meetId) return
      try {
        await API.meets.leaveMeet({ meetId })
      } catch (error) {
        console.warn('[meets] leaveMeet failed', error)
      }
      ctx.commit('removeParticipantFromMeet', { meetId, userId: currentUsername() })
      await ctx.dispatch('endActiveMeet', meetId)
    },

    /**
     * End the meet entirely for all participants (initiator).
     */
    async endMeet(ctx, meetId) {
      if (!meetId) return
      try {
        await API.meets.endMeet({ meetId })
      } catch (error) {
        console.warn('[meets] endMeet failed', error)
      }
      await ctx.dispatch('endActiveMeet', meetId)
    },

    /**
     * Tear down a meet locally (peers, media, timer, state).
     */
    endActiveMeet(ctx, meetId) {
      const meet = ctx.state.activeMeets[meetId]
      if (meet?.localStream) {
        meet.localStream.getTracks().forEach(t => t.stop())
      }
      closeAllPeers(ctx, meetId)
      delete localStreams[meetId]
      delete pendingSignals[meetId]
      ctx.commit('clearJoinRequestsFor', meetId)
      ctx.commit('removeOutgoingJoin', meetId)
      ctx.dispatch('_stopDurationTimer', meetId)
      ctx.commit('endActiveMeet', meetId)
    },

    /**
     * Toggle microphone mute state (local UI only – the meets API exposes no
     * per-participant mute endpoint yet).
     */
    toggleMute({ commit, state }, { meetId } = {}) {
      const muted = !state.isMuted
      commit('setIsMuted', muted)
      if (meetId && state.activeMeets[meetId]) {
        commit('setMeetMuted', { meetId, muted })
      }
      return muted
    },

    // ─────────────────────────────────────────────────
    // INVITATIONS
    // ─────────────────────────────────────────────────

    /**
     * Handle incoming meet invitation from socket.
     */
    handleIncomingInvitation({ commit }, invitation) {
      commit('addIncomingInvitation', invitation)
    },

    /**
     * Accept a meet invitation → join the session on the backend.
     */
    async acceptInvitation(ctx, { meetId, chatId } = {}) {
      if (!ctx.state.incomingInvitations[meetId]) return
      ctx.commit('removeIncomingInvitation', meetId)
      return ctx.dispatch('joinMeet', { meetId, chatId })
    },

    /**
     * Reject a meet invitation.
     */
    rejectInvitation({ commit }, meetId) {
      commit('removeIncomingInvitation', meetId)
    },

    // ─────────────────────────────────────────────────
    // SOCKET EVENTS
    // ─────────────────────────────────────────────────

    /**
     * Handle a `codx-junior-meet` lifecycle event.
     *
     * Known types:
     *   • 'initiated'      – a meet was created
     *   • 'joined' / 'left' / 'ended' – participant lifecycle
     *   • 'join-request'   – someone is knocking on a meet we are in
     *   • 'join-approved'  – our knock was accepted (→ join for real)
     *   • 'join-rejected'  – our knock was declined
     *
     * Payload: { type, meetId, from, fromSid?, to, fromName?, fromAvatar?, meet?, participants? }
     *
     * `fromSid` is the sender's session id: it distinguishes the several
     * devices a single account may join from.
     */
    handleMeetEvent(ctx, evt = {}) {
      const { type, meetId, from, to } = evt
      if (!meetId || !type) return
      const me = currentUsername()
      const fromSid = evt.fromSid || evt.fromDevice || ''

      // Outgoing knock resolved (we are not in the meet yet, so handle first).
      if (type === 'join-approved' || type === 'join-rejected') {
        if (to && to !== me) return
        if (!ctx.state.outgoingJoins[meetId]) return
        ctx.commit('removeOutgoingJoin', meetId)
        if (type === 'join-approved') {
          $storex.session.onInfo('You were admitted to the meet')
          ctx.dispatch('joinMeet', { meetId })
        } else {
          $storex.session.onWarning('Your request to join was declined')
        }
        return
      }

      if (type === 'initiated') {
        const initiator = evt.meet?.initiator || from
        if (initiator === me && (!fromSid || fromSid === API.sid)) return   // our own initiate
        if (ctx.state.activeMeets[meetId]) return
        const initiatorInfo = (evt.meet?.participants || [])
          .find(p => (typeof p === 'string' ? p : p.username) === initiator)
        ctx.commit('addIncomingInvitation', {
          meetId,
          from: initiator,
          fromName: initiatorInfo?.name || initiator,
          fromAvatar: initiatorInfo?.avatar || '',
          timestamp: Date.now()
        })
        return
      }

      // Everything else only concerns meets we are part of
      if (!ctx.state.activeMeets[meetId]) return

      if (type === 'join-request') {
        const requester = from
        // A same-username knock from *another* device is a real request.
        if (!requester || (requester === me && (!fromSid || fromSid === API.sid))) return
        ctx.commit('addJoinRequest', {
          meetId,
          from: requester,
          fromName: evt.fromName || requester,
          fromAvatar: evt.fromAvatar || ''
        })
        $storex.session.onInfo(`${evt.fromName || requester} wants to join the meet`)
        return
      }

      if (type === 'joined') {
        const list = normalizeParticipants(evt.participants)
        if (list.length) ctx.commit('setParticipants', { meetId, participants: list })
        else if (from) ctx.commit('addParticipantToMeet', { meetId, userId: from })

        // Mesh topology: every peer already in the meet offers to the newcomer.
        // The newcomer itself waits for the incoming offers.
        //
        // A second device of the SAME user is a real newcomer, so compare the
        // session id too instead of skipping every same-username join.
        const isSelfEcho = from === me && (!fromSid || fromSid === API.sid)
        if (from && !isSelfEcho) {
          ctx.dispatch('createOffer', { meetId, to: from, toSid: fromSid, username: from })
        }
        return
      }

      if (type === 'left') {
        const list = normalizeParticipants(evt.participants)
        if (list.length) ctx.commit('setParticipants', { meetId, participants: list })
        if (from) ctx.dispatch('_dropPeer', { meetId, peerId: peerIdOf(from, fromSid), username: from })
        return
      }

      if (type === 'ended') {
        ctx.dispatch('endActiveMeet', meetId)
      }
    },

    /**
     * Handle a `codx-junior-meet-signal` WebRTC event.
     * Payload: { meetId, type: 'offer'|'answer'|'ice-candidate', from, fromSid, to, signal }
     */
    async handleMeetSignal(ctx, evt = {}) {
      const { meetId, type, from, to, signal } = evt
      if (!meetId || !from || !type) return

      const fromSid = evt.fromSid || evt.fromDevice || ''
      const fromPeerId = peerIdOf(from, fromSid)
      const me = currentUsername()
      const mySid = API.sid

      // Drop only our OWN echo. A second device of the same user shares the
      // username but not the session id, so it must NOT be treated as "me" —
      // doing so is exactly what stopped a phone from seeing the desktop.
      const isSelfEcho = from === me && (!fromSid || fromSid === mySid)
      if (isSelfEcho) return
      if (to && to !== me && to !== mySid) return   // not addressed to us

      // The signalling event can race ahead of the REST (join) response → buffer.
      if (!ctx.state.activeMeets[meetId]) {
        pendingSignals[meetId] = pendingSignals[meetId] || []
        if (pendingSignals[meetId].length < 100) pendingSignals[meetId].push(evt)
        return
      }

      try {
        if (type === 'offer') {
          const pc = ensurePeer(ctx, meetId, fromPeerId, from)
          await pc.setRemoteDescription(new RTCSessionDescription(signal))
          await flushCandidates(meetId, fromPeerId, pc)
          const answer = await pc.createAnswer()
          await pc.setLocalDescription(answer)
          await API.meets.sendAnswer({ meetId, answer, to: from })
        } else if (type === 'answer') {
          const pc = peerConnections[meetId]?.[fromPeerId]
          if (!pc) return
          await pc.setRemoteDescription(new RTCSessionDescription(signal))
          await flushCandidates(meetId, fromPeerId, pc)
        } else if (type === 'ice-candidate') {
          if (!signal) return
          const pc = peerConnections[meetId]?.[fromPeerId]
          if (pc && pc.remoteDescription && pc.remoteDescription.type) {
            await pc.addIceCandidate(new RTCIceCandidate(signal))
          } else {
            pendingCandidates[meetId] = pendingCandidates[meetId] || {}
            pendingCandidates[meetId][fromPeerId] = pendingCandidates[meetId][fromPeerId] || []
            pendingCandidates[meetId][fromPeerId].push(signal)
          }
        }
      } catch (error) {
        console.error('[meets] handleMeetSignal failed', type, error)
      }
    },

    /**
     * Create and send an SDP offer to a specific peer *session*.
     * `to` is the username (used for routing/display), `toSid` is the target
     * session id when the payload provides one.
     */
    async createOffer(ctx, { meetId, to, toSid, username } = {}) {
      if (!meetId || !to) return
      const peerId = peerIdOf(to, toSid)
      try {
        const pc = ensurePeer(ctx, meetId, peerId, username || to)
        if (pc.signalingState !== 'stable') return
        const offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        await API.meets.sendOffer({ meetId, offer, to })
      } catch (error) {
        console.error('[meets] createOffer failed', error)
      }
    },

    /**
     * Drop the peer connection of a session that left. Accepts either the
     * device-scoped `peerId` or, as a fallback, the `username` (legacy payloads
     * without a session id — drops every session of that user).
     */
    _dropPeer(ctx, { meetId, peerId, username } = {}) {
      if (peerId) {
        closePeer(ctx, meetId, peerId)
        return
      }
      if (username) {
        Object.keys(peerConnections[meetId] || {})
          .filter(k => k === username || k.startsWith(`${username}::`))
          .forEach(k => closePeer(ctx, meetId, k))
      }
    },

    /**
     * Process signals buffered before the meet was registered locally.
     */
    _flushPendingSignals(ctx, meetId) {
      const buffered = pendingSignals[meetId] || []
      delete pendingSignals[meetId]
      buffered.forEach(evt => ctx.dispatch('handleMeetSignal', evt))
    },

    // ─────────────────────────────────────────────────
    // STATE HELPERS
    // ─────────────────────────────────────────────────

    /**
     * Update meet status (used by socket events / external callers).
     */
    updateMeetStatus({ commit }, { meetId, status }) {
      commit('updateMeetStatus', { meetId, status })
    },

    /**
     * Add participant to meet (used by socket events / external callers).
     */
    addParticipantToMeet({ commit }, { meetId, userId }) {
      commit('addParticipantToMeet', { meetId, userId })
    },

    /**
     * Update meet duration manually.
     */
    updateDuration({ commit }, { meetId, duration }) {
      commit('updateMeetDuration', { meetId, duration })
    },

    /**
     * Persist the meet chat association.
     */
    setChatId({ commit }, { meetId, chatId }) {
      commit('setChatId', { meetId, chatId })
    },

    /**
     * Reflect the local camera on/off state globally. Called by the meet UI when
     * the camera stream starts/stops so any UI (e.g. the Meet panel tab) can
     * show a camera indicator — even in the pre-join lobby with no active meet.
     */
    setLocalCameraEnabled({ commit }, enabled) {
      commit('setLocalCameraEnabled', enabled)
    },

    /**
     * Reflect the local microphone on/off state globally. Called by the meet UI
     * when the mic opens/closes so any UI (e.g. the Meet panel tab or the call
     * controls) can show a live mic indicator — even before joining.
     */
    setLocalMicEnabled({ commit }, enabled) {
      commit('setLocalMicEnabled', enabled)
    },

    /**
     * Publish the latest local microphone input level (0–100) so the "speaking"
     * state can be observed everywhere.
     */
    setMicLevel({ commit }, level) {
      commit('setMicLevel', level)
    },

    /**
     * List meets from the backend (active by default). Kept for backwards
     * compatibility — `loadActiveMeets` also stores them in state.
     */
    async listMeets() {
      try {
        const result = await API.meets.listActiveMeets()
        return result?.meets || result || []
      } catch (error) {
        console.warn('[meets] listMeets failed', error)
        return []
      }
    },

    // ─────────────────────────────────────────────────
    // HELPERS
    // ─────────────────────────────────────────────────

    /**
     * Start the duration ticker for a meet.
     */
    _startDurationTimer({ state, commit }, meetId) {
      if (durationTimers[meetId]) return

      const timer = setInterval(() => {
        const meet = state.activeMeets[meetId]
        if (!meet) {
          clearInterval(timer)
          delete durationTimers[meetId]
          return
        }
        const duration = Math.floor((Date.now() - meet.startedAt) / 1000)
        commit('updateMeetDuration', { meetId, duration })
      }, 1000)

      durationTimers[meetId] = timer
    },

    /**
     * Stop the duration ticker for a meet.
     */
    _stopDurationTimer(ctx, meetId) {
      const timer = durationTimers[meetId]
      if (timer) {
        clearInterval(timer)
        delete durationTimers[meetId]
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
    clearMeets(ctx) {
      Object.keys(peerConnections).forEach(meetId => closeAllPeers(ctx, meetId))
      Object.keys(durationTimers).forEach(meetId => ctx.dispatch('_stopDurationTimer', meetId))
      Object.keys(localStreams).forEach(meetId => delete localStreams[meetId])
      Object.keys(pendingSignals).forEach(meetId => delete pendingSignals[meetId])
      ctx.commit('clearAllMeets')
    }
  }
)
