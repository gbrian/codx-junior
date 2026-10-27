import { CACHE_TTL, hashString, normalizePath } from '../requestCache'
import { QUEUE_NAMES } from '../requestQueue'

/**
 * Files API module
 * Handles file operations: list, read, search, upload, binary download/preview
 *
 * ## `read` and `diff` go over HTTP
 *
 * `GET /api/files/read` and `POST /api/files/diff` are the expensive calls of the
 * editor / diff views. They are plain HTTP requests and stay that way: the
 * Socket.IO variant (`codx-junior-file-read` / `codx-junior-file-diff`) was
 * tried and measured slower, because the answer has to be broadcast and matched
 * by `request_id` instead of being returned to the caller.
 *
 * What keeps them cheap is the layer around the request, not the transport:
 *
 *  - an identical `read` / `diff` is served from the short-term cache for a few
 *    seconds (a diff is keyed by a hash of its content),
 *  - a caller arriving while the same request is running waits for it instead of
 *    starting a second one,
 *  - **different** reads and diffs are queued (`files:read` / `files:diff`, one
 *    at a time) so a re-rendered diff panel cannot flood the backend,
 *  - `force: true` bypasses the entry for an explicit refresh.
 *
 * Keys are built from the **normalized** path: `./src/a.js`, `src/a.js` and
 * `src//a.js` are one file, so they share an entry — and a write through any of
 * those spellings invalidates all of them.
 *
 * @example
 * const { content } = await api.files.read('./src/main.js', { force: true })
 * const { diff, stats } = await api.files.diff({ path, content })
 */

/**
 * Build the cache key of a file entry.
 *
 * @param {Object} API - API instance.
 * @param {string} kind - Entry family (`files:read`, `files:diff`).
 * @param {string} path - Project relative (or absolute) path.
 * @param {...string} parts - Extra key parts.
 * @returns {string} Cache key.
 */
function fileKey(API, kind, path, ...parts) {
  return API.cacheKey(kind, normalizePath(path), ...parts)
}

/**
 * Invalidate every cached entry of a file (content and diffs).
 *
 * Matches on the `|path|` segment of the key, so all the families of that path
 * (`files:read`, `files:diff` with any branch/content hash) are dropped at once.
 *
 * @param {Object} API - API instance.
 * @param {string} path - Project relative path.
 */
function invalidatePath(API, path) {
  if (!path) return
  const segment = `|${normalizePath(path)}|`
  API.invalidateCache((key) => key.includes(segment))
}

/**
 * File name (last path segment) of a path.
 *
 * @param {string} path - Project relative (or absolute) path.
 * @returns {string} Base name.
 */
function baseName(path) {
  return normalizePath(path).split('/').filter(Boolean).pop() || ''
}

export const filesModule = (API) => ({
  list(path) {
    return API.get(`/api/files?path=${encodeURIComponent(path)}`)
  },

  /**
   * Read a text file.
   *
   * `GET /api/files/read`, cached for a few seconds, shared with every
   * concurrent caller and queued behind the `files:read` queue: only one read is
   * on the wire at a time.
   *
   * @param {string} path - Project relative path.
   * @param {Object} [options] - Options.
   * @param {boolean} [options.force] - Bypass the cache and refresh the entry.
   * @param {number} [options.ttl] - Override the cache TTL (ms).
   * @returns {Promise<Object>} `{ content, is_binary, last_modification, size }`.
   *
   * @example
   * const { content } = await api.files.read('./src/main.js')
   * // Force a refresh after an external change:
   * await api.files.read('./src/main.js', { force: true })
   */
  read(path, { force = false, ttl = CACHE_TTL.fileRead } = {}) {
    return API.cached(
      fileKey(API, 'files:read', path),
      () => API.queues.run(
        QUEUE_NAMES.fileRead,
        () => API.get(`/api/files/read?path=${encodeURIComponent(path)}`)
      ),
      { ttl, force }
    )
  },

  readBinary(path) {
    return API.get(`/api/files/read?path=${encodeURIComponent(path)}&binary=true`, {
      responseType: 'arraybuffer'
    })
  },

  // Direct (streaming) URL to view a binary file's raw content inline.
  // Same-origin relative URL, safe to use as <iframe>/<img>/<video> src.
  getFilePreviewUrl(path) {
    return API.connection.prepareUrl("/api/files/download?path=" + encodeURIComponent(path) + "&inline=true")
  },

  // Direct URL to download a binary file's raw content as an attachment.
  // Pair with the anchor `download` attribute to force a save.
  getFileDownloadUrl(path) {
    return API.connection.prepareUrl("/api/files/download?path=" + encodeURIComponent(path))
  },

  search({ search, searchPath, page = 0, pageSize = 50, rawSearch = false, useRegex = false }) {
    const params = new URLSearchParams()
    params.append('search', search)
    if (searchPath) {
      params.append('search_path', searchPath)
    }
    params.append('page', page)
    params.append('page_size', pageSize)
    params.append('raw_search', rawSearch)
    params.append('use_regex', useRegex)
    return API.get(`/api/files/search?${params.toString()}`)
  },

  searchContent({ query, searchPath, page = 0, pageSize = 50, caseSensitive = false, rawSearch = false, useRegex = false }) {
    const params = new URLSearchParams()
    params.append('q', query)
    if (searchPath) {
      params.append('search_path', searchPath)
    }
    params.append('page', page)
    params.append('page_size', pageSize)
    params.append('case_sensitive', caseSensitive)
    params.append('raw_search', rawSearch)
    params.append('use_regex', useRegex)
    return API.get(`/api/files/search-content?${params.toString()}`)
  },

  upload(file, path, process = false) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('path', path || '')
    formData.append('process', process ? 'true' : 'false')
    return API.post(`/api/files/upload`, formData)
  },

  uploadMultiple(files, process = false) {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append('files', file)
    })
    formData.append('process', process ? 'true' : 'false')
    return API.post(`/api/files/upload-multiple`, formData)
  },

  /**
   * Diff of the given content against the file's current (or branch) version.
   *
   * `POST /api/files/diff`, cached by a hash of its body: re-rendering the same
   * editor state never asks the backend again and a second caller arriving while
   * the request is running waits for that same request. Different diffs are
   * **queued** (`files:diff`, one at a time) so the expensive calls do not fight
   * with the lighter requests of the app.
   *
   * @param {Object} params - Diff parameters.
   * @param {string} params.path - Project relative path.
   * @param {string} [params.content] - Content to compare.
   * @param {string} [params.from_branch] - Source branch.
   * @param {string} [params.to_branch] - Target branch.
   * @param {boolean} [params.force] - Bypass the cache and refresh the entry.
   * @returns {Promise<Object>} `{ diff, stats, last_modification, size }`.
   *
   * @example
   * const { diff, stats } = await api.files.diff({ path, content })
   * // Same content asked twice in a second → one request.
   * await Promise.all([1, 2].map(() => api.files.diff({ path, content })))
   */
  diff({ path, content, from_branch, to_branch, force = false } = {}) {
    const body = {
      path,
      content,
      from_branch: from_branch || null,
      to_branch: to_branch || null
    }

    return API.cached(
      fileKey(
        API,
        'files:diff',
        path,
        from_branch || '',
        to_branch || '',
        hashString(content)
      ),
      () => API.queues.run(
        QUEUE_NAMES.fileDiff,
        () => API.post(`/api/files/diff`, body)
      ),
      { ttl: CACHE_TTL.fileDiff, force }
    )
  },

  write(source, page_content) {
    return API.post(`/api/files/write?path=${encodeURIComponent(source)}`, { page_content, metadata: { source } })
      .then((result) => {
        invalidatePath(API, source)
        return result
      })
  },

  // Persist several editors in a single round-trip.
  // `files` = [{ path, content }] — only dirty files should be sent.
  // Mirrors `uploadMultiple` naming so the two bulk endpoints stay symmetrical.
  writeMultiple(files) {
    return API.post(`/api/files/write-multiple`, {
      files: files.map(({ path, content }) => ({ path, content }))
    }).then((result) => {
      files.forEach(({ path }) => invalidatePath(API, path))
      return result
    })
  },

  reset(source) {
    return API.get(`/api/files/reset?path=${encodeURIComponent(source)}`)
      .then((result) => {
        invalidatePath(API, source)
        return result
      })
  },

  rollback(path) {
    return API.get(`/api/files/reset?path=${encodeURIComponent(path)}`)
      .then((result) => {
        invalidatePath(API, path)
        return result
      })
  },

  create(path, isDir = false) {
    return API.post(`/api/files/create`, { path, is_dir: isDir })
      .then((result) => {
        invalidatePath(API, path)
        return result
      })
  },

  delete(path) {
    return API.post(`/api/files/delete`, { path })
      .then((result) => {
        invalidatePath(API, path)
        return result
      })
  },

  rename(oldPath, newPath) {
    return API.post(`/api/files/rename`, { old_path: oldPath, new_path: newPath })
      .then((result) => {
        invalidatePath(API, oldPath)
        invalidatePath(API, newPath)
        return result
      })
  },

  /**
   * Move one or several files/folders into a target directory.
   *
   * A move is the same filesystem operation as a rename whose new path lives in
   * another folder, so it is performed through `POST /api/files/rename` — no
   * extra endpoint is needed and every moved path inherits that call's cache
   * invalidation (source **and** destination).
   *
   * Callers are expected to filter out no-op moves (already in `targetDir`) and
   * moves of a folder into itself; `rename` would otherwise fail on the backend.
   *
   * @param {string|string[]} paths - Source path(s) (project relative or absolute).
   * @param {string} targetDir - Destination folder.
   * @returns {Promise<Array>} Result of each rename.
   *
   * @example
   * await api.files.move(['/src/a.js', '/src/b.js'], '/lib')
   * await api.files.move('/src/a.js', '/')   // back to the project root
   */
  move(paths, targetDir) {
    const sources = (Array.isArray(paths) ? paths : [paths]).filter(Boolean)
    const directory = normalizePath(targetDir) || '/'
    return Promise.all(sources.map((source) => {
      const destination = normalizePath(`${directory}/${baseName(source)}`)
      return API.post(`/api/files/rename`, { old_path: source, new_path: destination })
        .then((result) => {
          invalidatePath(API, source)
          invalidatePath(API, destination)
          return result
        })
    }))
  }
})