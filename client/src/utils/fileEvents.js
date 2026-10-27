/**
 * File events published by the backend over the socket.
 *
 * A file event looks like:
 *
 * ```json
 * {
 *   "type": "loaded",
 *   "file_path": "/home/me/project/src/main.js",
 *   "codx_path": "/home/me/project/.codx",
 *   "ts": 1793118344
 * }
 * ```
 *
 * The socket event **name** is not part of the contract: the payload is what
 * identifies a file event (`file_path` + a known `type`), so a new event name on
 * the server keeps working with the same client code.
 *
 * Views (the file explorer today) subscribe with `onFileEvent` instead of
 * parsing socket payloads themselves, so detection and path rules live here.
 */

/**
 * Event types that make a directory listing / a file content stale.
 *
 * Read types (`loaded`, `read`, `opened`) are included on purpose: the backend
 * uses them as well to announce that a file changed on disk (a chat or the
 * terminal just wrote it), and it is the only signal some changes produce.
 */
export const FILE_EVENT_TYPES = [
  // content read / reloaded from disk
  'loaded', 'read', 'opened', 'reloaded',
  // content changed
  'saved', 'written', 'updated', 'changed', 'modified', 'edited', 'uploaded',
  // directory entries changed
  'created', 'added', 'deleted', 'removed', 'truncated', 'renamed', 'moved'
]

/** Events after which the path no longer exists. */
export const DELETED_FILE_EVENT_TYPES = ['deleted', 'removed']

/**
 * Normalize a path so two spellings of the same folder compare equal:
 * `src//a.js/` → `src/a.js`.
 *
 * @param {string} path - Path to normalize.
 * @returns {string|null} Normalized path (null when empty).
 */
export function normalizeFilePath(path) {
  if (!path) return null
  return String(path).replace(/\/+/g, '/').replace(/(.)\/$/, '$1')
}

/**
 * Folder that contains the given path.
 *
 * @param {string} path - File or folder path.
 * @returns {string|null} Parent directory.
 *
 * @example
 * parentDirectory('/p/src/a.js') // => '/p/src'
 * parentDirectory('/p')          // => '/'
 */
export function parentDirectory(path) {
  const normalized = normalizeFilePath(path)
  if (!normalized) return null
  const index = normalized.lastIndexOf('/')
  if (index < 0) return null
  return index === 0 ? '/' : normalized.slice(0, index)
}

/**
 * True when a socket message is a file event.
 *
 * Detection is payload based: a `file_path` (or `path`) plus a known `type`.
 * When the type is unknown the socket event name is used as a last resort, so
 * an event named after files (`codx-junior-file-...`) is still accepted.
 *
 * @param {string} event - Socket event name.
 * @param {*} data - Socket payload.
 * @returns {boolean}
 */
export function isFileEvent(event, data) {
  if (!data || typeof data !== 'object') return false
  if (!data.file_path && !data.path) return false
  const type = String(data.type || '').toLowerCase()
  if (FILE_EVENT_TYPES.includes(type)) return true
  return String(event || '').toLowerCase().includes('file')
}

/**
 * Build the client representation of a file event.
 *
 * Renames and moves may announce the destination and/or the source under
 * different keys depending on the emitter, all of them are collected.
 *
 * @param {string} event - Socket event name.
 * @param {Object} data - Socket payload.
 * @returns {Object} Normalized file event.
 */
export function normalizeFileEvent(event, data) {
  const type = String(data?.type || 'changed').toLowerCase()
  const filePath = normalizeFilePath(data?.file_path || data?.path)
  return {
    event,
    type,
    filePath,
    // Destination of a rename / move, when the backend sends it
    newPath: normalizeFilePath(data?.new_path || data?.to_path || data?.destination_path),
    // Source of a rename / move, when the destination is the `file_path`
    previousPath: normalizeFilePath(data?.old_path || data?.from_path || data?.source_path),
    codxPath: data?.codx_path || null,
    project: data?.project || null,
    projectId: data?.project?.project_id || data?.project_id || null,
    ts: data?.ts || null,
    isDelete: DELETED_FILE_EVENT_TYPES.includes(type),
    raw: data
  }
}

/**
 * Folders whose listing is stale because of a file event (the folders holding
 * the file before and after a rename / move).
 *
 * @param {Object} fileEvent - Normalized file event.
 * @returns {string[]} Directory paths.
 */
export function affectedDirectories(fileEvent) {
  const paths = [fileEvent.filePath, fileEvent.newPath, fileEvent.previousPath]
    .filter(Boolean)
  return [...new Set(paths.map(parentDirectory).filter(Boolean))]
}

/**
 * True when the listing of `directory` must be reloaded.
 *
 * A change deeper in the tree never affects the folder on screen: only the
 * parent folder of the changed path (and the path itself, when it is the folder
 * being displayed) counts.
 *
 * @param {string} directory - Folder currently listed.
 * @param {Object} fileEvent - Normalized file event.
 * @returns {boolean}
 *
 * @example
 * isDirectoryAffected('/p/src', { filePath: '/p/src/a.js' })  // => true
 * isDirectoryAffected('/p/src', { filePath: '/p/src/x/a.js' }) // => false
 */
export function isDirectoryAffected(directory, fileEvent) {
  const normalized = normalizeFilePath(directory)
  if (!normalized || !fileEvent) return false
  const self = [fileEvent.filePath, fileEvent.newPath, fileEvent.previousPath]
  if (self.includes(normalized)) return true
  return affectedDirectories(fileEvent).includes(normalized)
}

const listeners = new Set()

/**
 * Subscribe to backend file events.
 *
 * @param {Function} listener - Receives the normalized file event.
 * @returns {Function} Unsubscribe function.
 *
 * @example
 * const off = onFileEvent(evt => console.log(evt.type, evt.filePath))
 * // later
 * off()
 */
export function onFileEvent(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/**
 * Remove a previously registered listener.
 *
 * @param {Function} listener - Listener to remove.
 */
export function offFileEvent(listener) {
  listeners.delete(listener)
}

/**
 * Deliver a file event to every subscriber. A failing listener never prevents
 * the others from receiving the event.
 *
 * @param {Object} fileEvent - Normalized file event.
 */
export function emitFileEvent(fileEvent) {
  listeners.forEach((listener) => {
    try {
      listener(fileEvent)
    } catch (ex) {
      console.error('[fileEvents] Listener failed', ex)
    }
  })
}

/**
 * Detect, normalize and publish a socket message when it is a file event.
 * Called by the session store for every message received from the server.
 *
 * @param {string} event - Socket event name.
 * @param {*} data - Socket payload.
 * @returns {Object|null} The published file event, or null.
 */
export function publishFileEvent(event, data) {
  if (!isFileEvent(event, data)) return null
  const fileEvent = normalizeFileEvent(event, data)
  emitFileEvent(fileEvent)
  return fileEvent
}