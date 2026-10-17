/**
 * ============================================================================
 * codx-junior — Infrastructure (Docker) API module
 * File: src/api/modules/infra.js
 * ----------------------------------------------------------------------------
 * BACKEND CONTRACT
 * ----------------
 * Thin HTTP client for the infrastructure REST API under `/api/infra/*`,
 * implemented by `api/codx/junior/api/infra.py`.
 *
 * Every request goes through the regular `API.get/post/delete` helpers, so
 * authentication (cookie/bearer), base URL and interceptors all apply.
 *
 * All routes are gated server-side to users with the `admin` role: container
 * start/stop/kill, container creation and any prune/removal are privileged
 * operations. A non-admin caller receives `403`.
 *
 * Error statuses worth handling in the UI:
 *   - `403` predefined Docker network cannot be removed.
 *   - `404` the resource (or the host id) does not exist.
 *   - `409` the resource is still in use (image referenced by a container,
 *           volume still mounted, network with attached endpoints).
 *   - `503` the Docker daemon / socket is unreachable.
 *
 * The machine-readable contract is exported as `INFRA_ENDPOINTS` and mirrored
 * by the JSDoc typedefs further down.
 * ============================================================================
 */

/* ──────────────────────────────────────────────────────────────────────────
 * 1. CONTRACT — hand this to the backend team
 * ────────────────────────────────────────────────────────────────────────── */

/**
 * @typedef {Object} InfraHost
 * @property {string}  id          Stable host key, e.g. "host-local".
 * @property {string}  name        Human readable host name.
 * @property {string}  endpoint    Docker endpoint, e.g. "unix:///var/run/docker.sock".
 * @property {string}  engine      Docker engine version.
 * @property {string}  os          OS / arch string.
 * @property {number}  cpu_cores   Total CPU cores.
 * @property {number}  cpu_pct     Aggregate CPU usage percentage (0-100).
 * @property {number}  mem_total   Total memory in bytes.
 * @property {number}  mem_used    Used memory in bytes.
 * @property {number}  disk_total  Total disk in bytes.
 * @property {number}  disk_used   Used disk in bytes.
 * @property {boolean} is_local    Whether this is the local daemon.
 */

/**
 * @typedef {Object} InfraPort
 * @property {number|null} host       Published host port (null when not published).
 * @property {number}      container  Container-side port.
 * @property {string}     proto      "tcp" | "udp".
 * @property {boolean}    published  Whether the port is published to the host.
 */

/**
 * @typedef {Object} InfraMount
 * @property {string} type         "bind" | "volume" | "tmpfs".
 * @property {string} source       Host path or volume name.
 * @property {string} destination  Container path.
 * @property {string} mode         "rw" | "ro".
 */

/**
 * @typedef {Object} InfraNetworkAttachment
 * @property {string} name  Network name.
 * @property {string} ip    Assigned IP ("" when not connected).
 */

/**
 * @typedef {Object} InfraEnvVar
 * @property {string} k  Variable name.
 * @property {string} v  Variable value (backend masks secrets as "***").
 */

/**
 * @typedef {Object} InfraHealthcheck
 * @property {string} test      Healthcheck command.
 * @property {string} interval  e.g. "30s".
 * @property {number} retries   Retry count.
 */

/**
 * @typedef {Object} InfraContainer
 * @property {string}  id               Full container id.
 * @property {string}  short            Short id (first 12 chars).
 * @property {string}  name             Container name.
 * @property {string}  image            Image reference "repo:tag".
 * @property {string}  image_id         Image SHA.
 * @property {'running'|'exited'|'paused'|'restarting'|'created'|'dead'} state  Lifecycle state.
 * @property {'healthy'|'unhealthy'|'starting'|null} health                     Health status (null if no healthcheck).
 * @property {string}  status_text      docker ps STATUS text, e.g. "Up 3 days".
 * @property {string}  created          ISO 8601.
 * @property {string}  started_at       ISO 8601.
 * @property {number}  uptime_seconds   Seconds since last start.
 * @property {string}  host_id          Owning host (see InfraHost.id).
 * @property {string}  stack            Compose project name ("" when none).
 * @property {string}  service          Compose service name ("" when none).
 * @property {InfraPort[]} ports
 * @property {number}  cpu_pct          Current CPU %.
 * @property {number}  mem_used         Current memory in bytes.
 * @property {number}  mem_limit        Memory limit in bytes.
 * @property {number}  mem_pct          Derived memory percentage.
 * @property {number}  net_rx           Total network received bytes.
 * @property {number}  net_tx           Total network transmitted bytes.
 * @property {number}  block_read       Total block read bytes.
 * @property {number}  block_write      Total block written bytes.
 * @property {number}  restart_count    Number of restarts.
 * @property {string}  restart_policy   e.g. "unless-stopped".
 * @property {Object.<string,string>} labels  docker labels.
 * @property {InfraEnvVar[]} env
 * @property {InfraMount[]}  mounts
 * @property {InfraNetworkAttachment[]} networks
 * @property {string[]} cmd
 * @property {string}  entrypoint
 * @property {InfraHealthcheck|null} healthcheck
 * @property {string|null} url          Exposed app URL (when discoverable).
 * @property {boolean} sysbox           Whether run under the sysbox runtime.
 * @property {number}  pids             Process count.
 */

/**
 * @typedef {Object} InfraStats
 * @property {{cpu_pct:number, mem_used:number, mem_limit:number, net_rx:number, net_tx:number, block_read:number, block_write:number, pids:number}} current
 * @property {{t:string, cpu:number, mem:number}[]} series  Time series (ISO ts + values).
 */

/**
 * Machine-readable endpoint contract. Ship this array to the backend team.
 * @type {{method:string, path:string, desc:string, response:string}[]}
 */
export const INFRA_ENDPOINTS = [
  { method: 'GET',    path: '/api/infra/hosts',              desc: 'List Docker hosts/endpoints.',                     response: '{ hosts: InfraHost[] }' },
  { method: 'GET',    path: '/api/infra/summary',            desc: 'Host gauges + container/image/volume/network counts.', query: 'host', response: '{ host: InfraHost, engine, cpu_pct, cpu_cores, mem_used, mem_total, disk_used, disk_total, counts: {...} }' },
  { method: 'GET',    path: '/api/infra/containers',         desc: 'List containers (filterable).',                    query: 'host,state,stack,q', response: '{ total: number, containers: InfraContainer[] }' },
  { method: 'GET',    path: '/api/infra/containers/:id',     desc: 'Container detail.',                                response: 'InfraContainer' },
  { method: 'GET',    path: '/api/infra/containers/:id/logs',desc: 'Recent log lines.',                                query: 'tail', response: '{ id, lines: { ts, level, msg }[] }' },
  { method: 'GET',    path: '/api/infra/containers/:id/stats',desc: 'CPU / memory time series.',                       response: 'InfraStats' },
  { method: 'POST',   path: '/api/infra/containers/:id/actions', desc: 'start | stop | restart | pause | unpause | kill.', body: '{ action }', response: 'InfraContainer' },
  { method: 'POST',   path: '/api/infra/containers',         desc: 'Create & run a container.',                        body: '{ name, image, ports[]{host,container,proto}, env[]{k,v}, cmd, stack }', response: 'InfraContainer' },
  { method: 'DELETE', path: '/api/infra/containers/:id',     desc: 'Remove a container.',                              response: '{ ok: true }' },
  { method: 'GET',    path: '/api/infra/stacks',             desc: 'Compose projects.',                                query: 'host', response: '{ stacks: { name, path, status, running, total, services[] }[] }' },
  { method: 'GET',    path: '/api/infra/images',             desc: 'Images on the host.',                              query: 'host', response: '{ images: { repo, tag, id, size, created, containers, dangling }[] }' },
  { method: 'GET',    path: '/api/infra/volumes',            desc: 'Volumes on the host.',                             query: 'host', response: '{ volumes: { name, driver, scope, mountpoint, size, stack, in_use, anonymous }[] }' },
  { method: 'GET',    path: '/api/infra/networks',           desc: 'Networks on the host.',                            query: 'host', response: '{ networks: { id, name, driver, scope, subnet, internal, containers[] }[] }' },
  { method: 'GET',    path: '/api/infra/events',             desc: 'Recent Docker daemon events.',                     query: 'host', response: '{ events: { ts, type, action, actor }[] }' },
  { method: 'DELETE', path: '/api/infra/images/:id',         desc: 'Remove an image (fails while a container uses it).', response: '{ ok: true }' },
  { method: 'DELETE', path: '/api/infra/volumes/:name',      desc: 'Remove a volume (fails while it is mounted).',       response: '{ ok: true }' },
  { method: 'DELETE', path: '/api/infra/networks/:id',       desc: 'Remove a network (fails while it has endpoints).',   response: '{ ok: true }' },
  { method: 'POST',   path: '/api/infra/maintenance/prune',  desc: 'Prune one resource class.',                          body: '{ target: images|volumes|networks|build_cache|system, older_than_days, dangling_only, host_id }', response: '{ ok, removed, reclaimed_bytes }' }
]

/* ──────────────────────────────────────────────────────────────────────────
 * 2. MODULE — the public API surface used by the UI
 * ────────────────────────────────────────────────────────────────────────── */

/**
 * Infrastructure module factory.
 * @param {object} API  The codx-junior API instance (see src/api/api.js).
 */
export function infraModule(API) {
  const get = (path) => API.get(path)
  const post = (path, body) => API.post(path, body)
  const del = (path) => API.delete(path)

  const slug = (id) => encodeURIComponent(id)
  const hostQs = (host) => 'host=' + encodeURIComponent(host || 'host-local')

  return {
    /** @type {typeof INFRA_ENDPOINTS} machine-readable backend contract. */
    endpoints: INFRA_ENDPOINTS,

    /** @returns {Promise<{hosts: import('./infra').InfraHost[]}>} */
    hosts: () => get('/api/infra/hosts'),

    /** @returns {Promise<object>} host gauges + counts */
    summary: (host = 'host-local') => get('/api/infra/summary?' + hostQs(host)),

    /**
     * @param {{host?:string,state?:string,stack?:string,q?:string}} params
     * @returns {Promise<{total:number, containers:any[]}>}
     */
    containers: (params = {}) => {
      const q = new URLSearchParams()
      if (params.host) q.set('host', params.host)
      if (params.state) q.set('state', params.state)
      if (params.stack) q.set('stack', params.stack)
      if (params.q) q.set('q', params.q)
      const qs = q.toString()
      return get('/api/infra/containers' + (qs ? '?' + qs : ''))
    },

    container: (id) => get('/api/infra/containers/' + slug(id)),
    logs: (id, tail = 120) => get('/api/infra/containers/' + slug(id) + '/logs?tail=' + tail),
    stats: (id) => get('/api/infra/containers/' + slug(id) + '/stats'),

    /** @param {'start'|'stop'|'restart'|'pause'|'unpause'|'kill'} action */
    action: (id, action) => post('/api/infra/containers/' + slug(id) + '/actions', { action }),

    /** @param {{name:string,image:string,ports?:any[],env?:any[],cmd?:string,stack?:string}} payload */
    create: (payload) => post('/api/infra/containers', payload),
    remove: (id) => del('/api/infra/containers/' + slug(id)),

    stacks: (host = 'host-local') => get('/api/infra/stacks?' + hostQs(host)),
    images: (host = 'host-local') => get('/api/infra/images?' + hostQs(host)),
    volumes: (host = 'host-local') => get('/api/infra/volumes?' + hostQs(host)),
    networks: (host = 'host-local') => get('/api/infra/networks?' + hostQs(host)),
    events: (host = 'host-local') => get('/api/infra/events?' + hostQs(host)),

    /* ── Maintenance ─────────────────────────────────────────────────────── */

    /** Remove a single image. Rejects with 409 while a container still uses it. */
    removeImage: (id) => del('/api/infra/images/' + slug(id)),
    /** Remove a single volume. Rejects with 409 while a container mounts it. */
    removeVolume: (name) => del('/api/infra/volumes/' + slug(name)),
    /** Remove a single network. Rejects with 403 (predefined) or 409 (endpoints). */
    removeNetwork: (id) => del('/api/infra/networks/' + slug(id)),

    /**
     * Prune one resource class.
     * @param {{target:'images'|'volumes'|'networks'|'build_cache'|'system',
     *          older_than_days?:number|null, dangling_only?:boolean, host_id?:string}} payload
     * @returns {Promise<{ok:boolean, removed:number, reclaimed_bytes:number}>}
     */
    prune: (payload = {}) => post('/api/infra/maintenance/prune', payload)
  }
}