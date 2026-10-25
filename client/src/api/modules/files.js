import { CACHE_TTL, hashString, normalizePath } from '../requestCache'
import { QUEUE_NAMES } from '../requestQueue'

/**
 * Files API module
 * Handles file operations: list, read, search, upload, binary download/preview
 *
 * `read` and `diff` are the expensive calls of the editor / diff views: the
 * same file is usually requested several times in a row (viewer, diff panel,
 * chat preview, file list). Both declare their cache **at the transport call**
 * (`API.get/post(url, data, { key, ttl, queue })`), so they share the short-term
 * cache, the in-flight dedupe map and the request queue with every other caller:
 *
 *  - an identical `POST /api/files/diff` is served from the cache for a few
 *    seconds (the transport keys POSTs by a hash of its body),
 *  - a caller arriving while the request is running waits for it instead of
 *    starting a second one,
 *  - **different** reads and diffs are queued (`files:read` / `files:diff`, one
 *    at a time) with `750 ms` of silence between two consecutive calls, so a
 *    re-rendered diff panel cannot flood the network and the small requests of
 *    the app still go through while it loads,
 *  - `force: true` bypasses the entry for an explicit refresh.
 *
 * Keys are built from the **normalized** path: `./src/a.js`, `src/a.js` and
 * `src//a.js` are one file, so they share an entry — and a write through any of
 * those spellings invalidates all of them.
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

export const filesModule = (API) => ({
  list(path) {
    return API.get(`/api/files?path=${encodeURIComponent(path)}`)
  },

  /**
   * Read a text file.
   *
   * Cached for a few seconds, shared with every concurrent caller and queued
   * behind the `files:read` queue: only one read is on the wire at a time, with
   * `750 ms` of silence left before the next one.
   *
   * @param {string} path - Project relative path.
   * @param {Object} [options] - Cache options.
   * @param {boolean} [options.force] - Bypass the cache and refresh the entry.
   * @param {number} [options.ttl] - Override the cache TTL (ms).
   * @returns {Promise<Object>} `{ content, last_modification, size }`.
   *
   * @example
   * const { content } = await api.files.read('./src/main.js')
   * // Force a refresh after an external change:
   * await api.files.read('./src/main.js', { force: true })
   */
  read(path, { force = false, ttl = CACHE_TTL.fileRead } = {}) {
    return API.get(`/api/files/read?path=${encodeURIComponent(path)}`, {
      key: fileKey(API, 'files:read', path),
      ttl,
      force,
      queue: QUEUE_NAMES.fileRead
    })
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
   * This is a **POST**, and it is cached like a GET: the transport keys it by
   * the hash of its body, so re-rendering the same editor state never asks the
   * backend again, and a second caller arriving while the request is running
   * waits for that same request instead of sending another one.
   *
   * Different diffs are **queued** (`files:diff`, one at a time) with `750 ms` of
   * silence after each one: while a diff is on the wire the next one waits, and
   * during the gap the connection is free for the lighter requests of the app.
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
   * const { diff } = await api.files.diff({ path, content })
   * // Same content asked twice in a second → one request.
   * await Promise.all([1, 2].map(() => api.files.diff({ path, content })))
   */
  diff({ path, content, from_branch, to_branch, force = false } = {}) {
    return API.post(`/api/files/diff`, {
      path,
      content,
      from_branch: from_branch || null,
      to_branch: to_branch || null
    }, {
      key: fileKey(
        API,
        'files:diff',
        path,
        from_branch || '',
        to_branch || '',
        hashString(content)
      ),
      ttl: CACHE_TTL.fileDiff,
      force,
      queue: QUEUE_NAMES.fileDiff
    })
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
  }
})