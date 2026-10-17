/**
 * ============================================================================
 * Infrastructure (Docker) — shared view state, selectors and actions.
 * ----------------------------------------------------------------------------
 * Single reactive store: every infra component (InfraView, the per-tab panels
 * and the container detail overlay) reads and mutates the SAME state, so an
 * action taken in one place is instantly reflected everywhere (counts, tables,
 * overlay…). Nothing here talks HTTP directly — everything goes through
 * `API.infra` (see src/api/modules/infra.js), which is mock-backed until the
 * backend implements /api/infra/*.
 * ============================================================================
 */
import { computed, reactive } from 'vue'
import { API } from '../../api/api'

/* ── Tabs ─────────────────────────────────────────────────────────────────── */
export const TABS = [
  { id: 'containers', label: 'Containers', icon: 'fa-cube' },
  { id: 'stacks', label: 'Stacks', icon: 'fa-layer-group' },
  { id: 'images', label: 'Images', icon: 'fa-hard-drive' },
  { id: 'volumes', label: 'Volumes', icon: 'fa-database' },
  { id: 'networks', label: 'Networks', icon: 'fa-network-wired' },
  { id: 'events', label: 'Events', icon: 'fa-bolt' },
  { id: 'maintenance', label: 'Maintenance', icon: 'fa-broom' }
]

const POLL_MS = 5000

let pollTimer = null
let toastSeq = 0
/**
 * Monotonic token for container-detail openings.
 *
 * `openContainer()` is async: the detail request resolves AFTER the overlay is
 * already visible. Without a token, a second open (or a slow first one) can
 * commit its result last and silently restore the default tab — which is
 * exactly why clicking "Logs" used to end up on "Overview".
 */
let openSeq = 0

/* ── State ────────────────────────────────────────────────────────────────── */
export const state = reactive({
  // loading | ready | error
  status: 'idle',
  error: null,
  lastUpdated: null,

  hosts: [],
  hostId: 'host-local',
  summary: null,

  containers: [],
  stacks: [],
  images: [],
  volumes: [],
  networks: [],
  events: [],

  route: 'containers',
  autoRefresh: false,
  filters: {
    q: '',
    state: 'all',
    stack: 'all',
    sort: 'name'
  },

  // container detail overlay (rendered as a centered modal, see ContainerDrawer.vue)
  drawerOpen: false,
  selectedContainerId: null,
  detail: null,
  detailTab: 'overview',
  logs: [],
  logsLoading: false,
  stats: null,
  statsLoading: false,

  // maintenance / cleanup (see MaintenancePanel.vue)
  maintenanceOlderThanDays: 30,
  maintenanceBusy: null, // id of the prune target / resource group in flight

  modal: null,
  toasts: []
})

/* ── Formatting helpers ───────────────────────────────────────────────────── */
export function fmtBytes(bytes, digits = 1) {
  if (bytes == null) return '—'
  const value = Number(bytes)
  if (!isFinite(value)) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  let n = Math.abs(value)
  let i = 0
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024
    i++
  }
  return `${(value < 0 ? -n : n).toFixed(i === 0 ? 0 : digits)} ${units[i]}`
}

export function fmtTime(iso) {
  if (!iso) return '—'
  const date = iso instanceof Date ? iso : new Date(iso)
  if (isNaN(date.getTime())) return '—'
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function fmtUptime(seconds) {
  if (seconds == null) return '—'
  const total = Math.max(0, Math.floor(seconds))
  const d = Math.floor(total / 86400)
  const h = Math.floor((total % 86400) / 3600)
  const m = Math.floor((total % 3600) / 60)
  if (d) return `${d}d ${h}h`
  if (h) return `${h}h ${m}m`
  if (m) return `${m}m`
  return `${total}s`
}

/** Maps a 0-100 percentage to a meter tone name. */
export function tone(value, warn = 80, error = 90) {
  const v = Number(value) || 0
  if (v >= error) return 'error'
  if (v >= warn) return 'warning'
  return 'success'
}

/** daisyUI badge tone for a container state. */
export function stateTone(containerState) {
  return {
    running: 'success',
    restarting: 'warning',
    paused: 'info',
    exited: 'ghost',
    created: 'ghost',
    dead: 'error'
  }[containerState] || 'ghost'
}

/** daisyUI dot color for a container state. */
export function dotClass(containerState) {
  return {
    running: 'bg-success',
    restarting: 'bg-warning',
    paused: 'bg-info',
    exited: 'bg-base-content/30',
    created: 'bg-base-content/30',
    dead: 'bg-error'
  }[containerState] || 'bg-base-content/30'
}

/** daisyUI badge tone for a health status. */
export function healthTone(health) {
  return { healthy: 'success', unhealthy: 'error', starting: 'warning' }[health] || 'ghost'
}

/** Human readable state, falling back to docker's own STATUS text. */
export function stateLabel(container) {
  if (!container) return '—'
  return container.status_text || container.state || '—'
}

/* ── Sorting ──────────────────────────────────────────────────────────────── */
function sortContainers(list, sort) {
  const arr = [...list]
  if (sort === 'cpu') return arr.sort((a, b) => (b.cpu_pct || 0) - (a.cpu_pct || 0))
  if (sort === 'mem') return arr.sort((a, b) => (b.mem_used || 0) - (a.mem_used || 0))
  if (sort === 'created') return arr.sort((a, b) => new Date(b.created) - new Date(a.created))
  return arr.sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')))
}

function sortImages(list, sort) {
  const arr = [...list]
  if (sort === 'created') return arr.sort((a, b) => new Date(b.created) - new Date(a.created))
  if (sort === 'mem') return arr.sort((a, b) => (b.size || 0) - (a.size || 0))
  return arr.sort((a, b) => `${a.repo}:${a.tag}`.localeCompare(`${b.repo}:${b.tag}`))
}

function sortVolumes(list, sort) {
  const arr = [...list]
  if (sort === 'mem') return arr.sort((a, b) => (b.size || 0) - (a.size || 0))
  if (sort === 'created') return arr.sort((a, b) => new Date(b.created) - new Date(a.created))
  return arr.sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')))
}

/* ── Selectors ────────────────────────────────────────────────────────────── */
function matches(values, term) {
  if (!term) return true
  return values.some(value => String(value ?? '').toLowerCase().includes(term))
}

export const filteredList = computed(() => {
  const term = (state.filters.q || '').trim().toLowerCase()
  const stateFilter = state.filters.state
  const stack = state.filters.stack
  const sort = state.filters.sort

  if (state.route === 'containers') {
    const list = state.containers.filter((c) => {
      if (stateFilter === 'unhealthy') {
        if (c.health !== 'unhealthy') return false
      } else if (stateFilter !== 'all' && c.state !== stateFilter) {
        return false
      }
      if (stack !== 'all' && c.stack !== stack) return false
      return matches([c.name, c.image, c.service, c.stack, c.short, c.id], term)
    })
    return sortContainers(list, sort)
  }

  if (state.route === 'stacks') {
    return state.stacks.filter((s) => {
      if (stack !== 'all' && s.name !== stack) return false
      return matches([s.name, s.path, s.status], term)
    })
  }

  if (state.route === 'images') {
    const list = state.images.filter(i => matches([i.repo, i.tag, i.id], term))
    return sortImages(list, sort)
  }

  if (state.route === 'volumes') {
    const list = state.volumes.filter(v => matches([v.name, v.driver, v.stack, v.mountpoint], term))
    return sortVolumes(list, sort)
  }

  if (state.route === 'networks') {
    return state.networks.filter(n => matches([n.name, n.driver, n.subnet], term))
  }

  if (state.route === 'events') {
    return state.events
      .filter(e => matches([e.actor, e.action, e.type], term))
      .slice()
      .sort((a, b) => new Date(b.ts) - new Date(a.ts))
  }

  return []
})

/* ── Maintenance (cleanup candidates) ─────────────────────────────────────── */
const DAY_MS = 86400000

/** Whole days between `iso` and now; null when the value is missing/invalid. */
export function ageDays(iso) {
  if (!iso) return null
  const t = new Date(iso).getTime()
  if (isNaN(t)) return null
  return Math.max(0, Math.floor((Date.now() - t) / DAY_MS))
}

/**
 * Prune targets offered by the maintenance panel. The `id` is sent verbatim to
 * `POST /api/infra/maintenance/prune` as `{ target }`.
 */
export const PRUNE_TARGETS = [
  { id: 'images', label: 'Unused images', icon: 'fa-hard-drive',
    desc: 'Dangling layers and images no container references.', danger: false },
  { id: 'volumes', label: 'Unused volumes', icon: 'fa-database',
    desc: 'Volumes no container mounts — their data is destroyed.', danger: true },
  { id: 'networks', label: 'Unused networks', icon: 'fa-network-wired',
    desc: 'Custom networks that no container is attached to.', danger: false },
  { id: 'build_cache', label: 'Build cache', icon: 'fa-hammer',
    desc: 'Layer cache kept by docker build.', danger: false },
  { id: 'system', label: 'Everything', icon: 'fa-broom',
    desc: 'Dangling images, unused volumes + networks, build cache.', danger: true }
]

const PRUNE_META = PRUNE_TARGETS.reduce((acc, t) => { acc[t.id] = t; return acc }, {})

/** Removes the oldest first, keeping unknown ages at the end. */
function byAge(items) {
  return items.sort((a, b) => {
    if (a.ageDays == null && b.ageDays == null) return a.name.localeCompare(b.name)
    if (a.ageDays == null) return 1
    if (b.ageDays == null) return -1
    return b.ageDays - a.ageDays
  })
}

function sumBytes(items) {
  return items.reduce((total, item) => total + (item.size || 0), 0)
}

/**
 * Cleanup candidates derived from the CURRENT host snapshot.
 *
 * Deliberately computed from `state` (not fetched): the maintenance view must
 * agree with what the Containers / Images / Volumes / Networks tabs show, and
 * it must stay useful even when the daemon-side maintenance endpoints are not
 * implemented. Nothing here mutates — removal always goes through the API.
 *
 * Every item carries the same shape so MaintenancePanel stays dumb:
 *   { key, name, subtitle, detail, size, created, ageDays, state }
 */
export const maintenanceReport = computed(() => {
  const days = Number(state.maintenanceOlderThanDays) || 0
  // Unknown age ("null") is always surfaced — hiding it would silently drop
  // resources the daemon did not date.
  const keep = (item) => days <= 0 || item.ageDays == null || item.ageDays >= days

  const containers = byAge(state.containers
    .filter(c => ['exited', 'created', 'dead'].includes(c.state))
    .map(c => ({
      key: c.id,
      name: c.name,
      subtitle: c.image,
      detail: stateLabel(c),
      size: 0,
      created: c.created,
      ageDays: ageDays(c.created),
      state: c.state
    }))
    .filter(keep))

  const images = byAge(state.images
    .filter(i => i.dangling || !i.containers)
    .map(i => ({
      key: i.id,
      name: `${i.repo && i.repo !== '<none>' ? i.repo : i.id}${i.tag && i.tag !== '<none>' ? ':' + i.tag : ''}`,
      subtitle: i.id,
      detail: i.dangling ? 'Dangling image layer' : 'Not referenced by any container',
      size: i.size || 0,
      created: i.created,
      ageDays: ageDays(i.created),
      state: i.dangling ? 'dangling' : 'unused'
    }))
    .filter(keep))

  const volumes = byAge(state.volumes
    .filter(v => !v.in_use)
    .map(v => ({
      key: v.name,
      name: v.name,
      subtitle: v.mountpoint,
      detail: v.anonymous ? 'Anonymous volume' : 'Not mounted by any container',
      size: v.size || 0,
      created: v.created,
      ageDays: ageDays(v.created),
      state: v.anonymous ? 'anonymous' : 'unused'
    }))
    .filter(keep))

  const networks = byAge(state.networks
    .filter(n => !(n.containers || []).length && !['host', 'none', 'bridge'].includes(n.name))
    .map(n => ({
      key: n.id,
      name: n.name,
      subtitle: `${n.driver} · ${n.subnet}`,
      detail: 'No attached containers',
      size: 0,
      created: n.created,
      ageDays: ageDays(n.created),
      state: 'unused'
    }))
    .filter(keep))

  const groups = [
    { id: 'containers', label: 'Stopped containers', icon: 'fa-cube',
      hint: 'Non-running containers keep their writable layer and pin their image.',
      items: containers, size: sumBytes(containers) },
    { id: 'images', label: 'Unused images', icon: 'fa-hard-drive',
      hint: 'Dangling layers and images that no container references.',
      items: images, size: sumBytes(images) },
    { id: 'volumes', label: 'Unused volumes', icon: 'fa-database',
      hint: 'Volumes that no container mounts. Their data is destroyed on removal.',
      items: volumes, size: sumBytes(volumes) },
    { id: 'networks', label: 'Unused networks', icon: 'fa-network-wired',
      hint: 'Custom networks without attached containers.',
      items: networks, size: sumBytes(networks) }
  ]

  const totalItems = groups.reduce((total, group) => total + group.items.length, 0)
  const reclaimable = groups.reduce((total, group) => total + group.size, 0)

  return { groups, totalItems, reclaimable, olderThanDays: days }
})

export function tabCount(tabId) {
  switch (tabId) {
    case 'containers': return state.containers.length
    case 'stacks': return state.stacks.length
    case 'images': return state.images.length
    case 'volumes': return state.volumes.length
    case 'networks': return state.networks.length
    case 'events': return state.events.length
    case 'maintenance': return maintenanceReport.value.totalItems
    default: return 0
  }
}

/* ── Toasts & modals ──────────────────────────────────────────────────────── */
export function pushToast({ text, kind = 'info', timeout = 4000 }) {
  const id = ++toastSeq
  state.toasts.push({ id, text, kind })
  setTimeout(() => {
    const ix = state.toasts.findIndex(t => t.id === id)
    if (ix >= 0) state.toasts.splice(ix, 1)
  }, timeout)
}

export function confirm({ title, html, confirmText = 'Confirm', danger = false, onConfirm }) {
  state.modal = { type: 'confirm', title, html, confirmText, danger, onConfirm }
}

export function showJson(title, data) {
  let json
  try {
    json = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
  } catch (err) {
    json = String(data)
  }
  state.modal = { type: 'json', title, json }
}

export function closeModal() {
  state.modal = null
}

/* ── Loading ──────────────────────────────────────────────────────────────── */
export async function loadHosts() {
  try {
    const { hosts } = await API.infra.hosts()
    state.hosts = hosts || []
    if (!state.hosts.find(h => h.id === state.hostId)) {
      state.hostId = state.hosts[0]?.id || 'host-local'
    }
  } catch (err) {
    pushToast({ text: `Could not list Docker hosts: ${err?.message || err}`, kind: 'error' })
  }
}

export async function loadAll({ silent = false } = {}) {
  const host = state.hostId
  if (!silent) {
    state.error = null
    if (state.status !== 'ready') state.status = 'loading'
  }

  try {
    const [summary, containers, stacks, images, volumes, networks, events] = await Promise.all([
      API.infra.summary(host),
      API.infra.containers({ host }),
      API.infra.stacks(host),
      API.infra.images(host),
      API.infra.volumes(host),
      API.infra.networks(host),
      API.infra.events(host)
    ])

    state.summary = summary || null
    state.containers = containers?.containers || []
    state.stacks = stacks?.stacks || []
    state.images = images?.images || []
    state.volumes = volumes?.volumes || []
    state.networks = networks?.networks || []
    state.events = events?.events || []
    state.lastUpdated = new Date()
    state.status = 'ready'
    state.error = null
  } catch (err) {
    state.error = err?.message || String(err)
    if (!silent) state.status = 'error'
  }
}

/* ── Filters / navigation ─────────────────────────────────────────────────── */
export function setRoute(route) {
  state.route = route
  closeDrawer()
}

export function setHost(hostId) {
  if (!hostId || hostId === state.hostId) return
  state.hostId = hostId
  state.summary = null
  closeDrawer()
  loadAll()
}

export function setFilter(patch = {}) {
  Object.assign(state.filters, patch)
}

/** Minimum age (days) a resource must have to be listed by the maintenance view. */
export function setMaintenanceAge(days) {
  state.maintenanceOlderThanDays = Math.max(0, Number(days) || 0)
}

/* ── Live refresh ─────────────────────────────────────────────────────────── */
function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

export function toggleLive(on) {
  state.autoRefresh = !!on
  stopPolling()
  if (!state.autoRefresh) return
  pollTimer = setInterval(() => {
    loadAll({ silent: true })
  }, POLL_MS)
}

/* ── Container actions ────────────────────────────────────────────────────── */
const ACTION_META = {
  start: { label: 'Start', danger: false, text: 'the container will be started.' },
  stop: { label: 'Stop', danger: true, text: 'running processes will be terminated.' },
  restart: { label: 'Restart', danger: true, text: 'the container will be restarted.' },
  pause: { label: 'Pause', danger: false, text: 'the container will be paused.' },
  unpause: { label: 'Resume', danger: false, text: 'the container will be resumed.' },
  kill: { label: 'Kill', danger: true, text: 'SIGKILL is sent immediately — no graceful shutdown.' }
}

export function askAction(container, action) {
  // Guard: the detail overlay can call this while `detail` is still loading.
  if (!container) return
  const name = container.name || container.id
  const meta = ACTION_META[action] || { label: action, danger: false, text: '' }
  confirm({
    title: `${meta.label} ${name}?`,
    html: `<b>${name}</b> — ${meta.text}`,
    confirmText: meta.label,
    danger: meta.danger,
    onConfirm: () => doAction(container.id || name, action)
  })
}

export function askRemove(container) {
  // Guard: the detail overlay can call this while `detail` is still loading —
  // without it the click throws and the confirmation dialog never opens.
  if (!container) return
  const name = container.name || container.id
  const target = container.id || name
  confirm({
    title: `Remove ${name}?`,
    html: `The container <b>${name}</b> will be removed. Volumes are kept.`,
    confirmText: 'Remove',
    danger: true,
    onConfirm: () => removeContainer(target)
  })
}

export async function doAction(id, action) {
  const container = state.containers.find(c => c.id === id || c.name === id)
  const name = container?.name || id
  state.modal = null
  try {
    await API.infra.action(id, action)
    pushToast({ text: `${name}: ${action}`, kind: 'success' })
    await loadAll({ silent: true })
    if (state.drawerOpen && state.selectedContainerId === id) {
      await refreshSelected()
      // Only refresh what is actually on screen.
      if (state.detailTab === 'logs') loadLogs()
    }
  } catch (err) {
    pushToast({ text: `${name}: ${err?.message || err}`, kind: 'error' })
  }
}

export async function removeContainer(id) {
  const container = state.containers.find(c => c.id === id || c.name === id)
  const name = container?.name || id
  state.modal = null
  try {
    await API.infra.remove(id)
    pushToast({ text: `${name} removed`, kind: 'success' })
    if (state.selectedContainerId === id) closeDrawer()
    await loadAll({ silent: true })
  } catch (err) {
    pushToast({ text: `${name}: ${err?.message || err}`, kind: 'error' })
  }
}

/* ── Maintenance actions ──────────────────────────────────────────────────── */

/** The single-resource DELETE for each cleanup group. */
const REMOVE_CALL = {
  containers: (item) => API.infra.remove(item.key),
  images: (item) => API.infra.removeImage(item.key),
  volumes: (item) => API.infra.removeVolume(item.name),
  networks: (item) => API.infra.removeNetwork(item.key)
}

export function askPrune(targetId) {
  const meta = PRUNE_META[targetId] || { label: targetId, desc: '', danger: true }
  const days = state.maintenanceOlderThanDays
  const scope = days > 0 ? `older than <b>${days} days</b>` : '<b>of any age</b>'
  confirm({
    title: `Prune ${meta.label.toLowerCase()}?`,
    html: `${meta.desc}<br>Resources ${scope} will be removed. This cannot be undone.`,
    confirmText: 'Prune',
    danger: true,
    onConfirm: () => runPrune(targetId)
  })
}

export async function runPrune(targetId) {
  state.modal = null
  state.maintenanceBusy = targetId
  try {
    const res = await API.infra.prune({
      target: targetId,
      host_id: state.hostId,
      older_than_days: state.maintenanceOlderThanDays || null,
      dangling_only: targetId === 'images'
    })
    const removed = res?.removed ?? 0
    const reclaimed = res?.reclaimed_bytes ? ` · ${fmtBytes(res.reclaimed_bytes)} reclaimed` : ''
    pushToast({
      text: removed ? `${removed} item(s) pruned${reclaimed}` : 'Nothing to prune',
      kind: removed ? 'success' : 'info'
    })
    await loadAll({ silent: true })
  } catch (err) {
    pushToast({ text: `Prune failed: ${err?.message || err}`, kind: 'error' })
  } finally {
    state.maintenanceBusy = null
  }
}

/**
 * Confirms (then removes) one or more cleanup candidates belonging to `group`.
 * @param {{id:string,label:string}} group  Group from `maintenanceReport`.
 * @param {Array<object>} items             Candidates to remove.
 */
export function askRemoveCandidates(group, items) {
  const list = (Array.isArray(items) ? items : [items]).filter(Boolean)
  if (!group || !list.length) return

  const single = list.length === 1
  confirm({
    title: single ? `Remove ${list[0].name}?` : `Remove ${list.length} ${group.label.toLowerCase()}?`,
    html: single
      ? `<b>${list[0].name}</b> — ${list[0].detail || 'this resource'} will be removed permanently.`
      : [
          list.slice(0, 8).map(i => `<code>${i.name}</code>`).join('<br>'),
          list.length > 8 ? `<br>… and ${list.length - 8} more` : ''
        ].join(''),
    confirmText: single ? 'Remove' : `Remove ${list.length}`,
    danger: true,
    onConfirm: () => removeCandidates(group, list)
  })
}

export async function removeCandidates(group, items) {
  const call = REMOVE_CALL[group?.id]
  if (!call || !items?.length) return

  state.modal = null
  state.maintenanceBusy = group.id
  let removed = 0
  let failed = 0
  // Sequential on purpose: one "still in use" must not abort the whole batch.
  for (const item of items) {
    try {
      await call(item)
      removed++
    } catch (err) {
      failed++
    }
  }
  state.maintenanceBusy = null

  pushToast({
    text: failed
      ? `${removed} removed, ${failed} failed (still in use)`
      : `${removed} ${group.label.toLowerCase()} removed`,
    kind: failed ? 'warning' : 'success'
  })
  await loadAll({ silent: true })
}

/* ── Run container modal ──────────────────────────────────────────────────── */
export function openRunModal(prefill = {}) {
  state.modal = {
    type: 'run',
    form: { name: '', image: '', ports: '', env: '', cmd: '', ...prefill },
    errors: {},
    submitting: false
  }
}

export function updateRunField(field, value) {
  const modal = state.modal
  if (!modal || modal.type !== 'run') return
  modal.form[field] = value
  if (modal.errors[field]) delete modal.errors[field]
}

function parsePorts(raw) {
  return String(raw || '')
    .split(/[,\s]+/)
    .filter(Boolean)
    .map((entry) => {
      const [hostPart, containerPart] = entry.split(':')
      const containerPort = Number(containerPart || hostPart)
      if (!containerPort) return null
      return { host: containerPart ? Number(hostPart) : null, container: containerPort, proto: 'tcp' }
    })
    .filter(Boolean)
}

function parseEnv(raw) {
  return String(raw || '')
    .split(',')
    .map(pair => pair.trim())
    .filter(Boolean)
    .map((pair) => {
      const ix = pair.indexOf('=')
      return ix > 0
        ? { k: pair.slice(0, ix).trim(), v: pair.slice(ix + 1).trim() }
        : { k: pair, v: '' }
    })
}

export async function submitRun() {
  const modal = state.modal
  if (!modal || modal.type !== 'run') return

  modal.errors = {}
  if (!modal.form.name?.trim()) modal.errors.name = 'Container name is required'
  if (!modal.form.image?.trim()) modal.errors.image = 'Image is required'
  if (Object.keys(modal.errors).length) return

  modal.submitting = true
  const name = modal.form.name.trim()
  try {
    await API.infra.create({
      name,
      image: modal.form.image.trim(),
      ports: parsePorts(modal.form.ports),
      env: parseEnv(modal.form.env),
      cmd: modal.form.cmd?.trim() || '',
      host_id: state.hostId
    })
    state.modal = null
    pushToast({ text: `${name} started`, kind: 'success' })
    await loadAll({ silent: true })
  } catch (err) {
    pushToast({ text: `${name}: ${err?.message || err}`, kind: 'error' })
  } finally {
    modal.submitting = false
  }
}

/* ── Container detail overlay ─────────────────────────────────────────────── */
export function closeDrawer() {
  openSeq++
  state.drawerOpen = false
  state.selectedContainerId = null
  state.detail = null
  state.detailTab = 'overview'
  state.logs = []
  state.logsLoading = false
  state.stats = null
  state.statsLoading = false
}

/**
 * Opens the container detail overlay (a centered modal).
 *
 * @param {string} id   Container id, short id or name.
 * @param {'overview'|'logs'|'stats'|'config'|'inspect'} [tab='overview'] Tab to show.
 *
 * The requested tab is committed BOTH before and after the detail request:
 * the awaited response must never be able to flip the user back to Overview
 * (that was the reason the "Logs" action kept opening the Overview tab).
 *
 * `inspect` needs no extra request — the overlay always loads the container
 * document, and the Inspect tab renders that document as JSON. That is why
 * the "Inspect" buttons behave exactly like the "Logs" ones.
 */
export async function openContainer(id, tab = 'overview') {
  const token = ++openSeq

  state.selectedContainerId = id
  state.drawerOpen = true
  state.detailTab = tab
  state.detail = state.containers.find(c => c.id === id || c.short === id || c.name === id) || null
  state.logs = []
  state.stats = null

  // Start the tab's data immediately — it must not wait for the detail request.
  if (tab === 'logs') loadLogs()
  if (tab === 'stats') loadStats()

  try {
    const fetched = await API.infra.container(id)
    if (token !== openSeq) return
    if (fetched) state.detail = fetched
  } catch (err) {
    if (token !== openSeq) return
    if (!state.detail) pushToast({ text: `Could not load ${id}`, kind: 'error' })
  }

  // Re-assert the tab requested by the caller (newest open wins).
  if (token === openSeq && state.detailTab !== tab) state.detailTab = tab
}

export function setDetailTab(tab) {
  state.detailTab = tab
  if (tab === 'logs' && !state.logs.length) loadLogs()
  if (tab === 'stats' && !state.stats) loadStats()
}

export async function refreshSelected() {
  const id = state.selectedContainerId
  if (!id) return
  try {
    const detail = await API.infra.container(id)
    if (detail && state.selectedContainerId === id) state.detail = detail
  } catch (err) {
    // keep the last known detail
  }
}

export async function loadLogs(tail = 200) {
  const id = state.selectedContainerId
  if (!id) return
  state.logsLoading = true
  try {
    const res = await API.infra.logs(id, tail)
    if (state.selectedContainerId !== id) return // stale response, another container is open
    state.logs = res?.lines || []
  } catch (err) {
    if (state.selectedContainerId === id) state.logs = []
  } finally {
    if (state.selectedContainerId === id) state.logsLoading = false
  }
}

export async function loadStats() {
  const id = state.selectedContainerId
  if (!id) return
  state.statsLoading = true
  try {
    const stats = await API.infra.stats(id)
    if (state.selectedContainerId !== id) return
    state.stats = stats
  } catch (err) {
    if (state.selectedContainerId === id) state.stats = null
  } finally {
    if (state.selectedContainerId === id) state.statsLoading = false
  }
}

/* ── Composable accessor ──────────────────────────────────────────────────── */
export function useInfra() {
  return {
    state,
    TABS,
    filteredList,
    tabCount,
    // formatting / tone helpers
    fmtBytes,
    fmtTime,
    fmtUptime,
    tone,
    stateTone,
    dotClass,
    healthTone,
    stateLabel,
    // actions
    loadHosts,
    loadAll,
    setRoute,
    setHost,
    setFilter,
    toggleLive,
    askAction,
    askRemove,
    doAction,
    removeContainer,
    openRunModal,
    updateRunField,
    submitRun,
    openContainer,
    closeDrawer,
    setDetailTab,
    refreshSelected,
    loadLogs,
    loadStats,
    // maintenance
    maintenanceReport,
    PRUNE_TARGETS,
    ageDays,
    setMaintenanceAge,
    askPrune,
    runPrune,
    askRemoveCandidates,
    removeCandidates,
    // ui
    pushToast,
    confirm,
    showJson,
    closeModal
  }
}

export default useInfra