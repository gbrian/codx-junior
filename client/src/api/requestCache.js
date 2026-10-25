/**
 * Short-term request cache with in-flight sharing and subscribers.
 *
 * Two problems it solves for the expensive file / diff endpoints:
 *
 *  1. **Repeated calls.** The same file is read by the editor, the diff panel,
 *     the chat preview and the file list within the same second. File reads and
 *     diffs are expensive on the backend, so identical calls are served from a
 *     very short-lived cache (a couple of seconds).
 *
 *  2. **Parallel calls.** When a key is requested again while the first request
 *     is still running, the new caller does not start another request: it
 *     subscribes to the in-flight promise and receives the very same result.
 *
 * Different keys are not limited here: the HTTP layer queues whole categories of
 * request (`requestQueue.js`) so only one diff / one read is on the wire at a
 * time. The two modules cooperate — the queue sits *behind* this cache, so a hit
 * never waits for a turn.
 *
 * Requests are identified by a **hash of their body** (`hashBody`), never by the
 * body itself: a diff carries the whole file content and keeping (or comparing)
 * that string on every call is exactly what the cache must avoid. Bodies that
 * cannot be serialized (`FormData`, `Blob`, `ArrayBuffer`) are never cached nor
 * deduplicated — two uploads are two different requests even if they look alike.
 *
 * Paths are normalized (`normalizePath`) before being used inside a key, so
 * `./src/a.js`, `src/a.js` and `src//a.js` share one entry — and an invalidation
 * triggered by one of them clears all of them.
 *
 * Subscribers (`subscribe`) are notified when an entry is refreshed or
 * invalidated, which is what lets a view drop its own copy of a file after a
 * write without polling.
 *
 * Values are cached **by reference**: treat them as read-only.
 *
 * @example
 * const cache = new RequestCache({ ttl: 3000 })
 * const key = 'files:read|/path/to/project|src/main.js|'
 *
 * // Three concurrent callers → one HTTP request.
 * await Promise.all([1, 2, 3].map(() => cache.run(key, () => readFile())))
 *
 * // A write invalidates the entry and notifies its subscribers.
 * cache.invalidate(key)
 */

/** Default cache lifetime, in milliseconds. */
const DEFAULT_TTL = 3000

/** Maximum cached entries kept before the oldest ones are evicted. */
const DEFAULT_MAX_ENTRIES = 300

/**
 * Recommended lifetimes for the expensive endpoints.
 */
export const CACHE_TTL = {
  /** `GET /api/files/read` — text content of a file. */
  fileRead: 3000,
  /** `POST /api/files/diff` and `GET /api/git/repo/file/diff`. */
  fileDiff: 4000,
  /** `GET /api/git/repo/commit/detail` — a commit never changes once created. */
  commitDetail: 30000
}

/**
 * Fast, stable hash used to key long payloads (the diffed file contents).
 *
 * @param {string} value - Text to hash.
 * @returns {string} Base 36 hash.
 */
export function hashString(value) {
  const text = value === undefined || value === null ? '' : String(value)
  let hash = 0
  for (let index = 0; index < text.length; index++) {
    hash = (hash << 5) - hash + text.charCodeAt(index)
    hash |= 0
  }
  return (hash >>> 0).toString(36)
}

/**
 * Serialize a request body into a stable string, or `null` when the body is not
 * cacheable.
 *
 * Binary bodies (uploads, image-to-text) cannot be compared by content: giving
 * them a shared key would make two different uploads look like one request.
 *
 * @param {*} data - Request body.
 * @returns {string|null} Serialized body, or `null` when it must stay unique.
 */
export function serializeBody(data) {
  if (data === undefined || data === null) return ''
  if (typeof data === 'string') return data
  if (typeof data === 'number' || typeof data === 'boolean') return String(data)
  if (typeof FormData !== 'undefined' && data instanceof FormData) return null
  if (typeof Blob !== 'undefined' && data instanceof Blob) return null
  if (typeof ArrayBuffer !== 'undefined') {
    if (data instanceof ArrayBuffer || ArrayBuffer.isView(data)) return null
  }
  if (typeof data === 'object') {
    try {
      return JSON.stringify(data)
    } catch (ex) {
      return null
    }
  }
  return String(data)
}

/**
 * Hash of a request body, used as the identity of a POST.
 *
 * @param {*} data - Request body.
 * @returns {string|null} Body hash, or `null` when the body must not be shared.
 *
 * @example
 * hashBody({ path: 'src/a.js', content: '...' }) // => '1f3k9z'
 */
export function hashBody(data) {
  const body = serializeBody(data)
  return body === null ? null : hashString(body)
}

/**
 * Normalize a file path so every spelling of the same file shares one key:
 * `./src/a.js`, `src/a.js`, `src//a.js` and `src\a.js` all become `src/a.js`.
 *
 * A leading `/` (absolute repository path, used by the PR views) is preserved.
 *
 * @param {string} value - Path to normalize.
 * @returns {string} Normalized path (`''` for empty input).
 *
 * @example
 * normalizePath('./src//main.js') // => 'src/main.js'
 */
export function normalizePath(value) {
  if (value === undefined || value === null) return ''
  let path = String(value).trim().replace(/\\/g, '/')
  path = path.replace(/^(?:\.\/)+/, '')
  path = path.replace(/\/{2,}/g, '/')
  while (path.length > 1 && path.endsWith('/')) path = path.slice(0, -1)
  return path
}

export class RequestCache {
  /**
   * @param {Object} [options] - Options.
   * @param {number} [options.ttl] - Default lifetime in milliseconds.
   * @param {number} [options.maxEntries] - Maximum number of cached entries.
   * @param {Function} [options.now] - Clock, injectable for tests.
   */
  constructor({ ttl = DEFAULT_TTL, maxEntries = DEFAULT_MAX_ENTRIES, now = () => Date.now() } = {}) {
    this.ttl = ttl
    this.maxEntries = maxEntries
    this.now = now
    /** Resolved values: key -> { value, expiresAt }. */
    this._entries = new Map()
    /** In-flight requests: key -> promise. */
    this._pending = new Map()
    /** Subscribers: key (or '*') -> Set<Function>. */
    this._subscribers = new Map()
    /** Bumped on every invalidation; see `run`. */
    this._revision = 0
    /** Hit / miss counters, handy while tuning the TTLs. */
    this.stats = { hits: 0, joins: 0, misses: 0, writes: 0, invalidations: 0 }
  }

  /** Number of cached entries. */
  get size() {
    return this._entries.size
  }

  /** Number of requests currently on the wire for a cached key. */
  get pending() {
    return this._pending.size
  }

  // ── Entries ───────────────────────────────────────────────────────────────

  /**
   * Read a cached value without touching the pending requests.
   *
   * @param {string} key - Cache key.
   * @returns {*} The cached value or `undefined` when missing / expired.
   */
  peek(key) {
    const entry = this._entries.get(key)
    if (!entry) return undefined
    if (entry.expiresAt <= this.now()) {
      this._entries.delete(key)
      return undefined
    }
    return entry.value
  }

  /**
   * @param {string} key - Cache key.
   * @returns {boolean} `true` when a fresh value is cached.
   */
  has(key) {
    return this.peek(key) !== undefined
  }

  /**
   * Store a value and notify the subscribers of `key`.
   *
   * @param {string} key - Cache key.
   * @param {*} value - Value; `undefined` is never cached.
   * @param {Object} [options] - Options.
   * @param {number} [options.ttl] - Override the lifetime for this entry.
   * @returns {*} The stored value.
   */
  set(key, value, { ttl } = {}) {
    if (value === undefined) return value
    // Delete first so Map insertion order stays equal to recency order (eviction).
    this._entries.delete(key)
    this._entries.set(key, {
      value,
      expiresAt: this.now() + (ttl === undefined ? this.ttl : ttl)
    })
    this.stats.writes++
    this._evict()
    this._notify(key, { key, value, event: 'update' })
    return value
  }

  // ── Execution ─────────────────────────────────────────────────────────────

  /**
   * Resolve `key` from the cache, join the running request or execute
   * `requestFn`. This is the single entry point every cached call must use.
   *
   * A request may wait in a queue (`requestQueue.js`) or on the wire for a while;
   * when an invalidation happens during that time the value is still delivered to
   * the callers but it is **not** cached, because it may already be out of date.
   *
   * @param {string} key - Cache key.
   * @param {Function} requestFn - Factory returning the request promise.
   * @param {Object} [options] - Options.
   * @param {number} [options.ttl] - Lifetime of the new entry.
   * @param {boolean} [options.force] - Bypass the cache and refresh the entry.
   * @returns {Promise<*>} The cached, shared or freshly fetched value.
   *
   * @example
   * const file = await cache.run(key, () => API.get(url), { ttl: 3000 })
   */
  run(key, requestFn, { ttl, force = false } = {}) {
    if (!force) {
      const cached = this.peek(key)
      if (cached !== undefined) {
        this.stats.hits++
        return Promise.resolve(cached)
      }
      const running = this._pending.get(key)
      if (running) {
        // Subscriber: wait for the request already on the wire.
        this.stats.joins++
        return running
      }
    }

    this.stats.misses++
    const revision = this._revision
    const promise = Promise.resolve()
      .then(requestFn)
      .then((value) => {
        // A mutation invalidated the cache while this request was waiting: keep
        // the answer for the callers, but do not cache a possibly stale value.
        if (this._revision === revision) this.set(key, value, { ttl })
        return value
      })
      .finally(() => {
        if (this._pending.get(key) === promise) this._pending.delete(key)
      })

    this._pending.set(key, promise)
    // Never let a rejection surface as "unhandled" for late subscribers.
    // The returned promise still rejects for the caller.
    promise.catch(() => {})
    return promise
  }

  // ── Invalidation ──────────────────────────────────────────────────────────

  /**
   * Drop cached entries and notify their subscribers.
   *
   * The matcher can be:
   *  - an exact key (`'files:read|<scope>|src/main.js|'`),
   *  - a key prefix (`'files:diff|<scope>|'`) — keys always end on a separator,
   *  - a RegExp,
   *  - a predicate `(key) => boolean`,
   *  - `'*'` / nothing for everything.
   *
   * @param {string|RegExp|Function} matcher - What to invalidate.
   * @returns {string[]} Removed keys.
   *
   * @example
   * cache.invalidate('files:read|/project|src/main.js|')
   * cache.invalidate((key) => key.includes('|src/main.js|'))
   */
  invalidate(matcher) {
    if (matcher === undefined || matcher === null || matcher === '*') {
      return this.invalidateAll()
    }
    const matches = this._matcher(matcher)
    const removed = []
    this._entries.forEach((entry, key) => {
      if (matches(key)) removed.push({ key, value: entry.value })
    })
    if (removed.length) this._revision++
    removed.forEach(({ key, value }) => {
      this._entries.delete(key)
      this.stats.invalidations++
      this._notify(key, { key, value, event: 'invalidate' })
    })
    return removed.map(({ key }) => key)
  }

  /**
   * Drop every cached entry.
   *
   * @returns {string[]} Removed keys.
   */
  invalidateAll() {
    return this.clear()
  }

  /**
   * Drop every cached entry (alias of `invalidateAll`).
   *
   * @returns {string[]} Removed keys.
   */
  clear() {
    const removed = []
    this._entries.forEach((entry, key) => removed.push({ key, value: entry.value }))
    this._entries.clear()
    this._revision++
    removed.forEach(({ key, value }) => {
      this._notify(key, { key, value, event: 'invalidate' })
    })
    return removed.map(({ key }) => key)
  }

  /**
   * Drop the entries whose lifetime already expired.
   *
   * @returns {RequestCache} This instance.
   */
  prune() {
    const now = this.now()
    this._entries.forEach((entry, key) => {
      if (entry.expiresAt <= now) this._entries.delete(key)
    })
    return this
  }

  // ── Subscribers ───────────────────────────────────────────────────────────

  /**
   * Subscribe to the updates of `key` (`'*'` receives every key).
   *
   * @param {string} key - Cache key or `'*'`.
   * @param {Function} handler - Receives `{ key, value, event }`.
   * @returns {Function} Unsubscribe function.
   *
   * @example
   * const off = API.onCacheUpdate(API.cacheKey('files:read', path), ({ event }) => {
   *   if (event === 'invalidate') this.reload()
   * })
   * // later: off()
   */
  subscribe(key, handler) {
    if (typeof handler !== 'function') return () => {}
    if (!this._subscribers.has(key)) this._subscribers.set(key, new Set())
    this._subscribers.get(key).add(handler)
    return () => this.unsubscribe(key, handler)
  }

  /**
   * @param {string} key - Cache key or `'*'`.
   * @param {Function} handler - Handler to remove.
   */
  unsubscribe(key, handler) {
    const handlers = this._subscribers.get(key)
    if (!handlers) return
    handlers.delete(handler)
    if (!handlers.size) this._subscribers.delete(key)
  }

  /**
   * Broadcast a custom payload to the subscribers of `key`.
   *
   * @param {string} key - Cache key or `'*'`.
   * @param {Object} [payload] - Extra payload fields.
   */
  notify(key, payload = {}) {
    this._notify(key, { key, ...payload })
  }

  // ── Internals ─────────────────────────────────────────────────────────────

  /**
   * Normalize a matcher into a `(key) => boolean` predicate.
   *
   * @param {string|RegExp|Function} matcher - Matcher.
   * @returns {Function} Predicate.
   */
  _matcher(matcher) {
    if (typeof matcher === 'function') return matcher
    if (matcher instanceof RegExp) return (key) => matcher.test(key)
    const value = String(matcher)
    // Keys look like `kind|scope|...|`, so a prefix always ends on a separator.
    return (key) => key === value || key.startsWith(value)
  }

  /** Evict the oldest entries when the store grows too large. */
  _evict() {
    while (this._entries.size > this.maxEntries) {
      const oldest = this._entries.keys().next().value
      this._entries.delete(oldest)
    }
  }

  /**
   * Notify the exact key subscribers and the wildcard ones.
   *
   * @param {string} key - Cache key.
   * @param {Object} payload - `{ key, value, event }`.
   */
  _notify(key, payload) {
    const handlers = new Set([
      ...(this._subscribers.get(key) || []),
      ...(this._subscribers.get('*') || [])
    ])
    handlers.forEach((handler) => {
      try {
        handler(payload)
      } catch (ex) {
        console.error('[requestCache] subscriber error', key, ex)
      }
    })
  }
}

export default RequestCache