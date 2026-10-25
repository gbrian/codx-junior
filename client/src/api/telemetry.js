/**
 * ============================================================================
 * Client telemetry — socket events and local-network calls.
 * ----------------------------------------------------------------------------
 * API monitoring reports what the SERVER measured for the requests it handled
 * (`/api/api-logs/*`). Two kinds of activity are invisible to that data source
 * because they never reach a route handler:
 *
 *   • SOCKET EVENTS — the socket.io traffic of this browser tab: what it emits,
 *     what it receives and the connection lifecycle. The server publishes the
 *     events but keeps no per-client delivery log.
 *   • LOCAL NETWORK CALLS — the HTTP requests this tab sends to the codx-junior
 *     host over the local network (same origin / localhost / RFC1918 / *.local),
 *     with the wall-clock latency the browser sees: DNS + TCP + round trip.
 *
 * Both streams are recorded IN THE BROWSER, in memory, and are correlated with
 * the server aggregates by the API monitoring chart.
 *
 * RETENTION — THE LAST HOUR ONLY
 * ------------------------------
 * Entries older than `CLIENT_LOG_TTL_MS` are dropped (`pruneClientTelemetry`,
 * also called on every push), which is exactly the window the chart overlays on
 * the backend buckets. Nothing is persisted: a reload starts empty.
 * `CLIENT_LOG_LIMIT` is only a memory guard for pathological bursts — the TTL
 * is what bounds the history.
 *
 * A CALL IS RECORDED TWICE
 * ------------------------
 * `beginNetworkCall()` unshifts the entry the moment the request leaves, with
 * `pending: true` and no `finishedAt`; `finish()` fills status/duration in when
 * the promise settles. That is what makes "requests processing" measurable: a
 * call in flight is a row without `finishedAt`, and a bucket that was taken
 * while it was open counts it as concurrent load.
 *
 * PRIVACY / SIZE
 * --------------
 * Only the SHAPE of an event is stored: name, direction, payload size, timings
 * and error message. Payloads and request bodies are never copied here.
 * ============================================================================
 */
import { reactive } from 'vue'

/**
 * How long the client-side logs are kept, in milliseconds.
 *
 * The chart overlays them on the backend buckets of the last hour, so keeping
 * more would only cost memory: older spots are rendered as gaps, not as zeros.
 */
export const CLIENT_LOG_TTL_MS = 60 * 60 * 1000

/**
 * Hard cap per stream, as a memory guard only.
 * The one-hour TTL is what normally bounds the buffers; this catches bursts
 * (a request storm) where one hour of entries would be too many objects.
 */
export const CLIENT_LOG_LIMIT = 5000

/** Calls slower than this are counted as "slow" in the header of the card. */
export const SLOW_CALL_MS = 1000

/* ── Local network detection ──────────────────────────────────────────────── */

/**
 * Hostnames/IPs that mean "the machine next to me". Single-label hosts
 * ("codx", "nas") and `.local` / `.lan` / `.internal` names are LAN names; the
 * address ranges are the RFC1918 / link-local blocks.
 */
const PRIVATE_HOST_PATTERNS = [
  /^localhost$/i,
  /^127\./,
  /^10\./,
  /^192\.168\./,
  /^172\.(1[6-9]|2\d|3[01])\./,
  /^169\.254\./, // link-local (APIPA)
  /^\[?::1\]?$/,
  /^\[?f[cd][0-9a-f]{2}:/i, // IPv6 unique-local / link-local
  /\.(local|localdomain|lan|internal|home|corp)$/i
]

function browserLocation() {
  return typeof window !== 'undefined' ? window.location : null
}

function currentOrigin() {
  const location = browserLocation()
  return location?.origin || 'http://localhost'
}

function currentHref() {
  const location = browserLocation()
  return location?.href || 'http://localhost/'
}

/**
 * True when the hostname belongs to the local network.
 * @param {string} hostname
 * @returns {boolean}
 */
export function isLocalHostname(hostname) {
  const host = String(hostname || '').toLowerCase()
  if (!host) return false
  // The host serving this tab is, by definition, the local codx-junior host.
  if (browserLocation() && host === browserLocation().hostname.toLowerCase()) return true
  // Single-label host ("codx", "nas", "workstation") — a LAN name, not a FQDN.
  if (!host.includes('.') && !host.includes(':')) return true
  return PRIVATE_HOST_PATTERNS.some((pattern) => pattern.test(host))
}

/**
 * True when `url` targets the local network (relative URLs resolve against the
 * current document, so every same-origin API call qualifies).
 * @param {string} url
 * @returns {boolean}
 */
export function isLocalNetworkUrl(url) {
  let parsed
  try {
    parsed = new URL(String(url || ''), currentHref())
  } catch {
    return false
  }
  if (parsed.origin === currentOrigin()) return true
  return isLocalHostname(parsed.hostname)
}

/**
 * Path of `url` without the query string.
 *
 * The query carries `codx_path` (project scoping) and search terms, so it is
 * useless for grouping and would explode the row count.
 * @param {string} url
 * @returns {string}
 */
export function localNetworkPath(url) {
  try {
    return new URL(String(url || ''), currentHref()).pathname || '/'
  } catch {
    return String(url || '').split('?')[0] || '/'
  }
}

/* ── Helpers ──────────────────────────────────────────────────────────────── */

/** Serializable size of a payload, in characters. Never throws. */
export function payloadSize(value) {
  if (value === undefined || value === null) return 0
  if (typeof value === 'string') return value.length
  try {
    return JSON.stringify(value)?.length || 0
  } catch {
    // Circular or non-serializable (class instance): size is unknown.
    return 0
  }
}

let sequence = 0

/**
 * Drops the expired entries of a newest-first buffer.
 *
 * Expired entries are always the tail, so this stops at the first one that is
 * still inside the window — no scan of the whole buffer.
 */
function pruneTail(list, cutoff) {
  while (list.length && (Number(list[list.length - 1].ts) || 0) < cutoff) {
    list.pop()
  }
}

/** Newest entry first; the tail (oldest) is dropped once the buffer is full. */
function pushCapped(list, entry) {
  pruneTail(list, Date.now() - CLIENT_LOG_TTL_MS)
  list.unshift(entry)
  if (list.length > CLIENT_LOG_LIMIT) list.splice(CLIENT_LOG_LIMIT)
}

/* ── State ────────────────────────────────────────────────────────────────── */

/**
 * Reactive store shared by every producer (socket / http layer) and by the API
 * monitoring view. Counters are cumulative since page load and survive a buffer
 * rotation, so the totals never "go down" while the session lasts.
 */
export const telemetry = reactive({
  /** Socket events, newest first: { id, ts, event, direction, size, durationMs, error, detail, socketId }. */
  socket: [],
  /**
   * Local network calls, newest first:
   * { id, ts, startedAt, finishedAt, pending, method, path, status, durationMs, error }.
   * `pending: true` means the request is still in flight (see `beginNetworkCall`).
   */
  network: [],

  /** Socket connection state, mirrored from the SocketManager lifecycle. */
  socketConnected: false,
  socketId: null,

  socketCounters: {
    total: 0,
    sent: 0,
    received: 0,
    system: 0,
    errors: 0,
    ackTotalMs: 0,
    acked: 0
  },

  networkCounters: {
    calls: 0,
    errors: 0,
    totalMs: 0,
    slow: 0
  },

  lastSocketAt: null,
  lastNetworkAt: null
})

/* ── Producers ────────────────────────────────────────────────────────────── */

/**
 * Records one socket event.
 *
 * @param {object} entry
 * @param {string} entry.event        Event name (or lifecycle name: connect…).
 * @param {'in'|'out'|'system'} [entry.direction='in']
 * @param {number} [entry.size]       Payload size in characters.
 * @param {number|null} [entry.durationMs] Ack latency, when an ack was used.
 * @param {string|null} [entry.error] Failure message, if any.
 * @param {string|null} [entry.detail] Extra context (e.g. disconnect reason).
 * @param {string|null} [entry.socketId]
 * @returns {object} the stored entry
 */
export function recordSocketEvent({
  event,
  direction = 'in',
  size = 0,
  durationMs = null,
  error = null,
  detail = null,
  socketId = null
} = {}) {
  const entry = {
    id: ++sequence,
    ts: Date.now(),
    event: String(event || 'unknown'),
    direction: direction === 'out' || direction === 'system' ? direction : 'in',
    size: Number(size) || 0,
    durationMs: durationMs === null || durationMs === undefined
      ? null
      : Math.max(0, Math.round(Number(durationMs) || 0)),
    error: error ? String(error) : null,
    detail: detail ? String(detail) : null,
    socketId: socketId || telemetry.socketId || null
  }

  pushCapped(telemetry.socket, entry)

  const counters = telemetry.socketCounters
  counters.total += 1
  if (entry.direction === 'out') counters.sent += 1
  else if (entry.direction === 'in') counters.received += 1
  else counters.system += 1
  if (entry.error) counters.errors += 1
  if (entry.durationMs !== null) {
    counters.ackTotalMs += entry.durationMs
    counters.acked += 1
  }

  telemetry.lastSocketAt = entry.ts
  return entry
}

/**
 * Registers one local HTTP call AT REQUEST START.
 *
 * The entry is visible immediately with `pending: true`, which is what makes
 * "requests processing" measurable. `finish()` fills in the outcome when the
 * promise settles; until then the call is counted as in flight.
 *
 * @param {object} [call]
 * @param {string} [call.method]
 * @param {string} [call.url]
 * @returns {{id: number, entry: object, finish: (result?: object) => object}|null}
 *          null when the URL does not target the local network.
 */
export function beginNetworkCall({ method = 'GET', url = '' } = {}) {
  if (!isLocalNetworkUrl(url)) return null

  const startedAt = Date.now()

  pushCapped(telemetry.network, {
    id: ++sequence,
    ts: startedAt,
    startedAt,
    finishedAt: null,
    pending: true,
    method: String(method || 'GET').toUpperCase(),
    path: localNetworkPath(url),
    status: 0,
    durationMs: 0,
    error: null
  })

  // Index 0 is the REACTIVE PROXY of the entry just unshifted. Mutating the raw
  // object would leave every consumer on the old values, so the handle keeps the
  // proxy: setting a field here notifies the tables and the chart.
  const entry = telemetry.network[0]

  /**
   * Closes the entry. Idempotent: a duplicate callback (axios settling twice,
   * a retried call) must not be counted as two calls.
   *
   * @param {object} [result]
   * @param {number} [result.status]    HTTP status (0 when it never answered).
   * @param {Error|string|null} [result.error]
   * @param {number|null} [result.durationMs] Overrides the measured wall clock.
   * @returns {object} the stored entry
   */
  const finish = ({ status = 0, error = null, durationMs = null } = {}) => {
    if (!entry.pending) return entry

    const finishedAt = Date.now()
    entry.pending = false
    entry.finishedAt = finishedAt
    entry.status = Number(status) || 0
    entry.error = error ? String(error.message || error) : null
    entry.durationMs = durationMs === null || durationMs === undefined
      ? Math.max(0, finishedAt - (Number(entry.startedAt) || finishedAt))
      : Math.max(0, Math.round(Number(durationMs) || 0))

    const counters = telemetry.networkCounters
    counters.calls += 1
    counters.totalMs += entry.durationMs
    if (entry.error || entry.status >= 500) counters.errors += 1
    if (entry.durationMs >= SLOW_CALL_MS) counters.slow += 1

    telemetry.lastNetworkAt = finishedAt
    return entry
  }

  return { id: entry.id, entry, finish }
}

/** Mirrors the socket connection state (used by the "Connected" pill). */
export function setSocketConnected(connected, socketId = null) {
  telemetry.socketConnected = !!connected
  telemetry.socketId = connected ? (socketId || telemetry.socketId) : null
}

/* ── Maintenance ──────────────────────────────────────────────────────────── */

/**
 * Drops everything that fell out of the retention window.
 *
 * Producers already prune on every push, but an idle tab would keep its older
 * entries until the next event: the view calls this on every load so the
 * "last hour" is true even when this browser sends nothing.
 *
 * @param {number} [now] Reference clock (tests).
 */
export function pruneClientTelemetry(now = Date.now()) {
  const cutoff = now - CLIENT_LOG_TTL_MS
  pruneTail(telemetry.socket, cutoff)
  pruneTail(telemetry.network, cutoff)
}

/**
 * Empties one stream (or both) and resets its counters. The connection state is
 * intentionally kept: clearing the log must not lie about the socket.
 * @param {'socket'|'network'|'all'} [scope='all']
 */
export function clearClientTelemetry(scope = 'all') {
  const all = scope === 'all'

  if (all || scope === 'socket') {
    telemetry.socket.splice(0)
    Object.assign(telemetry.socketCounters, {
      total: 0, sent: 0, received: 0, system: 0, errors: 0, ackTotalMs: 0, acked: 0
    })
    telemetry.lastSocketAt = null
  }

  if (all || scope === 'network') {
    telemetry.network.splice(0)
    Object.assign(telemetry.networkCounters, { calls: 0, errors: 0, totalMs: 0, slow: 0 })
    telemetry.lastNetworkAt = null
  }
}

export default telemetry