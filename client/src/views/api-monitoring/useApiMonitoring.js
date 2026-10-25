/**
 * ============================================================================
 * API monitoring — view state, filters and derived aggregations.
 * ----------------------------------------------------------------------------
 * Every HTTP call handled by the backend is stored as one event and aggregated
 * server-side (see `/api/api-logs/*`). Unlike Infrastructure → Monitoring there
 * is NO client-side sampling buffer for those numbers: they come straight from
 * the stored history, so what the charts show is exactly what happened — nothing
 * is interpolated or invented.
 *
 * TWO EXTRA SOURCES ARE CLIENT-SIDE
 * ---------------------------------
 * Activity that never reaches a route handler is captured in the browser by
 * `@/api/telemetry` and rendered by the same view:
 *   • SOCKET EVENTS — what this tab emits/receives plus the connection
 *     lifecycle (the server keeps no per-client delivery log).
 *   • LOCAL NETWORK — the calls this tab makes to the codx-junior host on the
 *     LAN, with the latency the browser measured (DNS + TCP + round trip).
 * The module owns the whole view state (filters, last response, polling) so the
 * components stay presentational, the same split used by useInfra.js.
 *
 * THE CHART OVERLAYS BOTH SOURCES (why this file buckets the client log)
 * ---------------------------------------------------------------------
 * "The app feels slow" has two very different causes: the API answered slowly,
 * or this browser was waiting on a queue of its own requests. The chart
 * therefore draws, per backend bucket, the local side of the same window:
 *   • local_done     — local calls that finished in the bucket;
 *   • local_inflight — local calls still open when the bucket ended (the
 *                      concurrency the browser was actually carrying);
 *   • local_errors   — local calls that failed in the bucket;
 *   • local_avg_ms   — average local latency in the bucket (not plotted: it is
 *                      shown in the tooltip footer, so the bars stay countable).
 * The server series stay lines; the local ones are BARS on their own axis, so a
 * slow moment is read at a glance: many bars and a fast backend = the wait is on
 * this tab's side, a tall latency line with empty bars = the backend is loaded.
 *
 * They come from `@/api/telemetry`, which keeps ONE HOUR of history, so buckets
 * older than the retained window are `null`: Chart.js renders a gap (and the
 * tooltip says "no local sample") instead of a misleading zero.
 *
 * THE TWO CLIENT TABLES ANSWER "WHAT IS SLOW, RIGHT NOW AND OVERALL"
 * -----------------------------------------------------------------
 *   • IN FLIGHT (realtime) — `inFlightCalls`: the calls open at this instant,
 *     longest first, with an elapsed time that ticks every second. Elapsed is
 *     derived, never stored (`now − startedAt`, see `clientNow`), so a request
 *     that never settles keeps counting instead of freezing at a stale value.
 *   • LOCAL STATISTICS — `localNetworkRows`: per endpoint, which requests cost
 *     the most TIME (`totalMs` + `share` of the local time) and which REPEAT
 *     the most (`calls`, `callsPerMin`), with avg/p95/max, errors and the open
 *     count. `state.localSortBy` chooses the ordering; pending calls are counted
 *     (`open`) but never averaged, or a stuck request would drag the numbers.
 *
 * LOADING MODEL
 * -------------
 * The six aggregations behind the view are INDEPENDENT queries. Each one is
 * committed the moment it answers, so the chart never waits behind a slow
 * table, and a query that hangs or fails only degrades its own card instead of
 * freezing the dashboard on an old snapshot.
 *
 * ADMIN MODE
 * ----------
 * `allUsers` switches every request to the `/admin` endpoints (metrics across
 * every user and project). It is only meaningful for admins — the view gates
 * the toggle on `$storex.users.isAdmin`.
 * ============================================================================
 */
import { computed, reactive, ref } from 'vue'
import { API } from '@/api/api'
import { apiLogsModule } from '@/api/modules/apiLogs'
import { telemetry, clearClientTelemetry, pruneClientTelemetry } from '@/api/telemetry'

/**
 * Time buckets offered by the header selector (`grouping` query param).
 * Second-level buckets are the useful ones for a live dashboard; `day` is kept
 * for long ranges. The value is forwarded verbatim to the backend.
 */
export const GROUPINGS = [
  { id: '5s', label: 'Every 5 sec' },
  { id: '10s', label: 'Every 10 sec' },
  { id: '30s', label: 'Every 30 sec' },
  { id: 'minute', label: 'Per minute' },
  { id: 'hour', label: 'Hourly' },
  { id: 'day', label: 'Daily' }
]

/** Bucket used until the operator picks another one. */
export const DEFAULT_GROUPING = '10s'

/** Width of each grouping, in milliseconds (client-side bucketing). */
export const GROUPING_MS = {
  '5s': 5 * 1000,
  '10s': 10 * 1000,
  '30s': 30 * 1000,
  minute: 60 * 1000,
  hour: 60 * 60 * 1000,
  day: 24 * 60 * 60 * 1000
}

/** Sampling cadence of the auto-refresh loop (seconds). */
export const REFRESH_INTERVALS = [
  { value: 10, label: '10s' },
  { value: 30, label: '30s' },
  { value: 60, label: '1 min' },
  { value: 300, label: '5 min' }
]

/** Range shortcuts. "24h" resolves to yesterday→today (buckets are per day). */
export const DATE_PRESETS = [
  { id: 'today', label: 'Today' },
  { id: '24h', label: '24h' },
  { id: '7d', label: '7d' },
  { id: '30d', label: '30d' }
]

/** HTTP methods offered by the filter ('' = every method). */
export const METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

export const SLOWEST_LIMIT = 25
export const ERRORS_LIMIT = 50
export const TOP_ENDPOINTS = 12
export const TOP_SLOWEST = 8
/** Rows rendered per client-side table (socket events / local network). */
export const TOP_CLIENT_ROWS = 8
export const DEFAULT_INTERVAL = 30

/**
 * Orderings offered by the local-network statistics table.
 *
 * `time` is the default on purpose: it answers "which requests are eating this
 * tab's time", which is the question the card exists for. `calls` answers the
 * other half — "which ones repeat the most" (a cheap endpoint called 200 times
 * is still a problem).
 */
export const LOCAL_SORTS = [
  { id: 'time', label: 'Total time' },
  { id: 'calls', label: 'Most repeated' },
  { id: 'avg', label: 'Average' },
  { id: 'p95', label: 'p95' },
  { id: 'max', label: 'Max' },
  { id: 'errors', label: 'Errors' },
  { id: 'last', label: 'Last seen' }
]

/**
 * Series rendered by the chart, straight from the backend aggregates:
 * throughput on the first axis (counts), latency on the second one (ms) — the
 * same palette as the infra / analytics charts.
 */
export const CHART_METRICS = [
  { key: 'calls', label: 'Calls', color: '#6366f1', fill: true },
  { key: 'errors', label: 'Errors', color: '#ef4444' },
  { key: 'avg_ms', label: 'Avg latency', color: '#10b981', axis: 'y1' },
  { key: 'p95_ms', label: 'p95 latency', color: '#f59e0b', axis: 'y1' }
]

/**
 * Series added for THIS BROWSER's local traffic (`@/api/telemetry`).
 *
 * They are BARS, and live on their own axis (`y2`): the counts are per tab — a
 * handful of requests — so sharing the server axis would rescale it and hide the
 * backend numbers. Bars are also the honest shape for counts: they have no
 * continuity between buckets, while a line would imply the value ramps from one
 * bucket to the next. The server series stay lines; the chart draws the bars
 * behind them (`order`), so the backend numbers are never hidden.
 */
export const CLIENT_CHART_METRICS = [
  { key: 'local_done', label: 'Local done', color: '#22d3ee', type: 'bar', axis: 'y2' },
  { key: 'local_inflight', label: 'Local in flight', color: '#a855f7', type: 'bar', axis: 'y2' },
  { key: 'local_errors', label: 'Local failed', color: '#fb7185', type: 'bar', axis: 'y2' }
]

/** Everything the chart draws (server aggregates + client log). */
export const chartMetrics = [...CHART_METRICS, ...CLIENT_CHART_METRICS]

/* ── Dates ────────────────────────────────────────────────────────────────── */
export function isoDay(date) {
  return date.toISOString().split('T')[0]
}

export function todayISO() {
  return isoDay(new Date())
}

export function daysAgoISO(days) {
  const date = new Date()
  date.setDate(date.getDate() - days)
  return isoDay(date)
}

/* ── Client ───────────────────────────────────────────────────────────────── */
let client = null

/**
 * Lazily instantiated API-log client. It shares the app-wide `API` instance, so
 * auth, base URL and interceptors all apply.
 */
function api() {
  if (!client) client = apiLogsModule(API)
  return client
}

/** The endpoint group matching the current admin mode. */
function scopedApi() {
  return state.allUsers ? api().admin : api()
}

/* ── State ────────────────────────────────────────────────────────────────── */
export const state = reactive({
  // idle | loading | ready | error
  status: 'idle',
  error: null,
  lastUpdated: null,

  /**
   * Monotonic counter, incremented once per committed refresh AND once per
   * configuration change.
   *
   * Derived lists are invalidated by the payload replacement itself, but a
   * canvas cannot be: `ApiMonitoringChart` binds to this counter so every round
   * produces exactly one redraw — even when two consecutive payloads happen to
   * carry the same values (identical arrays ⇒ no prop change ⇒ no redraw).
   */
  revision: 0,

  // admin endpoints (metrics from every user) — set from users.isAdmin
  allUsers: false,

  // auto-refresh
  live: false,
  interval: DEFAULT_INTERVAL,

  filters: {
    startDate: daysAgoISO(1),
    endDate: todayISO(),
    grouping: DEFAULT_GROUPING,
    path: '',
    method: '',
    statusCode: '',
    minDurationSeconds: '',
    username: '',
    projectName: ''
  },

  // last response
  summary: null,
  series: [],
  endpoints: {},
  statuses: {},
  slowest: [],
  errors: [],
  dates: [],

  /**
   * Selectable endpoints for the "path" filter. Kept across reloads: once a
   * path filter is applied the by-endpoint response only contains that one
   * endpoint, so the list would otherwise collapse to a single option.
   */
  endpointOptions: [],

  // endpoint table ordering: calls | errors | avg | p95 | max
  sortBy: 'p95',

  // local-network statistics ordering: time | calls | avg | p95 | max | errors | last
  localSortBy: 'time'
})

/* ── Filters ──────────────────────────────────────────────────────────────── */
function buildFilters() {
  const filters = state.filters
  const params = {
    startDate: filters.startDate || undefined,
    endDate: filters.endDate || undefined,
    path: filters.path || undefined,
    method: filters.method || undefined,
    statusCode: filters.statusCode === '' ? undefined : Number(filters.statusCode),
    minDurationSeconds:
      filters.minDurationSeconds === '' ? undefined : Number(filters.minDurationSeconds)
  }
  // The user-scoped endpoints already filter by the authenticated user; passing
  // `username` there is meaningless (and rejected as an unknown query param).
  if (state.allUsers) {
    params.username = filters.username || undefined
    params.projectName = filters.projectName || undefined
  }
  return params
}

/**
 * Patches the filters WITHOUT fetching (used on every keystroke / select).
 * Call `applyFilters()` to reload.
 *
 * The revision bump is what makes the configuration change visible
 * immediately: the endpoint table re-sorts and the canvas repaints as soon as
 * the control is used, without waiting for the next network round.
 */
export function setFilter(patch = {}) {
  Object.assign(state.filters, patch)
  state.revision += 1
}

/** True when at least one filter narrows the result set. */
export const filtersActive = computed(() => {
  const f = state.filters
  return !!(f.path || f.method || f.statusCode !== '' || f.minDurationSeconds !== '')
})

/** Range shortcut matching the current dates (or null). */
export const activePreset = computed(() => {
  const today = todayISO()
  const { startDate, endDate } = state.filters
  if (startDate === today && endDate === today) return 'today'
  if (startDate === daysAgoISO(1) && endDate === today) return '24h'
  if (startDate === daysAgoISO(7) && endDate === today) return '7d'
  if (startDate === daysAgoISO(30) && endDate === today) return '30d'
  return null
})

export const groupingLabel = computed(
  () => GROUPINGS.find(g => g.id === state.filters.grouping)?.label || 'Every 10 sec'
)

/** Applies a range shortcut. */
export function applyPreset(id) {
  const today = todayISO()
  const ranges = {
    today: { startDate: today, endDate: today },
    '24h': { startDate: daysAgoISO(1), endDate: today },
    '7d': { startDate: daysAgoISO(7), endDate: today },
    '30d': { startDate: daysAgoISO(30), endDate: today }
  }
  const range = ranges[id]
  if (range) Object.assign(state.filters, range)
  return applyFilters()
}

/** Resets every filter back to the default (last 24h, 10 s buckets). */
export function clearFilters() {
  Object.assign(state.filters, {
    startDate: daysAgoISO(1),
    endDate: todayISO(),
    grouping: DEFAULT_GROUPING,
    path: '',
    method: '',
    statusCode: '',
    minDurationSeconds: '',
    username: '',
    projectName: ''
  })
  return applyFilters()
}

/**
 * Ordering of the local-network statistics table.
 *
 * Pure client-side state: no fetch, and the rows are already derived, so the
 * table re-sorts on the next tick without touching the backend.
 */
export function setLocalSortBy(value) {
  state.localSortBy = LOCAL_SORTS.some(option => option.id === value) ? value : 'time'
}

/* ── Loading ──────────────────────────────────────────────────────────────── */
let round = null
let loadSeq = 0

/**
 * A single aggregation that has not answered within this window is dropped.
 *
 * The six panels are independent queries: without a timeout ONE wedged request
 * (a heavy `/by-endpoint` over a whole day, a dropped connection) would keep
 * the whole round pending forever — the dashboard would stay frozen on its
 * previous snapshot, with no error and no spinner to explain it.
 */
const REQUEST_TIMEOUT_MS = 30 * 1000

/**
 * Two loads requested within this window AND with the same filters are
 * coalesced (the Live tick and a manual Refresh usually land together). A load
 * with a different filter signature — the operator just changed the bucket
 * size — is never coalesced: it replaces the running round.
 */
const DUPLICATE_ROUND_WINDOW_MS = 1000

/** Identity of the current selection, used to coalesce identical loads only. */
function roundKey() {
  return `${state.filters.grouping}|${JSON.stringify(buildFilters())}`
}

/**
 * Races `task` against a clock. The rejection carries a readable message so it
 * can be shown in the banner as-is.
 *
 * @param {Promise<any>|any} task Request to track.
 * @param {string} label Human name of the panel (used in the message).
 * @param {number} [timeoutMs]
 * @returns {Promise<any>}
 */
function withTimeout(task, label, timeoutMs = REQUEST_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(
      () => reject(new Error(`${label} did not answer within ${Math.round(timeoutMs / 1000)}s`)),
      timeoutMs
    )
    Promise.resolve(task).then(
      (value) => {
        clearTimeout(timer)
        resolve(value)
      },
      (error) => {
        clearTimeout(timer)
        reject(error)
      }
    )
  })
}

/**
 * Writes one aggregation into the state. Called per slot, as soon as that slot
 * answers — this is what makes the chart react to a refresh instead of waiting
 * for the slowest table.
 */
function applyResult(slot, value) {
  switch (slot) {
    case 'summary':
      state.summary = value || null
      break
    case 'daily':
      state.series = Array.isArray(value) ? value : []
      break
    case 'endpoints':
      state.endpoints = value || {}
      // Only refresh the option list when no path filter is narrowing it.
      if (!state.filters.path) {
        state.endpointOptions = Object.keys(state.endpoints).sort()
      }
      break
    case 'statuses':
      state.statuses = value || {}
      break
    case 'slowest':
      state.slowest = Array.isArray(value) ? value : []
      break
    case 'errors':
      state.errors = Array.isArray(value) ? value : []
      break
    default:
      break
  }
}

/**
 * Reloads every panel of the view in one round (all requests in parallel).
 *
 * @param {{silent?: boolean}} [options] `silent` skips the loading/error state
 *        flip — used by the auto-refresh loop so the screen never blinks.
 */
export function applyFilters(options) {
  return loadAll(options)
}

export function loadAll({ silent = false } = {}) {
  // The client logs keep one hour: prune before deriving anything, so the chart
  // overlay and the tables always describe the same window (an idle tab would
  // otherwise keep expired entries until its next local call).
  pruneClientTelemetry()

  const now = Date.now()
  const key = roundKey()

  // Burst of identical requests (Live tick + Refresh click): reuse the round
  // that is already fetching the very same selection.
  if (round && round.key === key && now - round.startedAt < DUPLICATE_ROUND_WINDOW_MS) {
    return round.promise
  }

  const filters = buildFilters()
  const grouping = state.filters.grouping
  const client = scopedApi()

  if (!silent) {
    state.error = null
    if (state.status !== 'ready') state.status = 'loading'
  }

  const seq = ++loadSeq

  const tasks = {
    summary: () => client.summary(filters),
    daily: () => client.daily({ ...filters, grouping }),
    endpoints: () => client.byEndpoint(filters),
    statuses: () => client.byStatus(filters),
    slowest: () => client.slowest({ ...filters, limit: SLOWEST_LIMIT }),
    errors: () => client.errors({ ...filters, limit: ERRORS_LIMIT })
  }

  const labels = {
    summary: 'summary',
    daily: 'chart series',
    endpoints: 'endpoints',
    statuses: 'status codes',
    slowest: 'slowest calls',
    errors: 'failed calls'
  }

  const promise = (async () => {
    const failures = []

    await Promise.all(
      Object.entries(tasks).map(([slot, task]) => (
        withTimeout(task(), labels[slot])
          .then((value) => {
            if (seq === loadSeq) applyResult(slot, value)
          })
          .catch((error) => {
            // A newer round owns the state: its results must not be mixed with
            // the answer of an outdated selection.
            failures.push(error?.message || String(error))
          })
      ))
    )

    if (seq !== loadSeq) return

    state.status = 'ready'
    state.error = failures.length ? failures[0] : null
    state.lastUpdated = new Date()
    // Explicit "the numbers changed" signal for the tables and the canvas.
    state.revision += 1
  })()

  const release = () => {
    if (round && round.seq === seq) round = null
  }
  promise.then(release, release)

  round = { seq, key, startedAt: now, promise }
  return promise
}

/** Loads the dates that actually contain data (used as a hint in the header). */
export async function loadDates() {
  try {
    state.dates = await scopedApi().dates()
  } catch (err) {
    state.dates = []
  }
  return state.dates
}

/** Switches between the user-scoped and the admin endpoint set. */
export function setAllUsers(enabled) {
  state.allUsers = !!enabled
  // A different scope means a different date set: refresh both.
  loadDates()
  return loadAll()
}

/* ── Auto-refresh ─────────────────────────────────────────────────────────── */
let timer = null

export function stopLive() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function startLive() {
  stopLive()
  if (!state.live) return
  timer = setInterval(() => loadAll({ silent: true }), intervalMs())
}

function intervalMs() {
  const seconds = Number(state.interval) || DEFAULT_INTERVAL
  return Math.max(5, seconds) * 1000
}

/** Header "Live" switch. */
export function setLive(on) {
  state.live = !!on
  if (state.live) {
    loadAll({ silent: true })
    startLive()
  } else {
    stopLive()
  }
}

/** Header interval selector: reschedules when live, otherwise just remembers. */
export function setIntervalSeconds(seconds) {
  const value = Number(seconds)
  state.interval = REFRESH_INTERVALS.some(o => o.value === value) ? value : DEFAULT_INTERVAL
  if (state.live) {
    loadAll({ silent: true })
    startLive()
  }
}

/* ── Derived data ─────────────────────────────────────────────────────────── */

/** Numeric value used to order the endpoint table. */
function sortValue(row) {
  const values = {
    calls: Number(row.calls) || 0,
    errors: Number(row.errors) || 0,
    avg: Number(row.avg_duration_seconds) || 0,
    p95: Number(row.p95_duration_seconds) || 0,
    max: Number(row.max_duration_seconds) || 0
  }
  return values[state.sortBy] ?? 0
}

/** Endpoints as a sorted array `[{ path, calls, errors, avg_duration_seconds… }]`. */
export const endpointRows = computed(() =>
  Object.entries(state.endpoints || {})
    .map(([path, metrics]) => ({ path, ...metrics }))
    .sort((a, b) => sortValue(b) - sortValue(a))
)

/** Status codes as an array ordered numerically. */
export const statusRows = computed(() =>
  Object.entries(state.statuses || {})
    .map(([code, metrics]) => ({ code: Number(code), ...metrics }))
    .sort((a, b) => a.code - b.code)
)

/* ── Client buckets (local traffic aligned with the backend periods) ──────── */

/**
 * Backend period → epoch milliseconds, parsed as LOCAL time.
 *
 * Periods are not ISO-8601 ("YYYY-MM-DD", "YYYY-MM-DD HH:00", "YYYY-MM-DD
 * HH:MM", "YYYY-MM-DD HH:MM:SS"), and the API runs on this machine, so local
 * time is the correct interpretation — the same one the chart labels use.
 *
 * @param {string} period
 * @returns {number|null}
 */
export function periodToMs(period) {
  const value = String(period || '').trim()
  if (!value) return null

  const [datePart, timePart = ''] = value.split(' ')
  const [year, month, day] = datePart.split('-').map(Number)
  if (!year || !month || !day) return null

  const [hours = 0, minutes = 0, seconds = 0] = timePart
    .split(':')
    .map(part => Number(part) || 0)

  const ms = new Date(year, month - 1, day, hours, minutes, seconds, 0).getTime()
  return Number.isFinite(ms) ? ms : null
}

/**
 * Width of ONE bucket, taken from the precision of the period string the
 * backend actually returned (`requested` only fills in the second-level case,
 * where the string alone cannot say if it is 5 s, 10 s or 30 s).
 *
 * Reading the precision instead of trusting the request keeps the overlay
 * aligned even if a range falls back to a coarser grouping.
 */
function bucketSizeFor(period, requested) {
  const [, timePart = ''] = String(period || '').split(' ')
  const precision = timePart ? timePart.split(':').length : 0

  if (precision === 0) return GROUPING_MS.day
  if (precision === 1) return GROUPING_MS.hour
  if (precision === 2) return GROUPING_MS.minute
  return requested < GROUPING_MS.minute ? requested : GROUPING_MS.minute
}

/**
 * Start of the bucket containing `timestamp`, in LOCAL time.
 *
 * Aligning on the epoch (`Math.floor(ts / size)`) would be wrong for `hour` and
 * `day` buckets outside UTC: the server periods are local-time strings.
 */
function bucketStartOf(timestamp, size) {
  const ms = Number(timestamp) || 0
  const date = new Date(ms)
  if (!Number.isFinite(date.getTime())) return 0

  if (size >= GROUPING_MS.day) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime()
  }
  if (size >= GROUPING_MS.hour) {
    return new Date(
      date.getFullYear(), date.getMonth(), date.getDate(), date.getHours()
    ).getTime()
  }
  if (size >= GROUPING_MS.minute) {
    return new Date(
      date.getFullYear(), date.getMonth(), date.getDate(), date.getHours(), date.getMinutes()
    ).getTime()
  }
  // Sub-minute buckets: UTC offsets are whole minutes, so the epoch grid and
  // the local grid coincide.
  return Math.floor(ms / size) * size
}

/** How many values of a sorted array are < `value` (binary search). */
function countBelow(sorted, value) {
  let low = 0
  let high = sorted.length
  while (low < high) {
    const middle = (low + high) >> 1
    if (sorted[middle] < value) low = middle + 1
    else high = middle
  }
  return low
}

/**
 * Value at `ratio` (0..1) of a ASCENDING sorted array — nearest-rank p95.
 *
 * The local statistics only need a coarse tail indicator over a few dozen
 * samples per endpoint, so the nearest-rank definition is enough: it never
 * interpolates, which would invent a duration that was never measured.
 */
function percentile(sorted, ratio) {
  if (!sorted.length) return 0
  const index = Math.min(sorted.length - 1, Math.max(0, Math.ceil(ratio * sorted.length) - 1))
  return sorted[index]
}

/**
 * The local-network log folded into buckets, ready to be matched with the
 * backend series.
 *
 * Built in ONE pass over the buffer (start times, finish times, per-bucket
 * counters and summed durations) plus binary searches per row: a live dashboard
 * recomputes this on every request, so it must not be O(rows × entries).
 *
 * Concurrency at the end of a bucket is derived from the two sorted arrays:
 * `started before end − finished before end` is exactly how many calls were
 * open at that instant. A call still in flight appears in the LAST bucket and,
 * once it settles, retroactively in every bucket it spanned.
 *
 * The path/method filters are honoured, so the overlay describes the endpoints
 * currently selected instead of always the whole tab.
 */
export const clientBuckets = computed(() => {
  const size = bucketSizeFor(state.series?.[0]?.period, GROUPING_MS[state.filters.grouping])
  const pathFilter = state.filters.path
  const methodFilter = state.filters.method

  /** bucketStart → { done, errors, totalMs, finished } */
  const done = new Map()
  const starts = []
  const finished = []
  let oldest = null

  for (const entry of telemetry.network) {
    if (pathFilter && entry.path !== pathFilter) continue
    if (methodFilter && entry.method !== methodFilter) continue

    const startedAt = Number(entry.startedAt || entry.ts) || 0
    if (!startedAt) continue

    starts.push(startedAt)
    if (oldest === null || startedAt < oldest) oldest = startedAt

    if (entry.pending) continue

    const finishedAt = Number(entry.finishedAt) || startedAt
    finished.push(finishedAt)

    const key = bucketStartOf(finishedAt, size)
    const bucket = done.get(key) || { done: 0, errors: 0, totalMs: 0, finished: 0 }
    bucket.done += 1
    // Summed here (one pass) so the tooltip can show the local average latency
    // of the bucket without a second scan over the buffer.
    bucket.totalMs += Number(entry.durationMs) || 0
    bucket.finished += 1
    if (entry.error || Number(entry.status) >= 500) bucket.errors += 1
    done.set(key, bucket)
  }

  starts.sort((a, b) => a - b)
  finished.sort((a, b) => b - a)

  return { size, oldest, starts, finished, done }
})

/** Local counters of an empty bucket (kept out of the render loop). */
const EMPTY_BUCKET = { done: 0, errors: 0, totalMs: 0, finished: 0 }

/** Chart input: period label + counts + latencies in ms + the local overlay. */
export const chartRows = computed(() => {
  const buckets = clientBuckets.value

  return (state.series || []).map((entry) => {
    const row = {
      label: formatPeriod(entry.period),
      calls: Number(entry.calls) || 0,
      errors: Number(entry.errors) || 0,
      avg_ms: Math.round((Number(entry.avg_duration_seconds) || 0) * 1000),
      p95_ms: Math.round((Number(entry.p95_duration_seconds) || 0) * 1000),
      // null ⇒ "no sample": the bucket predates the retained local window, so
      // Chart.js draws a gap instead of a zero that would read as idle.
      local_done: null,
      local_inflight: null,
      local_errors: null,
      // Not plotted: the tooltip footer prints it, so the bars stay countable.
      local_avg_ms: null
    }

    const start = periodToMs(entry.period)
    if (start === null || buckets.oldest === null) return row

    const end = start + buckets.size
    if (end <= buckets.oldest) return row

    const local = buckets.done.get(start) || EMPTY_BUCKET
    row.local_done = local.done
    row.local_errors = local.errors
    row.local_avg_ms = local.finished ? Math.round(local.totalMs / local.finished) : 0
    // Concurrency at the end of the bucket: open calls still hold a slot, so a
    // request in flight right now already counts in the last bucket.
    row.local_inflight = Math.max(
      0,
      countBelow(buckets.starts, end) - countBelow(buckets.finished, end)
    )
    return row
  })
})

/** False until the backend reported at least one call. */
export const hasData = computed(() => (Number(state.summary?.calls) || 0) > 0)

/* ── Client logs: socket events + local network ───────────────────────────── */

/**
 * Timestamp refreshed once per second while the view is mounted.
 *
 * An ELAPSED time cannot be derived from the log alone — it needs "now" — and
 * the in-flight table must keep counting for a request that never settles.
 * Instead of one timer per row, a single heartbeat drives every derived elapsed
 * value. It is REFERENCE COUNTED (`startClientClock`/`stopClientClock`) so a
 * remount cannot stack timers, and it stops with the panel: no timer survives a
 * closed view, the same contract as the Live polling.
 */
export const clientNow = ref(Date.now())

let clockTimer = null
let clockUsers = 0

/**
 * Starts the 1 s heartbeat (idempotent while it is already running).
 * @param {number} [intervalMs] Refresh period; clamped to a sane minimum.
 */
export function startClientClock(intervalMs = 1000) {
  clockUsers += 1
  clientNow.value = Date.now()
  if (clockTimer) return

  const period = Math.max(250, Number(intervalMs) || 1000)
  clockTimer = setInterval(() => {
    clientNow.value = Date.now()
  }, period)
}

/** Releases one heartbeat reference; the interval stops with the last one. */
export function stopClientClock() {
  clockUsers = Math.max(0, clockUsers - 1)
  if (clockUsers || !clockTimer) return
  clearInterval(clockTimer)
  clockTimer = null
}

/**
 * Raw browser-side logs, newest first, straight from `@/api/telemetry`.
 * They are independent from the backend aggregates: a failed reload does not
 * touch them, and they are cleared explicitly from the cards.
 */
export const socketEvents = computed(() => telemetry.socket)
export const localNetworkCalls = computed(() => telemetry.network)

/**
 * Cumulative socket counters (they survive the ring-buffer rotation, so the
 * totals never shrink while the session lasts) + the connection state.
 */
export const socketTotals = computed(() => {
  const counters = telemetry.socketCounters
  return {
    connected: telemetry.socketConnected,
    socketId: telemetry.socketId,
    total: counters.total,
    sent: counters.sent,
    received: counters.received,
    system: counters.system,
    errors: counters.errors,
    avgAckMs: counters.acked ? counters.ackTotalMs / counters.acked : 0,
    lastAt: telemetry.lastSocketAt
  }
})

/** Cumulative local-network counters, with the average measured latency. */
export const localNetworkTotals = computed(() => {
  const counters = telemetry.networkCounters
  const calls = counters.calls
  return {
    calls,
    errors: counters.errors,
    errorRate: calls ? counters.errors / calls : 0,
    avgMs: calls ? counters.totalMs / calls : 0,
    slow: counters.slow,
    /**
     * Calls open RIGHT NOW — the live value shown next to the chart title. It is
     * the same measure the purple "in flight" bar converges to at the last
     * bucket, read directly so the number does not wait for a refresh.
     */
    inFlight: telemetry.network.filter(entry => entry.pending).length,
    lastAt: telemetry.lastNetworkAt
  }
})

/**
 * Requests open AT THIS INSTANT — the realtime table.
 *
 * Longest first: the row at the top is the one that has been blocking this tab
 * the longest, which is exactly the order an operator wants when the UI stalls.
 * `elapsedMs` is derived from the heartbeat, so it keeps growing for a request
 * that never settles and disappears the moment it does (the entry stops being
 * `pending`).
 */
export const inFlightCalls = computed(() => {
  const now = Number(clientNow.value) || Date.now()

  return telemetry.network
    .filter(entry => entry.pending)
    .map((entry) => {
      const startedAt = Number(entry.startedAt || entry.ts) || 0
      return {
        id: entry.id,
        method: entry.method,
        path: entry.path,
        startedAt,
        elapsedMs: startedAt ? Math.max(0, now - startedAt) : 0
      }
    })
    .sort((a, b) => b.elapsedMs - a.elapsedMs || a.path.localeCompare(b.path))
})

/** Socket events grouped by name, busiest first. */
export const socketEventRows = computed(() => {
  const map = new Map()

  for (const entry of telemetry.socket) {
    const row = map.get(entry.event) || {
      event: entry.event,
      calls: 0,
      sent: 0,
      received: 0,
      errors: 0,
      ackTotalMs: 0,
      acked: 0,
      lastAt: 0
    }
    row.calls += 1
    if (entry.direction === 'out') row.sent += 1
    else if (entry.direction === 'in') row.received += 1
    if (entry.error) row.errors += 1
    if (entry.durationMs !== null) {
      row.ackTotalMs += entry.durationMs
      row.acked += 1
    }
    row.lastAt = Math.max(row.lastAt, entry.ts || 0)
    map.set(entry.event, row)
  }

  return [...map.values()]
    .map(row => ({ ...row, avgAckMs: row.acked ? row.ackTotalMs / row.acked : 0 }))
    .sort((a, b) => b.calls - a.calls)
})

/** Numeric value used to order the local-network statistics table. */
const LOCAL_SORT_KEYS = {
  time: row => row.totalMs,
  calls: row => row.calls,
  avg: row => row.avgMs,
  p95: row => row.p95Ms,
  max: row => row.maxMs,
  errors: row => row.errors,
  last: row => row.lastAt
}

/**
 * Local calls grouped by method + path — the "which requests cost the most and
 * which repeat the most" table.
 *
 * Per endpoint it reports BOTH dimensions, because they fail differently:
 *   • time  — `totalMs` and `share` (its part of the local time in the retained
 *     hour): one slow endpoint can dominate the whole tab;
 *   • repeat — `calls` and `callsPerMin`: a fast endpoint called hundreds of
 *     times still saturates the browser and the API.
 * `avg`/`p95`/`max` describe the shape of the latency, `p95` being the one that
 * catches the repeated slow tail that an average hides.
 *
 * In-flight calls are COUNTED (`open`) but never averaged — they have no final
 * duration yet, and including them would drag the numbers down while a request
 * is merely still running.
 */
export const localNetworkRows = computed(() => {
  const now = Number(clientNow.value) || Date.now()

  const map = new Map()
  let oldest = null
  let totalTime = 0

  for (const entry of telemetry.network) {
    const startedAt = Number(entry.startedAt || entry.ts) || 0
    if (startedAt && (oldest === null || startedAt < oldest)) oldest = startedAt

    const key = `${entry.method} ${entry.path}`
    const row = map.get(key) || {
      key,
      method: entry.method,
      path: entry.path,
      calls: 0,
      errors: 0,
      open: 0,
      totalMs: 0,
      maxMs: 0,
      minMs: 0,
      lastStatus: 0,
      lastAt: 0,
      durations: []
    }

    // Still open: listed by the realtime table, counted here, excluded from the
    // latency statistics.
    if (entry.pending) {
      row.open += 1
      map.set(key, row)
      continue
    }

    const duration = Number(entry.durationMs) || 0
    row.calls += 1
    row.totalMs += duration
    totalTime += duration
    row.maxMs = Math.max(row.maxMs, duration)
    if (!row.minMs || duration < row.minMs) row.minMs = duration
    row.durations.push(duration)
    if (entry.error || Number(entry.status) >= 500) row.errors += 1

    const ts = Number(entry.ts) || 0
    if (ts >= row.lastAt) {
      row.lastAt = ts
      row.lastStatus = Number(entry.status) || 0
    }

    map.set(key, row)
  }

  // Rates are per minute: the log keeps one hour, but a fresh tab may hold only
  // a few seconds — without the floor a single call would read as 60 calls/min.
  const windowMs = Math.max(60 * 1000, now - (oldest === null ? now : oldest))

  const rows = [...map.values()].map((row) => {
    // `durations` is discarded after the sort: it is the only per-call array we
    // keep, and only long enough to read the p95 once.
    const durations = row.durations.sort((a, b) => a - b)
    const calls = row.calls

    return {
      key: row.key,
      method: row.method,
      path: row.path,
      calls,
      open: row.open,
      errors: row.errors,
      errorRate: calls ? row.errors / calls : 0,
      totalMs: row.totalMs,
      avgMs: calls ? row.totalMs / calls : 0,
      minMs: row.minMs,
      maxMs: row.maxMs,
      p95Ms: percentile(durations, 0.95),
      callsPerMin: calls / (windowMs / 60_000),
      share: totalTime ? row.totalMs / totalTime : 0,
      lastStatus: row.lastStatus,
      lastAt: row.lastAt
    }
  })

  const value = LOCAL_SORT_KEYS[state.localSortBy] || LOCAL_SORT_KEYS.time
  return rows.sort((a, b) => value(b) - value(a) || a.path.localeCompare(b.path))
})

/** Empties one of the client-side logs (or both). */
export function clearClientLogs(scope = 'all') {
  clearClientTelemetry(scope)
}

/* ── Diagnostics ──────────────────────────────────────────────────────────── */
const TONE_ORDER = { error: 0, warning: 1, info: 2 }

/**
 * Deterministic rules over the current aggregate — the "what should I look at
 * first" list. Every entry is derived from a measured value; nothing here is a
 * guess.
 */
export const issues = computed(() => {
  const list = []
  const summary = state.summary || {}
  const calls = Number(summary.calls) || 0

  if (!calls) return list

  const errorRate = Number(summary.error_rate) || 0
  const p95 = Number(summary.p95_duration_seconds) || 0
  const avg = Number(summary.avg_duration_seconds) || 0

  if (errorRate >= 0.05) {
    list.push({
      id: 'errors',
      tone: 'error',
      icon: 'fa-circle-exclamation',
      title: `${fmtPct(errorRate)} of the calls failed`,
      detail: `${Number(summary.errors) || 0} of ${fmtNum(calls)} calls returned an error or a 5xx.`
    })
  } else if (errorRate >= 0.01) {
    list.push({
      id: 'errors',
      tone: 'warning',
      icon: 'fa-triangle-exclamation',
      title: `Error rate at ${fmtPct(errorRate)}`,
      detail: 'Above the 1% threshold — check the failed calls list.'
    })
  }

  if (p95 >= 2) {
    list.push({
      id: 'p95',
      tone: 'error',
      icon: 'fa-gauge-high',
      title: `p95 latency is ${fmtMs(p95)}`,
      detail: '1 in 20 requests waits longer than this — users feel it.'
    })
  } else if (p95 >= 0.8) {
    list.push({
      id: 'p95',
      tone: 'warning',
      icon: 'fa-gauge-high',
      title: `p95 latency is ${fmtMs(p95)}`,
      detail: 'The slow tail is growing. Look at the slowest endpoints.'
    })
  }

  if (avg >= 0.5) {
    list.push({
      id: 'avg',
      tone: 'warning',
      icon: 'fa-clock',
      title: `Average latency is ${fmtMs(avg)}`,
      detail: 'Every request pays this — it multiplies the whole UI.'
    })
  }

  const worst = endpointRows.value[0]
  const worstP95 = Number(worst?.p95_duration_seconds) || 0
  if (worst && worstP95 >= 0.8) {
    list.push({
      id: 'endpoint',
      tone: worstP95 >= 2 ? 'error' : 'warning',
      icon: 'fa-route',
      title: `Slowest endpoint: ${worst.path}`,
      detail: `p95 ${fmtMs(worstP95)} over ${fmtNum(worst.calls)} calls.`
    })
  }

  const serverErrors = statusRows.value.filter(row => row.code >= 500)
  if (serverErrors.length) {
    const total = serverErrors.reduce((sum, row) => sum + (Number(row.calls) || 0), 0)
    list.push({
      id: 'status',
      tone: 'error',
      icon: 'fa-server',
      title: `${fmtNum(total)} server error response(s)`,
      detail: serverErrors.map(row => `${row.code}: ${fmtNum(row.calls)}`).join(' · ')
    })
  }

  // Client-side signals: a dropped socket pauses every live update, and a
  // failing LAN hop is invisible to the server-side aggregates.
  const socketCounters = telemetry.socketCounters
  if (socketCounters.total && !telemetry.socketConnected) {
    list.push({
      id: 'socket-offline',
      tone: 'warning',
      icon: 'fa-plug-circle-xmark',
      title: 'Socket disconnected',
      detail: 'Live updates are paused until this tab reconnects.'
    })
  }
  if (socketCounters.errors) {
    list.push({
      id: 'socket-errors',
      tone: 'error',
      icon: 'fa-bolt',
      title: `${fmtNum(socketCounters.errors)} socket event error(s)`,
      detail: 'An event was emitted while disconnected or the connection failed.'
    })
  }
  if (telemetry.networkCounters.errors) {
    list.push({
      id: 'local-network',
      tone: 'warning',
      icon: 'fa-network-wired',
      title: `${fmtNum(telemetry.networkCounters.errors)} local network call(s) failed`,
      detail: `Measured by this browser over ${fmtNum(telemetry.networkCounters.calls)} call(s).`
    })
  }

  // Realtime: one request open for seconds is the most concrete "stuck" signal
  // this tab can produce, and it is the row the in-flight table pins on top.
  const longest = inFlightCalls.value[0]
  if (longest && longest.elapsedMs >= 5_000) {
    list.push({
      id: 'local-inflight',
      tone: longest.elapsedMs >= 15_000 ? 'error' : 'warning',
      icon: 'fa-hourglass-half',
      title: `${longest.method} ${longest.path} has been open for ${fmtElapsed(longest.elapsedMs)}`,
      detail: `${fmtNum(inFlightCalls.value.length)} request(s) in flight in this tab right now.`
    })
  }

  return list.sort((a, b) => TONE_ORDER[a.tone] - TONE_ORDER[b.tone])
})

/* ── Formatting ───────────────────────────────────────────────────────────── */

/**
 * Bucket label → readable axis label.
 *
 * Backend periods look like "YYYY-MM-DD", "YYYY-MM-DD HH:00", "YYYY-MM-DD
 * HH:MM" or "YYYY-MM-DD HH:MM:SS" (not ISO-8601), so they are parsed by hand:
 *   • day          → MM-DD
 *   • hour/minute  → keep the day when the bucket starts a new hour, so a
 *                    multi-day range stays readable
 *   • second level → time only (HH:MM:SS): at 5/10/30 s the date would repeat
 *                    on every tick and the axis would become unreadable
 */
export function formatPeriod(period) {
  const value = String(period || '')
  if (!value) return ''
  const [date, time] = value.split(' ')
  if (!time) return date.slice(5) // MM-DD
  const parts = time.split(':')
  if (parts.length >= 3) return time // HH:MM:SS
  // Hourly buckets end in ":00": keep the day so a multi-day range is readable.
  return time.endsWith(':00') ? `${date.slice(5)} ${time}` : time
}

/** Seconds → latency string ("0 ms", "480 ms", "1.24 s"). */
export function fmtMs(seconds) {
  const value = Number(seconds) || 0
  if (!value) return '0 ms'
  if (value < 1) return `${Math.round(value * 1000)} ms`
  return `${value.toFixed(2)} s`
}

/**
 * MILLISECONDS → elapsed string ("840 ms", "3.42 s", "1m 05s").
 *
 * The realtime table works in milliseconds (it measures a live counter), unlike
 * the stored durations which are seconds — hence the separate formatter.
 */
export function fmtElapsed(ms) {
  const value = Math.max(0, Number(ms) || 0)
  if (value < 1000) return `${Math.round(value)} ms`
  if (value < 60_000) return `${(value / 1000).toFixed(2)} s`
  const minutes = Math.floor(value / 60_000)
  const seconds = Math.floor((value % 60_000) / 1000)
  return `${minutes}m ${String(seconds).padStart(2, '0')}s`
}

/** Seconds → accumulated duration ("90 s", "5m 30s", "2h 10m"). */
export function fmtDuration(seconds) {
  const value = Number(seconds) || 0
  if (!value) return '0 s'
  if (value < 60) return `${value.toFixed(1)} s`
  const minutes = Math.floor(value / 60)
  if (minutes < 60) return `${minutes}m ${Math.round(value % 60)}s`
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
}

/** 0..1 ratio → "%". */
export function fmtPct(ratio) {
  const value = (Number(ratio) || 0) * 100
  if (!value) return '0%'
  return `${value < 1 ? value.toFixed(2) : value.toFixed(1)}%`
}

/** Compact integers ("1.2K", "3.4M"). */
export function fmtNum(value) {
  const num = Number(value) || 0
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`
  return String(num)
}

/** Unix seconds (stored on the event) → readable timestamp. */
export function fmtTimestamp(unixSeconds) {
  const seconds = Number(unixSeconds) || 0
  if (!seconds) return '—'
  const date = new Date(seconds * 1000)
  if (isNaN(date.getTime())) return '—'
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`
}

/**
 * Epoch MILLISECONDS → "HH:MM:SS".
 * The client-side logs are stamped with `Date.now()`, unlike the backend events
 * which carry unix seconds (see `fmtTimestamp`), and in a live table the time of
 * day is what identifies a tick.
 */
export function fmtClock(ms) {
  const value = Number(ms) || 0
  if (!value) return '—'
  const date = new Date(value)
  if (isNaN(date.getTime())) return '—'
  return date.toLocaleTimeString()
}

/** Tone for an error ratio. */
export function errorTone(ratio) {
  const value = Number(ratio) || 0
  if (value >= 0.05) return 'error'
  if (value >= 0.01) return 'warning'
  return 'success'
}

/** Tone for a latency in seconds. */
export function latencyTone(seconds) {
  const value = Number(seconds) || 0
  if (value >= 2) return 'error'
  if (value >= 0.5) return 'warning'
  return 'success'
}

/** Tone for an HTTP status code. */
export function statusTone(code) {
  const value = Number(code) || 0
  if (value >= 500) return 'error'
  if (value >= 400) return 'warning'
  if (value >= 300) return 'info'
  return 'success'
}

/* ── Composable accessor ──────────────────────────────────────────────────── */
export function useApiMonitoring() {
  return {
    state,
    // configuration
    GROUPINGS,
    DEFAULT_GROUPING,
    GROUPING_MS,
    REFRESH_INTERVALS,
    DATE_PRESETS,
    METHODS,
    CHART_METRICS,
    CLIENT_CHART_METRICS,
    chartMetrics,
    LOCAL_SORTS,
    SLOWEST_LIMIT,
    ERRORS_LIMIT,
    TOP_ENDPOINTS,
    TOP_SLOWEST,
    TOP_CLIENT_ROWS,
    // date helpers
    todayISO,
    daysAgoISO,
    // filters
    setFilter,
    applyFilters,
    applyPreset,
    clearFilters,
    filtersActive,
    activePreset,
    groupingLabel,
    setLocalSortBy,
    // loading
    loadAll,
    loadDates,
    setAllUsers,
    // polling
    setLive,
    setIntervalSeconds,
    stopLive,
    // realtime clock (in-flight elapsed)
    clientNow,
    startClientClock,
    stopClientClock,
    // derived
    endpointRows,
    statusRows,
    chartRows,
    clientBuckets,
    hasData,
    issues,
    // client logs (socket events + local network)
    socketEvents,
    localNetworkCalls,
    socketTotals,
    localNetworkTotals,
    socketEventRows,
    inFlightCalls,
    localNetworkRows,
    clearClientLogs,
    // formatting
    formatPeriod,
    periodToMs,
    fmtMs,
    fmtElapsed,
    fmtDuration,
    fmtPct,
    fmtNum,
    fmtTimestamp,
    fmtClock,
    errorTone,
    latencyTone,
    statusTone
  }
}

export default useApiMonitoring