/**
 * ============================================================================
 * Infrastructure (Docker) — shared view state, selectors and actions.
 * ----------------------------------------------------------------------------
 * Single reactive store: every infra component (InfraView, the per-tab panels,
 * the container detail overlay, the host and cloud dialogs) reads and mutates
 * the SAME state, so an action taken in one place is instantly reflected
 * everywhere (counts, tables, overlay…). Nothing here talks HTTP directly —
 * everything goes through `API.infra` (see src/api/modules/infra.js), which is
 * mock-backed until the backend implements /api/infra/*.
 *
 * HOST RESOLUTION ORDER
 * ---------------------
 * `GET /api/infra/hosts` is the root of every other request: summary,
 * containers, stacks, images, volumes, networks and events are all scoped by
 * `?host=<id>`. `loadAll()` therefore awaits `loadHosts()` FIRST and only then
 * fans out, which is also why the selector must never end up empty (see
 * LOCAL_HOST below).
 *
 * SSH KEYS AND CLOUD SERVERS
 * --------------------------
 * Both flows live here too, because both end up creating a host:
 *   generate/upload key pair → (cloud) provision server → host registered →
 *   `loadHosts({force:true})` → `setHost(id)`.
 * Keys are global (a key must exist before the machine), credentials are
 * transient (memory only, wiped as soon as the server is accepted).
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
const CLOUD_POLL_MS = 3000

let pollTimer = null
let cloudPollTimer = null
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
  hostsLoading: false,
  hostId: 'host-local',
  summary: null,

  // managed SSH key pairs, shared by hosts and cloud servers
  sshKeys: [],
  sshKeysLoading: false,

  // cloud provider catalog for the "create server" wizard
  cloudProviders: [],
  cloudProvidersLoading: false,

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

/* ── Host definitions ─────────────────────────────────────────────────────── */

/**
 * Fallback used when `GET /api/infra/hosts` fails or returns nothing.
 *
 * The hosts list is the ROOT of every other request: `loadAll()` sends the
 * selected `host` id to summary/containers/stacks/…, so an empty list means a
 * blank selector AND unrouted requests. Falling back to the local socket keeps
 * the view usable — the toast tells the operator it is a fallback.
 */
export const LOCAL_HOST = {
  id: 'host-local',
  name: 'Local host',
  kind: 'local',
  enabled: true,
  is_local: true,
  hostname: '',
  ssh_port: 22,
  ssh_user: '',
  ssh_key_id: '',
  ssh_key_file: '',
  endpoint: 'unix:///var/run/docker.sock',
  tls_verify: false,
  tls_ca_file: '',
  tls_cert_file: '',
  tls_key_file: '',
  provider: null,
  server_id: '',
  region: '',
  engine: '',
  os: '',
  cpu_cores: 0,
  notes: ''
}

/** Stable, readable id derived from the name ("build box" → "host-build-box"). */
function hostIdFrom(name) {
  const slug = String(name || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return 'host-' + (slug || Date.now())
}

/**
 * Normalizes a host coming from the API (or from the form) so the UI always
 * reads the same keys. Accepts the aliases older payloads used
 * (`cert_file`, `key_file`, `ssh_host`, `user`, `docker_host`) and keeps the
 * values of `previous` when the response omits a field.
 */
export function normalizeHost(raw = {}, previous = null) {
  const endpoint = raw.endpoint || raw.docker_host || previous?.endpoint || 'unix:///var/run/docker.sock'
  const kind = raw.kind || (raw.is_local || endpoint.startsWith('unix://') ? 'local' : 'ssh')
  return {
    ...previous,
    id: raw.id || raw.host_id || previous?.id || hostIdFrom(raw.name),
    name: raw.name || raw.hostname || previous?.name || 'Docker host',
    kind,
    enabled: raw.enabled !== false,
    is_local: raw.is_local ?? previous?.is_local ?? kind === 'local',
    hostname: raw.hostname || raw.ssh_host || previous?.hostname || '',
    ssh_port: Number(raw.ssh_port ?? raw.port ?? previous?.ssh_port ?? 22) || 22,
    ssh_user: raw.ssh_user || raw.user || previous?.ssh_user || '',
    ssh_key_id: raw.ssh_key_id || previous?.ssh_key_id || '',
    ssh_key_file: raw.ssh_key_file || raw.cert_file || raw.key_file || previous?.ssh_key_file || '',
    endpoint,
    tls_verify: raw.tls_verify ?? previous?.tls_verify ?? false,
    tls_ca_file: raw.tls_ca_file || previous?.tls_ca_file || '',
    tls_cert_file: raw.tls_cert_file || previous?.tls_cert_file || '',
    tls_key_file: raw.tls_key_file || previous?.tls_key_file || '',
    provider: raw.provider || previous?.provider || null,
    server_id: raw.server_id || previous?.server_id || '',
    region: raw.region || previous?.region || '',
    engine: raw.engine || previous?.engine || '',
    os: raw.os || previous?.os || '',
    cpu_cores: raw.cpu_cores ?? previous?.cpu_cores ?? 0,
    notes: raw.notes || previous?.notes || ''
  }
}

/** The host currently selected in the header selector (never null once loaded). */
export const selectedHost = computed(
  () => state.hosts.find(h => h.id === state.hostId) || state.hosts[0] || null
)

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

/**
 * Closes whatever dialog is open.
 *
 * Also stops the cloud provisioning poll: the job lives server-side, but a
 * timer without a dialog to render it would just burn requests (and leak a
 * handle if the view unmounts).
 */
export function closeModal() {
  stopCloudPolling()
  state.modal = null
}

/* ── Loading ──────────────────────────────────────────────────────────────── */
let hostsInFlight = null

/**
 * Loads the Docker host list — STEP 1 of every refresh.
 *
 * Every other endpoint is scoped by `?host=<id>`, so this must run (and
 * succeed) before `loadAll()` fans out. The list is cached in `state`; pass
 * `{ force: true }` after a host was created / edited / removed.
 *
 * @param {{force?: boolean}} [options]
 * @returns {Promise<string>} the selected (and guaranteed to exist) host id.
 */
export async function loadHosts({ force = false } = {}) {
  if (!force && state.hosts.length) return state.hostId
  if (hostsInFlight) return hostsInFlight

  state.hostsLoading = true
  hostsInFlight = (async () => {
    try {
      const res = await API.infra.hosts()
      // Tolerate both payload shapes: a bare array or `{ hosts: [...] }`.
      const list = Array.isArray(res) ? res : (res?.hosts || [])
      if (list.length) {
        state.hosts = list.map((raw) => {
          const known = state.hosts.find(h => h.id === (raw.id || raw.host_id))
          return normalizeHost(raw, known)
        })
      } else if (!state.hosts.length) {
        state.hosts = [normalizeHost(LOCAL_HOST)]
      }
    } catch (err) {
      if (!state.hosts.length) {
        state.hosts = [normalizeHost(LOCAL_HOST)]
        pushToast({
          text: `Could not list Docker hosts (${err?.message || err}) — showing the local daemon`,
          kind: 'warning'
        })
      }
    } finally {
      state.hostsLoading = false
      hostsInFlight = null
    }

    // The selection MUST point at an existing host, otherwise every request
    // below would be sent with a bogus `host` filter.
    if (!state.hosts.length) state.hosts = [normalizeHost(LOCAL_HOST)]
    if (!state.hosts.find(h => h.id === state.hostId)) {
      state.hostId = state.hosts[0].id
    }
    return state.hostId
  })()

  return hostsInFlight
}

export async function loadAll({ silent = false } = {}) {
  if (!silent) {
    state.error = null
    if (state.status !== 'ready') state.status = 'loading'
  }

  // 1. Host first: summary/containers/… are all scoped by this id.
  const host = await loadHosts()

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

    // Feed the engine gauges back into the host entry so the selector can show
    // what it is actually talking to (the summary describes ONE host).
    const ix = state.hosts.findIndex(h => h.id === host)
    if (ix >= 0) {
      state.hosts[ix] = {
        ...state.hosts[ix],
        engine: summary?.engine || summary?.host?.engine || state.hosts[ix].engine,
        os: summary?.host?.os || state.hosts[ix].os,
        cpu_cores: summary?.cpu_cores ?? state.hosts[ix].cpu_cores
      }
    }
  } catch (err) {
    state.error = err?.message || String(err)
    if (!silent) state.status = 'error'
  }
}

/* ── SSH key pairs ────────────────────────────────────────────────────────── */

/**
 * Algorithms offered by the key generator.
 *
 * ED25519 is the default: shorter keys, faster handshakes, supported by every
 * OpenSSH released after 2014. RSA 4096 is kept for appliances and legacy
 * servers that still refuse Ed25519.
 */
export const SSH_KEY_ALGORITHMS = [
  { id: 'ed25519', label: 'ED25519', bits: 256,
    desc: 'Recommended. Short, fast, accepted by every recent OpenSSH.' },
  { id: 'rsa', label: 'RSA 4096', bits: 4096,
    desc: 'Widest compatibility, including legacy servers and appliances.' }
]

/** Normalizes a key pair coming from the API (aliases tolerated). */
export function normalizeSshKey(raw = {}, previous = null) {
  return {
    ...previous,
    id: raw.id || raw.key_id || previous?.id || '',
    name: raw.name || previous?.name || 'codx-junior',
    algorithm: raw.algorithm || raw.type || previous?.algorithm || 'ed25519',
    bits: raw.bits ?? previous?.bits ?? 0,
    fingerprint: raw.fingerprint || previous?.fingerprint || '',
    source: raw.source || previous?.source || 'generated',
    public_key: raw.public_key || raw.pub || previous?.public_key || '',
    private_key_file: raw.private_key_file || raw.private_path || previous?.private_key_file || '',
    public_key_file: raw.public_key_file || raw.public_path || previous?.public_key_file || '',
    created_at: raw.created_at || raw.created || previous?.created_at || '',
    hosts: raw.hosts || previous?.hosts || []
  }
}

function upsertSshKey(key) {
  if (!key?.id) return null
  const ix = state.sshKeys.findIndex(k => k.id === key.id)
  if (ix >= 0) state.sshKeys.splice(ix, 1, normalizeSshKey(key, state.sshKeys[ix]))
  else state.sshKeys.push(normalizeSshKey(key))
  return sshKeyById(key.id)
}

/** @returns {object|null} the key pair with that id, if it is loaded. */
export function sshKeyById(id) {
  if (!id) return null
  return state.sshKeys.find(k => k.id === id) || null
}

let sshKeysInFlight = null

/**
 * Loads the managed key pairs.
 *
 * Never throws: an unimplemented endpoint leaves the list empty, which only
 * disables the "use an existing key" picker. Generate/upload report their own
 * error inside the dialog.
 */
export async function loadSshKeys({ force = false } = {}) {
  if (!force && state.sshKeys.length) return state.sshKeys
  if (sshKeysInFlight) return sshKeysInFlight

  state.sshKeysLoading = true
  sshKeysInFlight = (async () => {
    try {
      const res = await API.infra.sshKeys()
      const list = Array.isArray(res) ? res : (res?.keys || [])
      if (list.length) {
        state.sshKeys = list.map(raw => normalizeSshKey(raw, sshKeyById(raw.id || raw.key_id)))
      }
    } catch (err) {
      // Silent on purpose: a host can still be saved with a key file path.
    } finally {
      state.sshKeysLoading = false
      sshKeysInFlight = null
    }
    return state.sshKeys
  })()

  return sshKeysInFlight
}

/** The dialog that owns the SSH key currently being managed. */
function keyModal() {
  const modal = state.modal
  return modal && (modal.type === 'host' || modal.type === 'cloud') ? modal : null
}

/** The form (host or cloud wizard) receiving the selected key id. */
function keySlot() {
  return keyModal()?.form || null
}

/** Points the open dialog at `keyId` (`''` clears the selection). */
export function setSshKey(keyId) {
  const slot = keySlot()
  const modal = keyModal()
  if (!slot) return
  slot.ssh_key_id = keyId || ''
  if (modal) {
    modal.keyError = null
    modal.testResult = null
  }
}

/**
 * Generates a key pair on the server and attaches it to the open dialog.
 *
 * Calling it again on a host that already has a pair simply creates a NEW pair
 * and re-points the host at it — the previous pair is left on disk so any other
 * host using it keeps working. That is the "replace the key at any time" flow.
 *
 * @param {{algorithm?: 'ed25519'|'rsa', bits?: number}} [options]
 */
export async function generateSshKey({ algorithm = 'ed25519', bits = 0 } = {}) {
  const slot = keySlot()
  const modal = keyModal()
  if (!slot || !modal) return null

  const algo = SSH_KEY_ALGORITHMS.find(a => a.id === algorithm) || SSH_KEY_ALGORITHMS[0]
  modal.keyBusy = true
  modal.keyError = null
  try {
    const res = await API.infra.generateSshKey({
      name: slot.name?.trim() || 'codx-junior',
      algorithm: algo.id,
      bits: Number(bits) || algo.bits,
      comment: `codx-junior@${window?.location?.hostname || 'host'}`
    })
    const key = upsertSshKey(res?.key || res)
    if (!key?.id) throw new Error('The API did not return the generated key')
    slot.ssh_key_id = key.id
    modal.testResult = null
    pushToast({ text: `${algo.label} key pair ready`, kind: 'success' })
    return key
  } catch (err) {
    modal.keyError = err?.message || String(err)
    return null
  } finally {
    modal.keyBusy = false
  }
}

/**
 * Imports an existing PRIVATE key (multipart). The public half is derived by
 * the backend when no `.pub` file is supplied.
 * @param {{privateFile?: File, publicFile?: File}} files
 */
export async function uploadSshKey({ privateFile = null, publicFile = null } = {}) {
  const slot = keySlot()
  const modal = keyModal()
  if (!slot || !modal) return null
  if (!privateFile) {
    modal.keyError = 'Choose the private key file to import'
    return null
  }

  const body = new FormData()
  body.append('name', slot.name?.trim() || privateFile.name?.replace(/\.(pem|key|ppk)$/i, '') || 'imported')
  body.append('private_key', privateFile)
  if (publicFile) body.append('public_key', publicFile)

  modal.keyBusy = true
  modal.keyError = null
  try {
    const res = await API.infra.uploadSshKey(body)
    const key = upsertSshKey(res?.key || res)
    if (!key?.id) throw new Error('The API did not return the imported key')
    slot.ssh_key_id = key.id
    modal.testResult = null
    pushToast({ text: `Key ${key.name} imported`, kind: 'success' })
    return key
  } catch (err) {
    modal.keyError = err?.message || String(err)
    return null
  } finally {
    modal.keyBusy = false
  }
}

/**
 * Deletes a key pair.
 *
 * Deliberately NOT wrapped in `confirm()`: that helper replaces `state.modal`,
 * which would destroy the host / cloud form the user is editing. The dialog
 * asks for the second click itself (see SshKeyField.vue).
 */
export async function deleteSshKey(id) {
  if (!id) return
  const label = sshKeyById(id)?.name || id
  try {
    await API.infra.deleteSshKey(id)
    state.sshKeys = state.sshKeys.filter(k => k.id !== id)
    const slot = keySlot()
    if (slot && slot.ssh_key_id === id) slot.ssh_key_id = ''
    pushToast({ text: `Key ${label} deleted`, kind: 'success' })
  } catch (err) {
    const modal = keyModal()
    if (modal) modal.keyError = err?.message || String(err)
    pushToast({ text: `${label}: ${err?.message || err}`, kind: 'error' })
  }
}

export async function copyPublicKey(key) {
  const text = key?.public_key || ''
  if (!text) {
    pushToast({ text: 'The public key is not available', kind: 'warning' })
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    pushToast({ text: 'Public key copied', kind: 'success' })
  } catch (err) {
    // Clipboard API needs a secure context — say so instead of failing silently.
    pushToast({ text: 'Clipboard is not available here', kind: 'error' })
  }
}

/**
 * Downloads the `.pub` file.
 *
 * Prefers the text already in `state`; when the list endpoint omitted it (an
 * imported key without a `.pub`, for instance) it fetches
 * `GET /api/infra/ssh-keys/:id/public-key` instead of refusing.
 */
export async function downloadPublicKey(key) {
  if (!key) return
  let text = key.public_key || ''
  if (!text && key.id) {
    try {
      const res = await API.infra.sshKeyPublicKey(key.id)
      text = typeof res === 'string' ? res : (res?.public_key || '')
      if (text) upsertSshKey({ ...key, public_key: text })
    } catch (err) {
      pushToast({ text: `Could not read the public key: ${err?.message || err}`, kind: 'error' })
      return
    }
  }
  if (!text) {
    pushToast({ text: 'The public key is not available', kind: 'warning' })
    return
  }

  const name = `${(key.name || 'id').replace(/[^\w.-]+/g, '_')}.pub`
  const blob = new Blob([text.endsWith('\n') ? text : text + '\n'], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

/* ── Cloud providers ──────────────────────────────────────────────────────── */

/**
 * Offline provider catalog.
 *
 * The wizard renders itself from a `CloudProvider` descriptor, so this array
 * keeps the dialog fully usable (and reviewable) before
 * `GET /api/infra/cloud/providers` exists. The backend response wins whenever
 * it is available — see `normalizeProvider()`.
 */
export const CLOUD_PROVIDERS_FALLBACK = [
  {
    id: 'hetzner',
    name: 'Hetzner Cloud',
    icon: 'fa-cloud',
    summary: 'Cheap x86 instances in the EU and US. The fastest way to get a dev server.',
    credentials: [
      { key: 'api_token', label: 'API token', type: 'password', required: true, secret: true,
        placeholder: '••••••••••••••••••••••••••••',
        help: 'Project → Security → API tokens (Read & Write).' }
    ],
    regions: [
      { value: 'fsn1', label: 'Falkenstein, DE' },
      { value: 'nbg1', label: 'Nuremberg, DE' },
      { value: 'hel1', label: 'Helsinki, FI' },
      { value: 'ash', label: 'Ashburn, US' },
      { value: 'hil', label: 'Hillsboro, US' }
    ],
    sizes: [
      { value: 'cx22', label: 'CX22 · 2 vCPU · 4 GB' },
      { value: 'cx32', label: 'CX32 · 4 vCPU · 8 GB' },
      { value: 'cpx11', label: 'CPX11 · 2 vCPU · 2 GB (AMD)' },
      { value: 'cpx21', label: 'CPX21 · 3 vCPU · 4 GB (AMD)' }
    ],
    images: [
      { value: 'ubuntu-24.04', label: 'Ubuntu 24.04 LTS' },
      { value: 'ubuntu-22.04', label: 'Ubuntu 22.04 LTS' },
      { value: 'debian-12', label: 'Debian 12' }
    ],
    default_region: 'fsn1',
    default_size: 'cx22',
    default_image: 'ubuntu-24.04',
    ssh_user: 'root',
    uploads_key: true
  },
  {
    id: 'aws',
    name: 'Amazon Web Services',
    icon: 'fa-server',
    summary: 'EC2 instances. Use a scoped IAM user — EC2 + VPC + key pair permissions.',
    credentials: [
      { key: 'access_key_id', label: 'Access key id', type: 'text', required: true,
        placeholder: 'AKIA…', help: 'IAM → Users → Security credentials.' },
      { key: 'secret_access_key', label: 'Secret access key', type: 'password', required: true, secret: true,
        placeholder: '••••••••••••••••••••••••••••' },
      { key: 'session_token', label: 'Session token (temporary credentials)', type: 'password', secret: true,
        help: 'Only for STS / SSO credentials. Leave empty for IAM user keys.' }
    ],
    regions: [
      { value: 'eu-west-1', label: 'Europe (Ireland)' },
      { value: 'eu-central-1', label: 'Europe (Frankfurt)' },
      { value: 'us-east-1', label: 'US East (N. Virginia)' },
      { value: 'us-west-2', label: 'US West (Oregon)' }
    ],
    sizes: [
      { value: 't3.small', label: 't3.small · 2 vCPU · 2 GB' },
      { value: 't3.medium', label: 't3.medium · 2 vCPU · 4 GB' },
      { value: 't3.large', label: 't3.large · 2 vCPU · 8 GB' },
      { value: 'm6i.large', label: 'm6i.large · 2 vCPU · 8 GB' }
    ],
    images: [
      { value: 'ubuntu-24.04', label: 'Ubuntu 24.04 LTS (resolved per region)' },
      { value: 'ubuntu-22.04', label: 'Ubuntu 22.04 LTS (resolved per region)' },
      { value: 'debian-12', label: 'Debian 12 (resolved per region)' },
      { value: 'amazon-linux-2023', label: 'Amazon Linux 2023' }
    ],
    default_region: 'eu-west-1',
    default_size: 't3.medium',
    default_image: 'ubuntu-24.04',
    ssh_user: 'ubuntu',
    uploads_key: true
  },
  {
    id: 'azure',
    name: 'Microsoft Azure',
    icon: 'fa-cubes',
    summary: 'Azure VMs via a service principal. Contributor + Network Contributor on the resource group.',
    credentials: [
      { key: 'tenant_id', label: 'Tenant id', type: 'text', required: true,
        placeholder: '00000000-0000-0000-0000-000000000000' },
      { key: 'client_id', label: 'Client (application) id', type: 'text', required: true,
        placeholder: '00000000-0000-0000-0000-000000000000' },
      { key: 'client_secret', label: 'Client secret', type: 'password', required: true, secret: true,
        placeholder: '••••••••••••••••••••••••••••' },
      { key: 'subscription_id', label: 'Subscription id', type: 'text', required: true,
        placeholder: '00000000-0000-0000-0000-000000000000' }
    ],
    regions: [
      { value: 'westeurope', label: 'West Europe' },
      { value: 'northeurope', label: 'North Europe' },
      { value: 'eastus', label: 'East US' },
      { value: 'westus2', label: 'West US 2' }
    ],
    sizes: [
      { value: 'Standard_B2s', label: 'B2s · 2 vCPU · 4 GB' },
      { value: 'Standard_B2ms', label: 'B2ms · 2 vCPU · 8 GB' },
      { value: 'Standard_D2s_v3', label: 'D2s v3 · 2 vCPU · 8 GB' }
    ],
    images: [
      { value: 'Canonical:ubuntu-24_04-lts:server:latest', label: 'Ubuntu 24.04 LTS' },
      { value: 'Canonical:ubuntu-22_04-lts:server:latest', label: 'Ubuntu 22.04 LTS' },
      { value: 'Debian:debian-12:12-gen2:latest', label: 'Debian 12' }
    ],
    default_region: 'westeurope',
    default_size: 'Standard_B2s',
    default_image: 'Canonical:ubuntu-24_04-lts:server:latest',
    ssh_user: 'azureuser',
    uploads_key: true
  }
]

/** Options may arrive as strings or `{value,label}` objects. */
function normalizeOptions(list) {
  return (Array.isArray(list) ? list : [])
    .map((entry) => {
      if (entry == null) return null
      if (typeof entry === 'string') return { value: entry, label: entry }
      const value = entry.value ?? entry.id ?? entry.name ?? entry.slug
      if (!value) return null
      return { value, label: entry.label ?? entry.name ?? String(value), note: entry.note }
    })
    .filter(Boolean)
}

/** Merges the backend descriptor over the offline fallback. */
function normalizeProvider(raw = {}) {
  const id = raw.id || raw.provider || raw.name
  const fallback = CLOUD_PROVIDERS_FALLBACK.find(p => p.id === id) || {}
  const regions = normalizeOptions(raw.regions?.length ? raw.regions : fallback.regions)
  const sizes = normalizeOptions(raw.sizes?.length ? raw.sizes : fallback.sizes)
  const images = normalizeOptions(raw.images?.length ? raw.images : fallback.images)
  return {
    ...fallback,
    ...raw,
    id,
    name: raw.name || fallback.name || id,
    icon: raw.icon || fallback.icon || 'fa-cloud',
    credentials: raw.credentials?.length ? raw.credentials : (fallback.credentials || []),
    regions,
    sizes,
    images,
    default_region: raw.default_region || fallback.default_region || regions[0]?.value || '',
    default_size: raw.default_size || fallback.default_size || sizes[0]?.value || '',
    default_image: raw.default_image || fallback.default_image || images[0]?.value || '',
    ssh_user: raw.ssh_user || fallback.ssh_user || 'root'
  }
}

/** @returns {object} the provider descriptor (never null). */
export function cloudProviderById(id) {
  return state.cloudProviders.find(p => p.id === id)
    || CLOUD_PROVIDERS_FALLBACK.find(p => p.id === id)
    || state.cloudProviders[0]
    || CLOUD_PROVIDERS_FALLBACK[0]
}

let providersInFlight = null

/**
 * Loads the provider catalog, falling back to the offline one.
 * @returns {Promise<object[]>}
 */
export async function loadCloudProviders({ force = false } = {}) {
  if (!force && state.cloudProviders.length) return state.cloudProviders
  if (providersInFlight) return providersInFlight

  state.cloudProvidersLoading = true
  providersInFlight = (async () => {
    try {
      const res = await API.infra.cloudProviders()
      const list = Array.isArray(res) ? res : (res?.providers || [])
      state.cloudProviders = list.length ? list.map(normalizeProvider) : CLOUD_PROVIDERS_FALLBACK
    } catch (err) {
      // The offline catalog is enough to render the wizard; provisioning will
      // surface the real error once the backend exists.
      state.cloudProviders = CLOUD_PROVIDERS_FALLBACK
    } finally {
      state.cloudProvidersLoading = false
      providersInFlight = null
    }
    return state.cloudProviders
  })()

  return providersInFlight
}

/** Steps of the wizard, used by the `steps` strip. */
export const CLOUD_FLOW = [
  { id: 'provider', label: 'Provider' },
  { id: 'credentials', label: 'Credentials' },
  { id: 'server', label: 'Server' },
  { id: 'progress', label: 'Provisioning' }
]

/** Milestones reported by the provisioning job. */
export const CLOUD_JOB_STEPS = [
  { id: 'creating', label: 'Create the server' },
  { id: 'booting', label: 'Boot & SSH access' },
  { id: 'installing_docker', label: 'Install Docker' },
  { id: 'registering', label: 'Register the host' },
  { id: 'ready', label: 'Ready' }
]

/** Index of `status` inside CLOUD_JOB_STEPS (-2 for a failed job). */
export function cloudJobIndex(status) {
  if (status === 'error') return -2
  const ix = CLOUD_JOB_STEPS.findIndex(s => s.id === status)
  return ix < 0 ? 0 : ix
}

export const EMPTY_CLOUD_JOB = {
  id: '',
  provider: '',
  status: 'queued',
  progress: 0,
  message: '',
  ip: '',
  hostname: '',
  host_id: '',
  host: null,
  logs: []
}

function cloudJobFrom(res, previous = null) {
  const raw = res?.job || res || {}
  return {
    ...previous,
    id: raw.id || raw.server_id || raw.job_id || previous?.id || '',
    provider: raw.provider || previous?.provider || '',
    status: raw.status || previous?.status || 'queued',
    progress: Number(raw.progress ?? previous?.progress ?? 0),
    message: raw.message || previous?.message || '',
    ip: raw.ip || raw.ipv4 || raw.ip_address || previous?.ip || '',
    hostname: raw.hostname || raw.name || previous?.hostname || '',
    host_id: raw.host_id || raw.host?.id || previous?.host_id || '',
    host: raw.host || previous?.host || null,
    logs: Array.isArray(raw.logs) ? raw.logs : (previous?.logs || [])
  }
}

/** Opens the "create a Docker server" wizard. */
export function openCloudModal(providerId = null) {
  const provider = providerId || state.cloudProviders[0]?.id || CLOUD_PROVIDERS_FALLBACK[0].id
  state.modal = {
    type: 'cloud',
    step: providerId ? 'credentials' : 'provider',
    providerId: provider,
    form: {
      provider,
      region: '',
      name: '',
      size: '',
      image: '',
      ssh_user: '',
      ssh_key_id: '',
      install_docker: true,
      open_ports: '22, 2376'
    },
    // TRANSIENT: lives in memory for this dialog only — never persisted.
    credentials: {},
    errors: {},
    testing: false,
    testResult: null,
    submitting: false,
    credentialsCleared: false,
    job: null,
    keyBusy: false,
    keyError: null
  }
  applyProviderDefaults(provider)
  // The catalog may be richer than the fallback: re-apply once it lands, but
  // never overwrite what the operator already typed.
  loadCloudProviders().then(() => applyProviderDefaults(state.modal?.providerId || provider, { onlyEmpty: true }))
  loadSshKeys()
}

function defaultServerName(providerId) {
  return `docker-${providerId}-${Math.random().toString(36).slice(2, 6)}`
}

/** Fills the provider specific selects. */
function applyProviderDefaults(providerId, { onlyEmpty = false } = {}) {
  const modal = state.modal
  if (!modal || modal.type !== 'cloud') return null
  const provider = cloudProviderById(providerId)
  if (!provider) return null

  const form = modal.form
  const pick = (current, next) => (onlyEmpty && current ? current : next)
  form.region = pick(form.region, provider.default_region || provider.regions?.[0]?.value || '')
  form.size = pick(form.size, provider.default_size || provider.sizes?.[0]?.value || '')
  form.image = pick(form.image, provider.default_image || provider.images?.[0]?.value || '')
  form.ssh_user = pick(form.ssh_user, provider.ssh_user || 'root')
  return provider
}

/** Switches provider and resets the provider specific fields. */
export function setCloudProvider(providerId) {
  const modal = state.modal
  if (!modal || modal.type !== 'cloud') return
  modal.providerId = providerId
  modal.form.provider = providerId
  modal.form.region = ''
  modal.form.size = ''
  modal.form.image = ''
  modal.form.ssh_user = ''
  modal.errors = {}
  modal.testResult = null
  applyProviderDefaults(providerId)
}

export function setCloudStep(step) {
  const modal = state.modal
  if (!modal || modal.type !== 'cloud') return
  modal.step = CLOUD_FLOW.some(s => s.id === step) ? step : 'provider'
}

export function updateCloudField(field, value) {
  const modal = state.modal
  if (!modal || modal.type !== 'cloud') return
  modal.form[field] = value
  if (modal.errors[field]) delete modal.errors[field]
  if (modal.errors.submit) delete modal.errors.submit
  if (field === 'size' || field === 'image' || field === 'region') modal.testResult = null
}

/** Credential inputs are never copied out of `modal.credentials`. */
export function updateCloudCredential(field, value) {
  const modal = state.modal
  if (!modal || modal.type !== 'cloud') return
  modal.credentials[field] = value
  if (modal.errors[field]) delete modal.errors[field]
  if (modal.errors.submit) delete modal.errors.submit
  modal.testResult = null
}

/** Client side checks; the backend re-validates everything anyway. */
function validateCloud(modal, stage) {
  const provider = cloudProviderById(modal.providerId)
  const errors = {}

  if (stage === 'credentials') {
    (provider.credentials || []).forEach((field) => {
      if (!field.required) return
      if (!String(modal.credentials[field.key] ?? '').trim()) {
        errors[field.key] = `${field.label} is required`
      }
    })
  }

  if (stage === 'server') {
    const name = String(modal.form.name || '').trim()
    if (!name) errors.name = 'A server name is required'
    else if (!/^[a-z](?:[a-z0-9-]{0,61}[a-z0-9])$/.test(name)) {
      errors.name = 'Lowercase letters, digits and dashes only (2-63 characters)'
    }
    if (!modal.form.region) errors.region = 'Select a region'
    if (!modal.form.size) errors.size = 'Select a server size'
    if (!modal.form.image) errors.image = 'Select an image'
    if (!modal.form.ssh_key_id) errors.ssh_key_id = 'Generate, import or pick an SSH key pair'
  }

  return errors
}

export function cloudNext() {
  const modal = state.modal
  if (!modal || modal.type !== 'cloud') return

  if (modal.step === 'provider') {
    modal.step = 'credentials'
    return
  }

  if (modal.step === 'credentials') {
    modal.errors = validateCloud(modal, 'credentials')
    if (Object.keys(modal.errors).length) return
    if (!modal.form.name) modal.form.name = defaultServerName(modal.providerId)
    modal.step = 'server'
  }
}

export function cloudBack() {
  const modal = state.modal
  if (!modal || modal.type !== 'cloud') return
  const ix = CLOUD_FLOW.findIndex(s => s.id === modal.step)
  if (ix > 0) modal.step = CLOUD_FLOW[ix - 1].id
}

/**
 * Checks the credentials against the provider without creating anything.
 * The result is rendered inside the dialog, so nothing is toasted here.
 */
export async function testCloudCredentials() {
  const modal = state.modal
  if (!modal || modal.type !== 'cloud') return

  modal.errors = validateCloud(modal, 'credentials')
  modal.testResult = null
  if (Object.keys(modal.errors).length) return

  modal.testing = true
  try {
    const res = await API.infra.validateCloud({
      provider: modal.providerId,
      credentials: { ...modal.credentials },
      region: modal.form.region
    })
    const ok = res?.ok !== false && !res?.error
    modal.testResult = {
      ok,
      text: res?.message || res?.error || (ok ? 'Credentials accepted' : 'The provider rejected these credentials'),
      account: res?.account || res?.project || ''
    }
  } catch (err) {
    modal.testResult = { ok: false, text: err?.message || String(err) }
  } finally {
    modal.testing = false
  }
}

function parsePortList(raw) {
  return String(raw || '')
    .split(/[,\s]+/)
    .map(value => Number(value))
    .filter(value => Number.isInteger(value) && value > 0 && value <= 65535)
}

/** Sends the creation request and switches to the progress step. */
export async function createCloudServer() {
  const modal = state.modal
  if (!modal || modal.type !== 'cloud') return

  modal.errors = validateCloud(modal, 'server')
  if (Object.keys(modal.errors).length) return

  modal.submitting = true
  modal.keyError = null
  const name = modal.form.name.trim()

  try {
    const res = await API.infra.createCloudServer({
      provider: modal.providerId,
      credentials: { ...modal.credentials },
      region: modal.form.region,
      name,
      size: modal.form.size,
      image: modal.form.image,
      ssh_key_id: modal.form.ssh_key_id,
      ssh_user: modal.form.ssh_user,
      install_docker: modal.form.install_docker !== false,
      open_ports: parsePortList(modal.form.open_ports),
      tags: { 'managed-by': 'codx-junior' }
    })

    // Credentials were accepted: drop them from memory immediately. They are
    // never written to localStorage, to the URL or back to the API.
    modal.credentials = {}
    modal.credentialsCleared = true
    modal.testResult = null
    modal.job = cloudJobFrom(res)
    modal.step = 'progress'
    pushToast({ text: `Creating ${name}…`, kind: 'info' })

    if (modal.job.id) startCloudPolling()
    else await loadAll({ silent: true })
  } catch (err) {
    modal.errors = { ...modal.errors, submit: err?.message || String(err) }
    pushToast({ text: `${name}: ${err?.message || err}`, kind: 'error' })
  } finally {
    modal.submitting = false
  }
}

/* ── Cloud provisioning poll ──────────────────────────────────────────────── */

export function stopCloudPolling() {
  if (cloudPollTimer) {
    clearInterval(cloudPollTimer)
    cloudPollTimer = null
  }
}

function startCloudPolling() {
  stopCloudPolling()
  cloudPollTimer = setInterval(pollCloudJob, CLOUD_POLL_MS)
  pollCloudJob()
}

async function pollCloudJob() {
  const modal = state.modal
  if (!modal || modal.type !== 'cloud' || !modal.job?.id) {
    stopCloudPolling()
    return
  }

  try {
    const res = await API.infra.cloudServer(modal.job.id)
    const job = cloudJobFrom(res, modal.job)
    modal.job = job

    if (job.status === 'ready') {
      stopCloudPolling()
      await finishCloudServer(job)
    } else if (job.status === 'error') {
      stopCloudPolling()
      pushToast({ text: job.message || 'Provisioning failed', kind: 'error' })
    }
  } catch (err) {
    // Transient failure: the job lives server-side, keep polling.
  }
}

/** Called once the job reports `ready`: refresh the hosts and select the new one. */
async function finishCloudServer(job) {
  await loadHosts({ force: true })
  const hostId = job.host_id || job.host?.id || ''
  pushToast({ text: `${job.hostname || job.id} is ready`, kind: 'success' })
  if (!hostId) return
  if (hostId !== state.hostId) await setHost(hostId)
  else await loadAll({ silent: true })
}

export function askDestroyCloudServer(job) {
  if (!job?.id) return
  const label = job.hostname || job.id
  confirm({
    title: `Delete ${label}?`,
    html: `The server <b>${label}</b> is destroyed at the provider and its host entry is removed ` +
          'from codx-junior. Containers and volumes on it are lost.',
    confirmText: 'Delete server',
    danger: true,
    onConfirm: () => destroyCloudServer(job.id)
  })
}

export async function destroyCloudServer(id) {
  stopCloudPolling()
  state.modal = null
  try {
    await API.infra.destroyCloudServer(id)
    pushToast({ text: 'Server deleted', kind: 'success' })
    await loadHosts({ force: true })
    await loadAll({ silent: true })
  } catch (err) {
    pushToast({ text: `Delete failed: ${err?.message || err}`, kind: 'error' })
  }
}

/* ── Host definitions (create / edit / test / remove) ─────────────────────── */
const EMPTY_HOST_FORM = {
  id: '',
  name: '',
  kind: 'ssh',
  is_local: false,
  enabled: true,
  hostname: '',
  ssh_port: 22,
  ssh_user: 'root',
  ssh_key_id: '',
  ssh_key_file: '',
  endpoint: 'unix:///var/run/docker.sock',
  tls_verify: false,
  tls_ca_file: '',
  tls_cert_file: '',
  tls_key_file: '',
  notes: ''
}

/** Editable subset of a host (engine gauges are read-only). */
function hostFormFrom(host = {}) {
  return {
    id: host.id || '',
    name: host.name || '',
    kind: host.kind || (host.is_local ? 'local' : 'ssh'),
    is_local: !!host.is_local,
    enabled: host.enabled !== false,
    hostname: host.hostname || '',
    ssh_port: host.ssh_port || 22,
    ssh_user: host.ssh_user || 'root',
    ssh_key_id: host.ssh_key_id || '',
    ssh_key_file: host.ssh_key_file || '',
    endpoint: host.endpoint || 'unix:///var/run/docker.sock',
    tls_verify: !!host.tls_verify,
    tls_ca_file: host.tls_ca_file || '',
    tls_cert_file: host.tls_cert_file || '',
    tls_key_file: host.tls_key_file || '',
    notes: host.notes || ''
  }
}

/**
 * Opens the host dialog.
 * @param {object|null} host  Host to edit, or null to create a new one.
 */
export function openHostModal(host = null) {
  const source = host || null
  state.modal = {
    type: 'host',
    mode: source ? 'edit' : 'create',
    form: { ...EMPTY_HOST_FORM, ...(source ? hostFormFrom(source) : {}) },
    errors: {},
    submitting: false,
    testing: false,
    testResult: null,
    keyBusy: false,
    keyError: null
  }
  // Key pairs are shared with the cloud wizard: load them so the picker works
  // (and so an existing pair can be reused instead of generating another one).
  loadSshKeys()
}

/** Edits the currently selected host. */
export function openHostSettings() {
  openHostModal(selectedHost.value)
}

/** Endpoint implied by the SSH settings (Docker's own `ssh://` transport). */
function endpointFor(form) {
  if (form.kind === 'local') return 'unix:///var/run/docker.sock'
  const user = form.ssh_user ? `${form.ssh_user}@` : ''
  const port = Number(form.ssh_port)
  const portPart = port && port !== 22 ? `:${port}` : ''
  return `ssh://${user}${form.hostname || 'host'}${portPart}`
}

/** Keeps a derived `ssh://` endpoint in sync with the SSH fields. */
function syncEndpoint(form) {
  if (form.kind !== 'ssh') return
  if (!form.endpoint || form.endpoint.startsWith('ssh://')) {
    form.endpoint = endpointFor(form)
  }
}

const SSH_FIELDS = ['hostname', 'ssh_user', 'ssh_port']

export function updateHostField(field, value) {
  const modal = state.modal
  if (!modal || modal.type !== 'host') return
  modal.form[field] = value
  if (SSH_FIELDS.includes(field)) syncEndpoint(modal.form)
  if (modal.errors[field]) delete modal.errors[field]
  if (modal.errors.ssh_key_id) delete modal.errors.ssh_key_id
  modal.testResult = null
}

export function setHostKind(kind) {
  const modal = state.modal
  if (!modal || modal.type !== 'host') return
  modal.form.kind = kind === 'local' ? 'local' : 'ssh'
  modal.form.endpoint = endpointFor(modal.form)
  delete modal.errors.hostname
  delete modal.errors.ssh_port
  modal.testResult = null
}

/** Client-side validation; the backend still re-checks everything. */
function validateHost(form) {
  const errors = {}
  if (!form.name?.trim()) errors.name = 'A host name is required'

  if (form.kind === 'ssh') {
    if (!form.hostname?.trim()) errors.hostname = 'The SSH host (name or IP) is required'
    const port = Number(form.ssh_port)
    if (!port || port < 1 || port > 65535) errors.ssh_port = 'Port must be between 1 and 65535'
    // Either a managed key pair or an explicit key file must be reachable.
    if (!form.ssh_key_id && !form.ssh_key_file?.trim()) {
      errors.ssh_key_id = 'Generate, import or select an SSH key pair (or set a key file path)'
    }
  }

  if (!form.endpoint?.trim()) errors.endpoint = 'A Docker endpoint is required'

  return errors
}

/** Form → API payload (drops SSH fields for the local socket). */
function hostPayload(form) {
  const kind = form.kind === 'local' ? 'local' : 'ssh'
  const ssh = kind === 'ssh'
  return {
    id: form.id || undefined,
    name: form.name.trim(),
    kind,
    enabled: form.enabled !== false,
    is_local: kind === 'local',
    hostname: ssh ? form.hostname?.trim() || '' : '',
    ssh_port: ssh ? Number(form.ssh_port) || 22 : null,
    ssh_user: ssh ? form.ssh_user?.trim() || '' : '',
    ssh_key_id: ssh ? form.ssh_key_id || '' : '',
    ssh_key_file: ssh ? form.ssh_key_file?.trim() || '' : '',
    endpoint: form.endpoint?.trim() || 'unix:///var/run/docker.sock',
    tls_verify: !!form.tls_verify,
    tls_ca_file: form.tls_ca_file?.trim() || '',
    tls_cert_file: form.tls_cert_file?.trim() || '',
    tls_key_file: form.tls_key_file?.trim() || '',
    notes: form.notes?.trim() || ''
  }
}

/**
 * Probes the unsaved definition (SSH handshake + daemon ping). The result is
 * rendered inside the dialog, so nothing is toasted here.
 */
export async function testHostConnection() {
  const modal = state.modal
  if (!modal || modal.type !== 'host') return

  modal.errors = validateHost(modal.form)
  modal.testResult = null
  if (Object.keys(modal.errors).length) return

  modal.testing = true
  try {
    const res = await API.infra.testHost(hostPayload(modal.form))
    const ok = res?.ok !== false && !res?.error
    modal.testResult = {
      ok,
      text: res?.message || res?.error || (ok ? 'Connection successful' : 'The Docker daemon is unreachable'),
      engine: res?.engine,
      os: res?.os
    }
  } catch (err) {
    modal.testResult = { ok: false, text: err?.message || String(err) }
  } finally {
    modal.testing = false
  }
}

export async function submitHost() {
  const modal = state.modal
  if (!modal || modal.type !== 'host') return

  modal.errors = validateHost(modal.form)
  if (Object.keys(modal.errors).length) return

  const payload = hostPayload(modal.form)
  const editing = modal.mode === 'edit' && !!payload.id
  modal.submitting = true
  try {
    const saved = editing
      ? await API.infra.updateHost(payload.id, payload)
      : await API.infra.createHost(payload)

    state.modal = null
    pushToast({ text: `${payload.name} ${editing ? 'updated' : 'added'}`, kind: 'success' })

    await loadHosts({ force: true })
    const targetId = saved?.id || saved?.host_id || payload.id
    if (targetId && targetId !== state.hostId) {
      setHost(targetId) // reloads everything for the new host
    } else {
      await loadAll({ silent: true })
    }
  } catch (err) {
    pushToast({ text: `${payload.name}: ${err?.message || err}`, kind: 'error' })
  } finally {
    modal.submitting = false
  }
}

export function askRemoveHost(host) {
  if (!host) return
  if (host.is_local) {
    pushToast({ text: 'The local host cannot be removed', kind: 'warning' })
    return
  }
  confirm({
    title: `Remove host ${host.name}?`,
    html: `The connection settings for <b>${host.name}</b> will be deleted. ` +
          'Containers keep running on that machine — codx-junior simply stops managing it.',
    confirmText: 'Remove host',
    danger: true,
    onConfirm: () => removeHost(host.id)
  })
}

export async function removeHost(id) {
  state.modal = null
  const host = state.hosts.find(h => h.id === id)
  const label = host?.name || id
  try {
    await API.infra.deleteHost(id)
    pushToast({ text: `${label} removed`, kind: 'success' })
    if (state.hostId === id) state.hostId = ''
    await loadHosts({ force: true })
    await loadAll({ silent: true })
  } catch (err) {
    pushToast({ text: `${label}: ${err?.message || err}`, kind: 'error' })
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
  state.status = 'loading'
  closeDrawer()
  return loadAll()
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
    // hosts
    loadHosts,
    selectedHost,
    normalizeHost,
    openHostModal,
    openHostSettings,
    updateHostField,
    setHostKind,
    submitHost,
    testHostConnection,
    askRemoveHost,
    removeHost,
    // ssh keys
    SSH_KEY_ALGORITHMS,
    normalizeSshKey,
    loadSshKeys,
    sshKeyById,
    generateSshKey,
    uploadSshKey,
    setSshKey,
    deleteSshKey,
    copyPublicKey,
    downloadPublicKey,
    // cloud providers
    CLOUD_PROVIDERS_FALLBACK,
    CLOUD_FLOW,
    CLOUD_JOB_STEPS,
    EMPTY_CLOUD_JOB,
    cloudProviderById,
    cloudJobIndex,
    loadCloudProviders,
    openCloudModal,
    setCloudProvider,
    setCloudStep,
    cloudNext,
    cloudBack,
    updateCloudField,
    updateCloudCredential,
    testCloudCredentials,
    createCloudServer,
    stopCloudPolling,
    askDestroyCloudServer,
    destroyCloudServer,
    // actions
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