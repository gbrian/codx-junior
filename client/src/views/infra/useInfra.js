/**
 * ============================================================================
 * Infrastructure (Docker) — shared view state, selectors and actions.
 * ----------------------------------------------------------------------------
 * Single reactive store: every infra component (InfraView, the per-tab panels
 * and the container drawer) reads and mutates the SAME state, so an action
 * taken in one place is instantly reflected everywhere (counts, tables,
 * drawer…). Nothing here talks HTTP directly — everything goes through
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
  { id: 'events', label: 'Events', icon: 'fa-bolt' }
]

const POLL_MS = 5000

let pollTimer = null
let toastSeq = 0

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

  // container detail drawer
  drawerOpen: false,
  selectedContainerId: null,
  detail: null,
  detailTab: 'overview',
  logs: [],
  logsLoading: false,
  stats: null,
  statsLoading: false,

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

export function tabCount(tabId) {
  switch (tabId) {
    case 'containers': return state.containers.length
    case 'stacks': return state.stacks.length
    case 'images': return state.images.length
    case 'volumes': return state.volumes.length
    case 'networks': return state.networks.length
    case 'events': return state.events.length
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
  const meta = ACTION_META[action] || { label: action, danger: false, text: '' }
  confirm({
    title: `${meta.label} ${container.name}?`,
    html: `<b>${container.name}</b> — ${meta.text}`,
    confirmText: meta.label,
    danger: meta.danger,
    onConfirm: () => doAction(container.id, action)
  })
}

export function askRemove(container) {
  confirm({
    title: `Remove ${container.name}?`,
    html: `The container <b>${container.name}</b> will be removed. Volumes are kept.`,
    confirmText: 'Remove',
    danger: true,
    onConfirm: () => removeContainer(container.id)
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
      loadLogs()
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

/* ── Container drawer ─────────────────────────────────────────────────────── */
export function closeDrawer() {
  state.drawerOpen = false
  state.selectedContainerId = null
  state.detail = null
  state.logs = []
  state.stats = null
}

export async function openContainer(id) {
  state.selectedContainerId = id
  state.drawerOpen = true
  state.detailTab = 'overview'
  state.detail = state.containers.find(c => c.id === id || c.short === id || c.name === id) || null
  state.logs = []
  state.stats = null

  try {
    state.detail = (await API.infra.container(id)) || state.detail
  } catch (err) {
    pushToast({ text: `Could not load ${id}`, kind: 'error' })
  }

  loadLogs()
  loadStats()
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
    if (detail) state.detail = detail
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
    state.logs = res?.lines || []
  } catch (err) {
    state.logs = []
  } finally {
    state.logsLoading = false
  }
}

export async function loadStats() {
  const id = state.selectedContainerId
  if (!id) return
  state.statsLoading = true
  try {
    state.stats = await API.infra.stats(id)
  } catch (err) {
    state.stats = null
  } finally {
    state.statsLoading = false
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
    pushToast,
    confirm,
    showJson,
    closeModal
  }
}

export default useInfra
