/**
 * Request queue: a hard concurrency limit per request category.
 *
 * `/api/files/diff` and `/api/files/read` are expensive backend calls and the UI
 * asks for a lot of them at the same time (a diff panel schedules one diff per
 * rendered file, the editor, the diff panel and the chat preview read the same
 * file...). Fired in parallel they saturate the network and the backend, and the
 * answers come back out of order — the last one wins, and it is rarely the one
 * the user is looking at.
 *
 * A queue owns a category of request and lets only N of them be on the wire
 * (`1` by default, i.e. strictly sequential): the rest waits in line and starts
 * as soon as a slot frees up.
 *
 * **Breathing room between heavy calls.** Waiting for a slot is not enough: two
 * diffs chained back-to-back still occupy the connection for the whole time. Once
 * a heavy request finishes, the queue holds the next one for `gapMs` (`750 ms`
 * for reads and diffs), leaving the network free so the small calls — settings,
 * status, chat, the commit graph — go through immediately instead of queueing
 * behind a wall of diffs. The gap is only applied when there is something waiting:
 * the first call on an idle queue starts at once.
 *
 * The queue never sees duplicates, because it sits *behind* the short-term cache
 * and the in-flight dedupe of the HTTP layer (`api.js`):
 *
 *  - a cached answer is returned before the queue is reached,
 *  - a request identical to one already running/queued joins that promise, so it
 *    is enqueued once, not twice.
 *
 * @example
 * // Only one diff at a time, whatever the number of callers.
 * await API.post(url, body, { ttl: 4000, queue: 'files:diff' })
 *
 * // Two reads at a time instead of one, 750 ms apart.
 * API.setQueueConcurrency('files:read', 2)
 *
 * // No breathing room at all (or 200 ms).
 * API.setQueueGap('files:diff', 0)
 *
 * // What is happening right now.
 * console.table(API.queueStats)
 */

/** Concurrency used when a queue is created without an explicit limit. */
export const DEFAULT_CONCURRENCY = 1

/**
 * Idle time left between two consecutive heavy requests, so the lighter calls of
 * the app are not stuck behind them. `750 ms` of silence is enough for a few
 * small requests to complete on a keep-alive connection.
 */
export const DEFAULT_GAP_MS = 750

/**
 * Names of the queues used by the API modules.
 *
 * Two callers asking for the same name share the same queue, even when they live
 * in different modules (`files.diff` and `repo.fileDiff` share `files:diff`).
 */
export const QUEUE_NAMES = {
  /** `GET /api/files/read` — one file read at a time. */
  fileRead: 'files:read',
  /** `POST /api/files/diff` and `GET /api/git/repo/file/diff` — one diff at a time. */
  fileDiff: 'files:diff'
}

/**
 * Default gap (ms) of the heavy queues, indexed by queue name.
 *
 * Queues not listed here start their next job as soon as a slot is free.
 */
export const QUEUE_GAPS = {
  [QUEUE_NAMES.fileRead]: DEFAULT_GAP_MS,
  [QUEUE_NAMES.fileDiff]: DEFAULT_GAP_MS
}

export class RequestQueue {
  /**
   * @param {Object} [options] - Options.
   * @param {string} [options.name] - Queue name (shown in the stats).
   * @param {number} [options.concurrency] - Max requests on the wire at once.
   * @param {number} [options.maxPending] - Max jobs waiting (`0` = unlimited).
   * @param {number} [options.gapMs] - Idle time before the next job (`0` = none).
   */
  constructor({
    name = 'default',
    concurrency = DEFAULT_CONCURRENCY,
    maxPending = 0,
    gapMs = 0
  } = {}) {
    this.name = name
    this.concurrency = Math.max(1, Number(concurrency) || DEFAULT_CONCURRENCY)
    this.maxPending = Math.max(0, Number(maxPending) || 0)
    this.gapMs = Math.max(0, Number(gapMs) || 0)
    /** Jobs currently on the wire. */
    this._active = 0
    /** Jobs waiting for a slot: `[{ taskFn, resolve, reject, enqueuedAt }]`. */
    this._pending = []
    /** Timestamp before which the next job must not start. */
    this._cooldownUntil = 0
    /** Pending `setTimeout` handle of the cooldown wake-up. */
    this._timer = null
    this.stats = {
      queued: 0,
      running: 0,
      completed: 0,
      failed: 0,
      dropped: 0,
      peak: 0,
      maxWaitMs: 0,
      gapWaits: 0
    }
  }

  /** Requests currently on the wire. */
  get active() {
    return this._active
  }

  /** Requests waiting for a slot. */
  get pending() {
    return this._pending.length
  }

  /** Requests known by the queue (running + waiting). */
  get size() {
    return this._active + this._pending.length
  }

  /** Milliseconds left before the next job may start (`0` = free). */
  get cooldownRemaining() {
    return Math.max(0, this._cooldownUntil - Date.now())
  }

  /**
   * Change the limit at runtime (`1` = strictly sequential).
   *
   * Lowering it never cancels a running request: the extra slots simply close as
   * the current requests finish.
   *
   * @param {number} concurrency - Max requests on the wire.
   * @returns {RequestQueue} This queue.
   *
   * @example
   * queue.setConcurrency(1)
   */
  setConcurrency(concurrency) {
    this.concurrency = Math.max(1, Number(concurrency) || DEFAULT_CONCURRENCY)
    this._drain()
    return this
  }

  /**
   * Change the idle time left between two consecutive requests (`0` disables it).
   *
   * @param {number} gapMs - Milliseconds to wait after a request before the next.
   * @returns {RequestQueue} This queue.
   *
   * @example
   * queue.setGap(0)    // back-to-back
   * queue.setGap(1500) // even more breathing room
   */
  setGap(gapMs) {
    this.gapMs = Math.max(0, Number(gapMs) || 0)
    if (!this.gapMs) {
      // Do not keep the current cooldown alive once the gap is removed.
      this._cooldownUntil = 0
      this._clearTimer()
    }
    this._drain()
    return this
  }

  /**
   * Enqueue a task. The returned promise settles with the task result (value or
   * error), exactly as if the task had been called directly.
   *
   * @param {Function} taskFn - Factory returning the request promise.
   * @returns {Promise<*>} Task result.
   *
   * @example
   * const diff = await queue.run(() => API.post('/api/files/diff', body))
   */
  run(taskFn) {
    return new Promise((resolve, reject) => {
      if (this.maxPending && this._pending.length >= this.maxPending) {
        this.stats.dropped++
        reject(new Error(`[requestQueue:${this.name}] too many pending requests`))
        return
      }
      this._pending.push({ taskFn, resolve, reject, enqueuedAt: Date.now() })
      this.stats.queued++
      this._drain()
    })
  }

  /**
   * Reject every waiting job (running jobs are allowed to finish).
   *
   * Called when the project or the user changes: those answers belong to a
   * session that no longer exists.
   *
   * @param {string} [reason] - Error message.
   * @returns {number} Number of cancelled jobs.
   */
  clear(reason = 'queue cleared') {
    this._clearTimer()
    this._cooldownUntil = 0
    const pending = this._pending.splice(0, this._pending.length)
    pending.forEach((job) => job.reject(new Error(`[requestQueue:${this.name}] ${reason}`)))
    return pending.length
  }

  /**
   * Start as many waiting jobs as the concurrency and the gap allow.
   *
   * @private
   */
  _drain() {
    if (!this._pending.length) {
      this._clearTimer()
      return
    }
    if (this._active >= this.concurrency) return

    const remaining = this.cooldownRemaining
    if (remaining > 0) {
      // Leave the wire free for the small requests until the gap expires.
      this._schedule(remaining)
      return
    }


    while (this._active < this.concurrency && this._pending.length) {
      this._cooldownUntil = 0
      const job = this._pending.shift()
      const waitMs = Date.now() - job.enqueuedAt
      this.stats.maxWaitMs = Math.max(this.stats.maxWaitMs, waitMs)
      this._active++
      this.stats.running = this._active
      this.stats.peak = Math.max(this.stats.peak, this._active)

      Promise.resolve()
        .then(job.taskFn)
        .then(
          (value) => {
            this.stats.completed++
            job.resolve(value)
          },
          (error) => {
            this.stats.failed++
            job.reject(error)
          }
        )
        // Always free the slot, including on rejection: a failing diff must not
        // block the queue.
        .then(() => {
          this._active--
          this.stats.running = this._active
          // Only space out *consecutive* calls: if nothing is waiting, the next
          // request to arrive starts immediately.
          if (this._pending.length && this.gapMs) {
            this._cooldownUntil = Math.max(this._cooldownUntil, Date.now() + this.gapMs)
          }
          this._drain()
        })
    }
  }

  /**
   * Wake up the queue once the current cooldown expires.
   *
   * @param {number} waitMs - Milliseconds to wait.
   * @private
   */
  _schedule(waitMs) {
    if (this._timer) return
    this.stats.gapWaits++
    this._timer = setTimeout(() => {
      this._timer = null
      this._drain()
    }, waitMs)
    // Node timers must not keep the process alive (no-op in the browser).
    if (this._timer && typeof this._timer.unref === 'function') this._timer.unref()
  }

  /**
   * Cancel a pending cooldown wake-up.
   *
   * @private
   */
  _clearTimer() {
    if (!this._timer) return
    clearTimeout(this._timer)
    this._timer = null
  }
}

export class RequestQueueRegistry {
  /**
   * @param {Object} [options] - Options.
   * @param {number} [options.concurrency] - Default concurrency for new queues.
   * @param {number} [options.gapMs] - Default gap for queues not listed in `gaps`.
   * @param {Object} [options.gaps] - Per-queue-name gap: `{ 'files:diff': 750 }`.
   */
  constructor({ concurrency = DEFAULT_CONCURRENCY, gapMs = 0, gaps = {} } = {}) {
    this.concurrency = concurrency
    this.gapMs = gapMs
    /** @type {Object} Queue name -> gap in milliseconds. */
    this.gaps = { ...gaps }
    /** @type {Map<string, RequestQueue>} name -> queue. */
    this._queues = new Map()
  }

  /**
   * Gap (ms) that a queue is created with.
   *
   * @param {string} name - Queue name.
   * @param {number} [gapMs] - Explicit gap; when omitted the configured one wins.
   * @returns {number} Gap in milliseconds.
   * @private
   */
  _resolveGap(name, gapMs) {
    if (gapMs !== undefined) return Math.max(0, Number(gapMs) || 0)
    if (this.gaps[name] !== undefined) return Math.max(0, Number(this.gaps[name]) || 0)
    return this.gapMs
  }

  /**
   * Get (or lazily create) the queue of a category.
   *
   * @param {string} name - Queue name.
   * @param {Object} [options] - Options.
   * @param {number} [options.concurrency] - Concurrency to apply to the queue.
   * @param {number} [options.gapMs] - Gap to apply to the queue.
   * @returns {RequestQueue} Queue instance.
   */
  get(name, { concurrency, gapMs } = {}) {
    let queue = this._queues.get(name)
    if (!queue) {
      queue = new RequestQueue({
        name,
        concurrency: concurrency || this.concurrency,
        gapMs: this._resolveGap(name, gapMs)
      })
      this._queues.set(name, queue)
    } else {
      if (concurrency) queue.setConcurrency(concurrency)
      if (gapMs !== undefined) queue.setGap(gapMs)
    }
    return queue
  }

  /**
   * Run a task in the queue of its category. Without a name the task runs
   * immediately (no queueing), which keeps the call sites simple.
   *
   * @param {string} [name] - Queue name.
   * @param {Function} taskFn - Factory returning the request promise.
   * @param {Object} [options] - Options.
   * @param {number} [options.concurrency] - Override the queue concurrency.
   * @param {number} [options.gapMs] - Override the queue gap.
   * @returns {Promise<*>} Task result.
   */
  run(name, taskFn, { concurrency, gapMs } = {}) {
    if (!name) return Promise.resolve().then(taskFn)
    return this.get(name, { concurrency, gapMs }).run(taskFn)
  }

  /**
   * Change the concurrency of a queue at runtime.
   *
   * @param {string} name - Queue name.
   * @param {number} concurrency - Max requests on the wire.
   * @returns {RequestQueue} The queue.
   */
  setConcurrency(name, concurrency) {
    return this.get(name).setConcurrency(concurrency)
  }

  /**
   * Change the idle time left between two consecutive requests of a queue.
   *
   * @param {string} name - Queue name.
   * @param {number} gapMs - Milliseconds (`0` = back-to-back).
   * @returns {RequestQueue} The queue.
   *
   * @example
   * requestQueues.setGap('files:diff', 1500)
   */
  setGap(name, gapMs) {
    this.gaps[name] = Math.max(0, Number(gapMs) || 0)
    return this.get(name).setGap(this.gaps[name])
  }

  /**
   * Snapshot of every queue, handy from the dev tools console.
   *
   * @returns {Object} `{ [name]: { concurrency, gapMs, active, pending, ... } }`.
   *
   * @example
   * requestQueues.stats()
   * // { 'files:diff': { concurrency: 1, gapMs: 750, active: 0, pending: 3,
   * //   cooldownMs: 420, queued: 9, gapWaits: 5, ... } }
   */
  stats() {
    const snapshot = {}
    this._queues.forEach((queue, name) => {
      snapshot[name] = {
        concurrency: queue.concurrency,
        gapMs: queue.gapMs,
        cooldownMs: queue.cooldownRemaining,
        active: queue.active,
        pending: queue.pending,
        ...queue.stats
      }
    })
    return snapshot
  }

  /**
   * Cancel every waiting job of every queue.
   *
   * @param {string} [reason] - Error message.
   */
  clear(reason) {
    this._queues.forEach((queue) => queue.clear(reason))
  }
}

/**
 * Shared registry used by the HTTP layer (`api.js`).
 *
 * Reads and diffs keep `DEFAULT_GAP_MS` of silence between two consecutive
 * requests; every other queue is unaffected.
 */
export const requestQueues = new RequestQueueRegistry({ gaps: QUEUE_GAPS })

export default requestQueues