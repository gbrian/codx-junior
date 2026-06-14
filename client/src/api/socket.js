import io from 'socket.io-client'

/**
 * SocketManager handles all socket.io connection lifecycle,
 * event emission and reception on behalf of the API layer.
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
    })

    socket.on('connect', () => {
      console.log('[SocketManager] connected', socket.id)
      this._onConnect(socket.id)
    })

    socket.on('disconnect', () => {
      console.log('[SocketManager] disconnected')
      this._onDisconnect()
    })

    socket.io.on('reconnect', () => {
      console.log('[SocketManager] reconnected', socket.id)
      this._onConnect(socket.id)
    })

    socket.onAny((event, data) => {
      this._onEvent({ event, data })
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
    if (!this._socket) {
      console.warn('[SocketManager] emit called but socket is not connected')
      return
    }
    if (typeof ack === 'function') {
      this._socket.emit(event, data, ack)
    } else {
      this._socket.emit(event, data)
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