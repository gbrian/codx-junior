/**
 * ============================================================================
 * Infrastructure — live monitoring samples + refresh scheduler.
 * ----------------------------------------------------------------------------
 * The Docker API exposes a *snapshot* (`GET /api/infra/summary`), not a history
 * series, so the charts are fed from a rolling buffer sampled on the client:
 * every refresh appends ONE point, the oldest one is dropped once the buffer is
 * full. That keeps the graphs honest — nothing is interpolated or invented — and
 * it needs no backend change.
 *
 * WHY A SEPARATE MODULE
 * ---------------------
 * `useInfra.js` owns the Docker snapshot, the tabs and every action. This module
 * only owns the *time* dimension (how often we poll, and what we remember), so a
 * chart can be added or dropped without touching the shared store.
 *
 * LIVE BY DEFAULT
 * ---------------
 * `monitoring.live` starts as `true`: the Infrastructure view is a monitoring
 * surface, so polling is the expected behaviour as soon as it mounts. Polling is
 * still stopped on unmount (`stopMonitoring`) and resumed on the next mount, so
 * the preference survives navigation while no timer burns in the background.
 * ============================================================================
 */
import { computed, reactive, watch } from 'vue'
import { state, loadAll } from './useInfra'

/** Intervals offered by the header selector (seconds). */
export const REFRESH_INTERVALS = [
  { value: 2, label: '2s' },
  { value: 5, label: '5s' },
  { value: 10, label: '10s' },
  { value: 30, label: '30s' },
  { value: 60, label: '1 min' }
]

/** Requested default: refresh every 5 seconds. */
export const DEFAULT_REFRESH_SECONDS = 5

/**
 * Samples kept in memory. At the default 5s cadence 120 points span ~10 minutes
 * — long enough to spot a spike, short enough to stay readable in one chart.
 */
export const MONITORING_MAX_SAMPLES = 120

/**
 * The tab descriptor lives here (not in `useInfra.TABS`) because the store is
 * shared by every infra panel and is not the owner of the charts.
 */
export const MONITORING_TAB = { id: 'monitoring', label: 'Monitoring', icon: 'fa-chart-line' }

export const monitoring = reactive({
  live: true,
  interval: DEFAULT_REFRESH_SECONDS,
  samples: []
})

let timer = null

/* ── Helpers ──────────────────────────────────────────────────────────────── */
function round1(value) {
  return Math.round((Number(value) || 0) * 10) / 10
}

/** Percentage of `used` over `total` with one decimal (0 when total is unknown). */
function pct(used, total) {
  const t = Number(total) || 0
  if (!t) return 0
  return round1((Number(used) || 0) / t * 100)
}

function intervalMs() {
  const seconds = Number(monitoring.interval)
  const safe = REFRESH_INTERVALS.some(o => o.value === seconds) ? seconds : DEFAULT_REFRESH_SECONDS
  return Math.max(1, safe) * 1000
}

/* ── Sample buffer ────────────────────────────────────────────────────────── */

/**
 * Appends one point taken from a host snapshot.
 *
 * Accepts an explicit `summary` (the watcher below passes the fresh one); when
 * omitted the current `state.summary` is used. Returns the stored sample so a
 * caller can assert on it.
 */
export function recordSample(summary = state.summary) {
  if (!summary) return null

  const counts = summary.counts || {}
  const sample = {
    t: new Date().toISOString(),
    cpu: round1(summary.cpu_pct),
    mem: pct(summary.mem_used, summary.mem_total),
    disk: pct(summary.disk_used, summary.disk_total),
    mem_used: Number(summary.mem_used) || 0,
    mem_total: Number(summary.mem_total) || 0,
    running: Number(counts.running) || 0,
    stopped: Number(counts.stopped) || 0,
    paused: Number(counts.paused) || 0,
    restarting: Number(counts.restarting) || 0,
    unhealthy: Number(counts.unhealthy) || 0,
    total: Number(counts.total) || 0,
    images: Number(counts.images) || 0,
    volumes: Number(counts.volumes) || 0,
    networks: Number(counts.networks) || 0
  }

  monitoring.samples.push(sample)
  const excess = monitoring.samples.length - MONITORING_MAX_SAMPLES
  if (excess > 0) monitoring.samples.splice(0, excess)
  return sample
}

/** Empties the buffer (manual "Reset", or after switching to another host). */
export function clearSamples() {
  monitoring.samples.splice(0, monitoring.samples.length)
}

export const sampleCount = computed(() => monitoring.samples.length)
export const lastSample = computed(
  () => monitoring.samples[monitoring.samples.length - 1] || null
)

/* ── Polling ──────────────────────────────────────────────────────────────── */
async function poll() {
  await loadAll({ silent: true })
}

/**
 * (Re)starts the poll loop. Honours `monitoring.live` and `monitoring.interval`,
 * so it is safe to call after changing either one.
 */
export function startMonitoring() {
  stopMonitoring()
  state.autoRefresh = monitoring.live
  if (!monitoring.live) return
  timer = setInterval(poll, intervalMs())
}

/** Stops the loop without touching the `live` preference (used on unmount). */
export function stopMonitoring() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

/** Header "Live" switch: flips the preference and starts/stops the loop. */
export function setLive(on) {
  monitoring.live = !!on
  state.autoRefresh = monitoring.live
  if (monitoring.live) startMonitoring()
  else stopMonitoring()
}

/** Header interval selector: reschedules when live, otherwise just remembers. */
export function setRefreshInterval(seconds) {
  const value = Number(seconds)
  monitoring.interval = REFRESH_INTERVALS.some(o => o.value === value)
    ? value
    : DEFAULT_REFRESH_SECONDS
  if (monitoring.live) startMonitoring()
}

/* ── Watchers (module scope: one instance for the whole app) ──────────────── */

/**
 * Every successful `loadAll()` replaces `state.summary` with a NEW object, so
 * watching the reference is enough to record exactly one point per refresh —
 * no matter who triggered it (poll loop, Refresh button, container action…).
 */
watch(() => state.summary, (summary) => {
  if (summary) recordSample(summary)
})

/** A different host is a different machine: previous points are meaningless. */
watch(() => state.hostId, () => {
  clearSamples()
})

export default monitoring