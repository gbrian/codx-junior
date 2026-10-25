import io from 'socket.io-client'
import {
  recordSocketEvent,
  payloadSize,
  setSocketConnected
} from './telemetry'

/**
 * SocketManager handles all socket.io connection lifecycle,
 * event emission and reception on behalf of the API layer.
 *
 * Every lifecycle change and every event that crosses the wire is also written
 * to the client telemetry ring buffer (`./telemetry`) — that is what
 * API monitoring → "Socket events" renders. Only the event name, the payload
 * size and the timings are kept; payloads are never copied.
 */
export class SocketManager {
  constructor({ onEvent, onConnect, onDisconnect } = {}) {
    this._socket = null
    this._onEvent = onEvent || (() => {})
    this._onConnect = onConnect || (() => {})
    this._onDisconnect = onDisconnect || (() => {})
    this._listeners = new Map()
  }

  get id() {
    return this._socket?.id || null
  }

  get connected() {
    return this._socket?.connected || false
  }

  get socket() {
    return this._socket
  }

  /**
   * Connect to the socket.io server.
   * If a socket already exists it will be closed first.
   */
  connect() {
    if (this._socket) {
      this._socket.close()
      this._socket = null
    }

    const socket = io({
      path: '/api/socket.io',
      reconnectionDelayMax: 5000,
      transports: ['websocket']
    })

    socket.on('connect_error', (err) => {
      console.warn('[SocketManager] connect_error:', err.message)
      recordSocketEvent({
        event: 'connect_error',
        direction: 'system',
        error: err?.message || 'connect_error',
        socketId: socket.id
      })
    })

    socket.on('connect', () => {
      console.log('[SocketManager] connected', socket.id)
      setSocketConnected(true, socket.id)
      recordSocketEvent({
        event: 'connect',
        direction: 'system',
        detail: socket.io?.engine?.transport?.name || null,
        socketId: socket.id
      })
      this._onConnect(socket.id)
    })

    socket.on('disconnect', (reason) => {
      console.log('[SocketManager] disconnected')
      setSocketConnected(false)
      recordSocketEvent({
        event: 'disconnect',
        direction: 'system',
        detail: reason || null,
        socketId: socket.id
      })
      this._onDisconnect()
    })

    socket.io.on('reconnect', (attempt) => {
      console.log('[SocketManager] reconnected', socket.id)
      setSocketConnected(true, socket.id)
      recordSocketEvent({
        event: 'reconnect',
        direction: 'system',
        detail: attempt ? `attempt ${attempt}` : null,
        socketId: socket.id
      })
      this._onConnect(socket.id)
    })

    socket.onAny((event, ...args) => {
      // Size of the whole argument list: the server may send more than one.
      recordSocketEvent({
        event,
        direction: 'in',
        size: payloadSize(args),
        socketId: socket.id
      })
      this._onEvent({ event, data: args[0] })
    })

    // Re-attach any named listeners registered before connect
    this._listeners.forEach((handler, event) => {
      socket.on(event, handler)
    })

    this._socket = socket
    return this
  }

  /**
   * Disconnect and destroy the current socket.
   */
  disconnect() {
    if (this._socket) {
      recordSocketEvent({
        event: 'close',
        direction: 'system',
        socketId: this._socket.id
      })
      setSocketConnected(false)
      this._socket.close()
      this._socket = null
    }
  }

  /**
   * Emit an event with optional data and an optional ack callback.
   * @param {string} event
   * @param {*} data
   * @param {Function} [ack]
   */
  emit(event, data, ack) {
    const socket = this._socket

    if (!socket) {
      console.warn('[SocketManager] emit called but socket is not connected')
      recordSocketEvent({
        event,
        direction: 'out',
        size: payloadSize(data),
        error: 'socket not connected'
      })
      return
    }

    if (typeof ack === 'function') {
      // The ack round trip is the only per-event latency this side can measure:
      // record it so a slow handler shows up in the socket table.
      const startedAt = typeof performance !== 'undefined' ? performance.now() : Date.now()
      socket.emit(event, data, (...ackArgs) => {
        const elapsed = (typeof performance !== 'undefined' ? performance.now() : Date.now()) - startedAt
        recordSocketEvent({
          event,
          direction: 'out',
          size: payloadSize(data),
          durationMs: elapsed,
          error: ackArgs[0]?.error || null,
          socketId: socket.id
        })
        ack(...ackArgs)
      })
    } else {
      recordSocketEvent({
        event,
        direction: 'out',
        size: payloadSize(data),
        socketId: socket.id
      })
      socket.emit(event, data)
    }
  }

  /**
   * Register a named event listener.
   * Persists across reconnects.
   * @param {string} event
   * @param {Function} handler
   */
  on(event, handler) {
    this._listeners.set(event, handler)
    if (this._socket) {
      this._socket.on(event, handler)
    }
  }

  /**
   * Remove a named event listener.
   * @param {string} event
   */
  off(event) {
    this._listeners.delete(event)
    if (this._socket) {
      this._socket.off(event)
    }
  }
}