/**
 * Browser-session collaboration transport.
 *
 * Two users in the same meeting already have a WebRTC peer connection (the
 * meet mesh in `store/meets.js`).  This module piggybacks on it with a
 * dedicated ordered data channel, so browser annotations, presence and the
 * "share this session" announcement reach every participant without adding a
 * new backend endpoint.  A `BroadcastChannel` mirrors the same messages between
 * tabs of the same browser, which keeps a user's tabs in sync even outside a
 * call.
 *
 * The transport is deliberately channel-agnostic: callers send plain objects
 * and every listener receives the same shape, regardless of whether the
 * message arrived over WebRTC or the local BroadcastChannel.
 */

const CHANNEL_LABEL = 'codx-browser-collab'
const MESSAGE_SCOPE = 'codx-browser-collab'
const CHUNK_SIZE = 48 * 1024
const PRESENCE_TTL_MS = 45 * 1000

let clientId = null
try {
  const key = 'codx-browser-collab-client-id'
  clientId = sessionStorage.getItem(key)
  if (!clientId) {
    clientId = `bc_${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`
    sessionStorage.setItem(key, clientId)
  }
} catch (e) {
  clientId = `bc_${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`
}

// { `${meetId}::${peerId}`: RTCDataChannel }
const channels = new Map()
// Messages waiting for a data channel to finish opening.
const pendingByChannel = new Map()
// Serialized chunks waiting for SCTP send-buffer space.
const sendQueues = new Map()
// { messageId: { parts: string[], total: number, received: number, createdAt: number } }
const pendingChunks = new Map()
// { meetId: Map<clientId, { clientId, user, sessionId, lastSeen }> }
const participants = new Map()
const listeners = new Set()

let localBroadcast = null
try {
  if (typeof BroadcastChannel !== 'undefined') {
    localBroadcast = new BroadcastChannel(MESSAGE_SCOPE)
    localBroadcast.onmessage = event => handleWireMessage(null, null, event.data)
  }
} catch (e) {
  localBroadcast = null
}

/** Stable id of this tab. */
export function getCollabClientId() {
  return clientId
}

function channelKey(meetId, peerId) {
  return `${meetId || 'local'}::${peerId || 'local'}`
}

/**
 * Create the collaboration data channel on an outgoing peer connection.
 * The answering peer receives it through `ondatachannel` and registers it with
 * `attachCollabDataChannel`.
 *
 * @param {string} meetId
 * @param {string} peerId
 * @param {RTCPeerConnection} peerConnection
 * @returns {RTCDataChannel|null}
 */
export function createCollabDataChannel(meetId, peerId, peerConnection) {
  if (!peerConnection || !meetId || !peerId) return null
  if (peerConnection._codxCollabChannel) return peerConnection._codxCollabChannel
  try {
    const channel = peerConnection.createDataChannel(CHANNEL_LABEL, { ordered: true })
    peerConnection._codxCollabChannel = channel
    registerChannel(meetId, peerId, channel)
    return channel
  } catch (error) {
    console.warn('[browserCollab] Could not create data channel', error)
    return null
  }
}

/**
 * Register a data channel that was created by the remote peer.
 *
 * @param {string} meetId
 * @param {string} peerId
 * @param {RTCDataChannel} channel
 */
export function attachCollabDataChannel(meetId, peerId, channel) {
  if (!channel || channel.label !== CHANNEL_LABEL) return
  registerChannel(meetId, peerId, channel)
}

function registerChannel(meetId, peerId, channel) {
  const key = channelKey(meetId, peerId)
  const previous = channels.get(key)
  if (previous && previous !== channel) {
    try { previous.close() } catch (e) { /* ignore */ }
  }
  channels.set(key, channel)
  channel.onmessage = event => handleWireMessage(meetId, peerId, event.data)
  channel.onopen = () => {
    const queued = pendingByChannel.get(key) || []
    pendingByChannel.delete(key)
    if (queued.length) enqueueChunks(key, channel, queued)
    pumpSendQueue(key)
  }
  channel.onclose = () => {
    if (channels.get(key) === channel) channels.delete(key)
    pendingByChannel.delete(key)
    sendQueues.delete(key)
  }
  channel.bufferedAmountLowThreshold = 64 * 1024
  channel.onbufferedamountlow = () => pumpSendQueue(key)
  channel.onerror = (event) => {
    console.warn('[browserCollab] Data channel error', event)
  }
}

/** Remove and close the channel of a peer that left. */
export function closeCollabChannel(meetId, peerId) {
  const key = channelKey(meetId, peerId)
  const channel = channels.get(key)
  if (channel) {
    try { channel.close() } catch (e) { /* ignore */ }
    channels.delete(key)
  }
}

/**
 * Broadcast a collaboration message to every peer of a meeting and to the
 * other tabs of this browser.
 *
 * @param {string|null} meetId - Meeting id (null for local-tab only).
 * @param {Object} payload - `{ sessionId, kind, ... }`.
 */
export function broadcastBrowserCollab(meetId, payload) {
  if (!payload) return
  const message = {
    ...payload,
    scope: MESSAGE_SCOPE,
    v: 1,
    meetId: meetId || payload.meetId || null,
    clientId,
    sentAt: Date.now()
  }
  const serialized = JSON.stringify(message)
  const chunks = []
  if (serialized.length > CHUNK_SIZE) {
    const id = `${clientId}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`
    const total = Math.ceil(serialized.length / CHUNK_SIZE)
    for (let index = 0; index < total; index += 1) {
      chunks.push(JSON.stringify({
        scope: MESSAGE_SCOPE,
        v: 1,
        clientId,
        meetId: message.meetId,
        chunk: { id, index, total },
        data: serialized.slice(index * CHUNK_SIZE, (index + 1) * CHUNK_SIZE)
      }))
    }
  } else {
    chunks.push(serialized)
  }

  if (!meetId) {
    // Local-tab collaboration only: do not leak the message into a meeting the
    // user happens to be in with another panel open.
    if (localBroadcast) {
      chunks.forEach((chunk) => {
        try { localBroadcast.postMessage(chunk) } catch (e) { /* ignore */ }
      })
    }
    return
  }

  channels.forEach((channel, key) => {
    const channelMeet = key.split('::')[0]
    if (channelMeet !== meetId) return
    if (channel.readyState !== 'open') {
      // The meet mesh opens the channel asynchronously. Keep the last few
      // announcements so a session shared right after joining is not lost.
      const queue = pendingByChannel.get(key) || []
      if (queue.length < 100) {
        pendingByChannel.set(key, [...queue, ...chunks])
      }
      return
    }
    enqueueChunks(key, channel, chunks)
  })

  if (localBroadcast) {
    chunks.forEach((chunk) => {
      try { localBroadcast.postMessage(chunk) } catch (e) { /* ignore */ }
    })
  }
}

function enqueueChunks(key, channel, chunks) {
  if (!chunks?.length) return
  const state = sendQueues.get(key) || { channel, chunks: [] }
  state.channel = channel
  state.chunks.push(...chunks)
  sendQueues.set(key, state)
  pumpSendQueue(key)
}

function pumpSendQueue(key) {
  const state = sendQueues.get(key)
  if (!state) return
  const channel = state.channel
  if (!channel || channel.readyState !== 'open') return
  while (state.chunks.length && channel.bufferedAmount < 192 * 1024) {
    try {
      channel.send(state.chunks.shift())
    } catch (error) {
      console.warn('[browserCollab] Could not send annotation chunk', error)
      break
    }
  }
  if (!state.chunks.length) sendQueues.delete(key)
}

function handleWireMessage(meetId, peerId, raw) {
  let message = null
  try {
    message = typeof raw === 'string' ? JSON.parse(raw) : raw
  } catch (error) {
    return
  }
  if (!message || message.scope !== MESSAGE_SCOPE) return
  if (message.clientId === clientId) return

  if (message.chunk) {
    if (pendingChunks.size > 60) {
      const cutoff = Date.now() - 60 * 1000
      pendingChunks.forEach((pending, key) => {
        if (pending.createdAt < cutoff) pendingChunks.delete(key)
      })
    }
    const key = `${message.clientId}:${message.chunk.id}`
    const pending = pendingChunks.get(key) || {
      parts: new Array(message.chunk.total),
      total: message.chunk.total,
      received: 0,
      createdAt: Date.now()
    }
    if (pending.parts[message.chunk.index] === undefined) {
      pending.parts[message.chunk.index] = message.data
      pending.received += 1
    }
    pendingChunks.set(key, pending)
    if (pending.received < pending.total) return
    pendingChunks.delete(key)
    try {
      message = JSON.parse(pending.parts.join(''))
    } catch (error) {
      return
    }
  }

  // Chunks are small envelopes; the reassembled object carries the real scope.
  if (!message || message.scope !== MESSAGE_SCOPE || message.clientId === clientId) return
  const effectiveMeet = meetId || message.meetId || null
  notePresence(effectiveMeet, message)
  const event = { ...message, meetId: effectiveMeet, fromPeerId: peerId || null }
  listeners.forEach((listener) => {
    try {
      listener(event)
    } catch (error) {
      console.error('[browserCollab] Listener failed', error)
    }
  })
}

function notePresence(meetId, message) {
  if (!meetId || !message?.user) return
  if (!['presence', 'browser-session', 'annotation'].includes(message.kind)) return
  if (!participants.has(meetId)) participants.set(meetId, new Map())
  const meetParticipants = participants.get(meetId)
  meetParticipants.set(message.clientId, {
    clientId: message.clientId,
    user: message.user,
    sessionId: message.sessionId || null,
    kind: message.kind,
    lastSeen: Date.now()
  })
}

/** Subscribe to collaboration messages. Returns an unsubscribe function. */
export function onBrowserCollab(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/**
 * Participants recently seen in a meeting. Expired entries are removed lazily.
 *
 * @param {string} meetId
 * @returns {Array<{ clientId: string, user: Object, sessionId: string|null, lastSeen: number }>}
 */
export function getCollabParticipants(meetId) {
  if (!meetId || !participants.has(meetId)) return []
  const now = Date.now()
  const meetParticipants = participants.get(meetId)
  const alive = []
  meetParticipants.forEach((entry, key) => {
    if (now - entry.lastSeen > PRESENCE_TTL_MS) {
      meetParticipants.delete(key)
      return
    }
    alive.push(entry)
  })
  return alive.sort((a, b) => b.lastSeen - a.lastSeen)
}

/** Clear buffers for a meeting that ended. */
export function resetCollab(meetId) {
  if (meetId) {
    participants.delete(meetId)
    Array.from(channels.keys())
      .filter(key => key.startsWith(`${meetId}::`))
      .forEach((key) => {
        const channel = channels.get(key)
        if (channel) {
          try { channel.close() } catch (e) { /* ignore */ }
        }
        channels.delete(key)
      })
  } else {
    participants.clear()
    channels.forEach((channel) => {
      try { channel.close() } catch (e) { /* ignore */ }
    })
    channels.clear()
  }
  pendingChunks.clear()
  pendingByChannel.clear()
  sendQueues.clear()
}

/** Diagnostics used by the meet panel badge. */
export function getCollabChannelCount(meetId = null) {
  if (!meetId) return channels.size
  return Array.from(channels.keys()).filter(key => key.startsWith(`${meetId}::`)).length
}

export { MESSAGE_SCOPE }
