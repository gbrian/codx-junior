/**
 * ============================================================================
 * codx-junior — Infrastructure (Docker) API module
 * File: src/api/modules/infra.js
 * ----------------------------------------------------------------------------
 * BACKEND CONTRACT
 * ----------------
 * This module is written against a proposed REST contract under `/api/infra/*`.
 * Until the backend implements those routes, every method resolves against an
 * in-file mock dataset (see the `MOCK` object below).
 *
 * To switch to live HTTP with ZERO changes at the call sites, set
 * `USE_MOCK = false`. Every request is then issued through the regular
 * `API.get/post/delete` helpers (auth, base url, interceptors all apply).
 *
 * These routes MUST be gated to users with the `admin` role (container start/
 * stop/exec is a privileged operation).
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
 * @property {string} v  Variable value (backend SHOULD mask secrets).
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
  { method: 'GET',    path: '/api/infra/events',             desc: 'Recent Docker daemon events.',                     query: 'host', response: '{ events: { ts, type, action, actor }[] }' }
]

/* ──────────────────────────────────────────────────────────────────────────
 * 2. MOCK — in-file dataset + router (delete once the backend is live)
 * ────────────────────────────────────────────────────────────────────────── */

/** Flip to `false` to hit the real `/api/infra/*` routes. */
const USE_MOCK = false

const MiB = 1024 ** 2
const GiB = 1024 ** 3
const DAY = 86400e3
const HOUR = 3600e3
const MIN = 60e3

const _now = Date.now()
const _isoAgo = (ms) => new Date(_now - ms).toISOString()

let _seedRnd = 1337
function _rnd() { _seedRnd = (_seedRnd * 1103515245 + 12345) % 2147483648; return _seedRnd / 2147483648 }
function _rid(n) { let s = ''; for (let i = 0; i < n; i++) s += '0123456789abcdef'[Math.floor(_rnd() * 16)]; return s }

// MOCK: container factory so seeds stay readable
function C(o) {
  return Object.assign({
    id: '', short: '', name: '', image: '', image_id: 'sha256:' + _rid(12),
    state: 'running', health: null, status_text: '',
    created: _isoAgo(DAY * 3), started_at: _isoAgo(DAY * 3), uptime_seconds: DAY * 3 / 1000,
    host_id: 'host-local', stack: '', service: '',
    ports: [], cpu_pct: 0, mem_used: 0, mem_limit: 1 * GiB, mem_pct: 0,
    net_rx: 0, net_tx: 0, block_read: 0, block_write: 0,
    restart_count: 0, restart_policy: 'unless-stopped',
    labels: {}, env: [], mounts: [], networks: [], cmd: [], entrypoint: '',
    healthcheck: null, url: null, sysbox: false, pids: 0
  }, o)
}

const MOCK = {
  hosts: [
    { id: 'host-local', name: 'codx-junior-host', endpoint: 'unix:///var/run/docker.sock',
      engine: '27.3.1', os: 'Ubuntu 22.04 · linux/amd64', cpu_cores: 8, cpu_pct: 34,
      mem_total: 32 * GiB, mem_used: 12.4 * GiB, disk_total: 512 * GiB, disk_used: 198 * GiB, is_local: true },
    { id: 'host-remote', name: 'build-runner-01', endpoint: 'tcp://10.0.0.21:2376',
      engine: '26.1.4', os: 'Debian 12 · linux/amd64', cpu_cores: 16, cpu_pct: 58,
      mem_total: 64 * GiB, mem_used: 41.2 * GiB, disk_total: 1024 * GiB, disk_used: 610 * GiB, is_local: false }
  ],

  containers: [
    C({
      id: 'a1b2c3d4e5f6', name: 'codx-junior', image: 'codxjunior/codx-junior:latest',
      state: 'running', health: 'healthy', created: _isoAgo(DAY * 21), started_at: _isoAgo(DAY * 3),
      uptime_seconds: 3 * 86400, stack: 'codx-junior', service: 'app', url: 'http://localhost:8001',
      ports: [{ host: 8001, container: 8001, proto: 'tcp', published: true }],
      cpu_pct: 6.4, mem_used: 1.21 * GiB, mem_limit: 4 * GiB, pids: 24,
      net_rx: 812 * MiB, net_tx: 1.9 * GiB, block_read: 340 * MiB, block_write: 1.2 * GiB,
      restart_policy: 'unless-stopped',
      healthcheck: { test: 'curl -f http://localhost:8001/health', interval: '30s', retries: 3 },
      cmd: ['/app/run.sh'], entrypoint: '/docker-entrypoint.sh',
      labels: { 'com.docker.compose.project': 'codx-junior', 'com.docker.compose.service': 'app',
                'traefik.enable': 'true', 'traefik.http.routers.codx.rule': 'Host(`codx.local`)',
                'traefik.http.services.codx.loadbalancer.server.port': '8001' },
      env: [{ k: 'CODX_JUNIOR_WEB_PORT', v: '8001' }, { k: 'CODX_JUNIOR_AUTH', v: 'on' },
            { k: 'DATABASE_URL', v: 'postgresql://codx:***@codx-junior-db:5432/codx' },
            { k: 'REDIS_URL', v: 'redis://codx-junior-cache:6379/0' }],
      mounts: [{ type: 'bind', source: '/home/codx-junior/.codx', destination: '/home/codx-junior/.codx', mode: 'rw' },
               { type: 'volume', source: 'codx_media', destination: '/data/media', mode: 'rw' }],
      networks: [{ name: 'codx-junior_default', ip: '172.18.0.4' }, { name: 'edge', ip: '172.20.0.9' }]
    }),
    C({
      id: 'b2c3d4e5f6a1', name: 'codx-junior-db', image: 'postgres:16-alpine',
      state: 'running', health: 'healthy', created: _isoAgo(DAY * 21), started_at: _isoAgo(DAY * 3),
      uptime_seconds: 3 * 86400, stack: 'codx-junior', service: 'db',
      ports: [{ host: null, container: 5432, proto: 'tcp', published: false }],
      cpu_pct: 1.8, mem_used: 421 * MiB, mem_limit: 2 * GiB, pids: 9,
      net_rx: 220 * MiB, net_tx: 96 * MiB, block_read: 1.4 * GiB, block_write: 2.8 * GiB,
      labels: { 'com.docker.compose.project': 'codx-junior', 'com.docker.compose.service': 'db' },
      env: [{ k: 'POSTGRES_DB', v: 'codx' }, { k: 'POSTGRES_USER', v: 'codx' }, { k: 'PGDATA', v: '/var/lib/postgresql/data' }],
      mounts: [{ type: 'volume', source: 'pgdata', destination: '/var/lib/postgresql/data', mode: 'rw' }],
      networks: [{ name: 'codx-junior_default', ip: '172.18.0.2' }],
      healthcheck: { test: 'pg_isready -U codx', interval: '10s', retries: 5 }
    }),
    C({
      id: 'c3d4e5f6a1b2', name: 'codx-junior-cache', image: 'redis:7-alpine',
      state: 'running', created: _isoAgo(DAY * 21), started_at: _isoAgo(DAY * 3), uptime_seconds: 3 * 86400,
      stack: 'codx-junior', service: 'cache',
      ports: [{ host: null, container: 6379, proto: 'tcp', published: false }],
      cpu_pct: 0.4, mem_used: 88 * MiB, mem_limit: 512 * MiB, pids: 6,
      net_rx: 140 * MiB, net_tx: 210 * MiB,
      labels: { 'com.docker.compose.project': 'codx-junior', 'com.docker.compose.service': 'cache' },
      env: [{ k: 'REDIS_ARGS', v: '--appendonly yes' }],
      mounts: [{ type: 'volume', source: 'redis_data', destination: '/data', mode: 'rw' }],
      networks: [{ name: 'codx-junior_default', ip: '172.18.0.3' }]
    }),
    C({
      id: 'd4e5f6a1b2c3', name: 'traefik', image: 'traefik:v3.0',
      state: 'running', health: 'healthy', created: _isoAgo(DAY * 40), started_at: _isoAgo(DAY * 5),
      uptime_seconds: 5 * 86400, stack: 'edge', service: 'proxy', url: 'http://localhost:8080',
      ports: [{ host: 80, container: 80, proto: 'tcp', published: true },
              { host: 443, container: 443, proto: 'tcp', published: true },
              { host: 8080, container: 8080, proto: 'tcp', published: true }],
      cpu_pct: 1.1, mem_used: 96 * MiB, mem_limit: 256 * MiB, pids: 11,
      net_rx: 4.2 * GiB, net_tx: 9.8 * GiB,
      labels: { 'com.docker.compose.project': 'edge', 'traefik.enable': 'true' },
      env: [{ k: 'TRAEFIK_API_DASHBOARD', v: 'true' }, { k: 'TRAEFIK_PROVIDERS_DOCKER', v: 'true' }],
      mounts: [{ type: 'bind', source: '/var/run/docker.sock', destination: '/var/run/docker.sock', mode: 'ro' },
               { type: 'volume', source: 'traefik_acme', destination: '/acme.json', mode: 'rw' }],
      networks: [{ name: 'edge', ip: '172.20.0.2' }]
    }),
    C({
      id: 'e5f6a1b2c3d4', name: 'ollama', image: 'ollama/ollama:0.3.12',
      state: 'running', created: _isoAgo(DAY * 14), started_at: _isoAgo(DAY * 2),
      uptime_seconds: 2 * 86400, stack: 'ai', service: 'embed', url: 'http://localhost:11434',
      ports: [{ host: 11434, container: 11434, proto: 'tcp', published: true }],
      cpu_pct: 22.7, mem_used: 6.1 * GiB, mem_limit: 12 * GiB, pids: 18,
      net_rx: 320 * MiB, net_tx: 1.1 * GiB, block_read: 12 * GiB, block_write: 2.0 * GiB,
      restart_policy: 'always',
      labels: { 'com.docker.compose.project': 'ai', 'com.docker.compose.service': 'embed' },
      env: [{ k: 'OLLAMA_HOST', v: '0.0.0.0:11434' }, { k: 'OLLAMA_KEEP_ALIVE', v: '24h' }],
      mounts: [{ type: 'volume', source: 'ollama_models', destination: '/root/.ollama', mode: 'rw' }],
      networks: [{ name: 'ai_default', ip: '172.22.0.2' }]
    }),
    C({
      id: 'f6a1b2c3d4e5', name: 'monitoring-grafana', image: 'grafana/grafana:11.1.0',
      state: 'running', created: _isoAgo(DAY * 30), started_at: _isoAgo(DAY * 5),
      uptime_seconds: 5 * 86400, stack: 'monitoring', service: 'grafana', url: 'http://localhost:3000',
      ports: [{ host: 3000, container: 3000, proto: 'tcp', published: true }],
      cpu_pct: 0.9, mem_used: 210 * MiB, mem_limit: 1 * GiB, pids: 14,
      net_rx: 180 * MiB, net_tx: 640 * MiB,
      labels: { 'com.docker.compose.project': 'monitoring' },
      env: [{ k: 'GF_SECURITY_ADMIN_USER', v: 'admin' }, { k: 'GF_USERS_ALLOW_SIGN_UP', v: 'false' }],
      mounts: [{ type: 'volume', source: 'grafana_data', destination: '/var/lib/grafana', mode: 'rw' }],
      networks: [{ name: 'monitoring_default', ip: '172.23.0.3' }]
    }),
    C({
      id: 'a6b1c2d3e4f5', name: 'monitoring-prometheus', image: 'prom/prometheus:v2.53.0',
      state: 'running', created: _isoAgo(DAY * 30), started_at: _isoAgo(DAY * 5),
      uptime_seconds: 5 * 86400, stack: 'monitoring', service: 'prometheus', url: 'http://localhost:9090',
      ports: [{ host: 9090, container: 9090, proto: 'tcp', published: true },
              { host: 9100, container: 9100, proto: 'tcp', published: true }],
      cpu_pct: 3.3, mem_used: 780 * MiB, mem_limit: 2 * GiB, pids: 16,
      net_rx: 1.2 * GiB, net_tx: 3.4 * GiB, block_read: 900 * MiB, block_write: 1.6 * GiB,
      labels: { 'com.docker.compose.project': 'monitoring' },
      env: [{ k: 'PROM_RETENTION', v: '30d' }],
      mounts: [{ type: 'volume', source: 'prom_data', destination: '/prometheus', mode: 'rw' }],
      networks: [{ name: 'monitoring_default', ip: '172.23.0.2' }]
    }),
    C({
      id: 'b6c2d3e4f5a1', name: 'registry', image: 'registry:2',
      state: 'running', created: _isoAgo(DAY * 45), started_at: _isoAgo(DAY * 5),
      uptime_seconds: 5 * 86400, stack: 'registry', service: 'registry', url: 'http://localhost:5000',
      ports: [{ host: 5000, container: 5000, proto: 'tcp', published: true }],
      cpu_pct: 0.2, mem_used: 48 * MiB, mem_limit: 256 * MiB, pids: 5,
      net_rx: 60 * MiB, net_tx: 140 * MiB,
      labels: { 'com.docker.compose.project': 'registry' },
      mounts: [{ type: 'volume', source: 'registry_data', destination: '/var/lib/registry', mode: 'rw' }],
      networks: [{ name: 'registry_default', ip: '172.24.0.2' }]
    }),
    C({
      id: 'c6d3e4f5a1b2', name: 'workspace-codx-junior', image: 'codxjunior/codx-junior-default-workspace:latest',
      state: 'running', created: _isoAgo(HOUR * 8), started_at: _isoAgo(HOUR * 8), uptime_seconds: 8 * 3600,
      stack: 'workspaces', service: 'ws-codx-junior', sysbox: true, url: 'http://localhost:9080/codx-junior/preview',
      ports: [{ host: 9080, container: 3000, proto: 'tcp', published: true }],
      cpu_pct: 14.2, mem_used: 2.4 * GiB, mem_limit: 6 * GiB, pids: 42,
      net_rx: 420 * MiB, net_tx: 340 * MiB, block_read: 1.1 * GiB, block_write: 780 * MiB,
      labels: { 'com.docker.compose.project': 'workspaces',
                'traefik.enable': 'true',
                'traefik.http.routers.ws-codx.rule': "PathPrefix('/codx-junior/preview')",
                'traefik.http.services.ws-codx.loadbalancer.server.port': '3000' },
      env: [{ k: 'PUID', v: '1001' }, { k: 'PGID', v: '1001' }, { k: 'CODE_SERVER_PORT', v: '9080' }],
      mounts: [{ type: 'bind', source: '/home/codx-junior-projects/codx-junior', destination: '/home/codx-junior-projects/codx-junior', mode: 'rw' }],
      networks: [{ name: 'workspaces_default', ip: '172.25.0.3' }, { name: 'edge', ip: '172.20.0.21' }]
    }),
    C({
      id: 'd6e4f5a1b2c3', name: 'workspace-frontend', image: 'codxjunior/codx-junior-default-workspace:latest',
      state: 'restarting', created: _isoAgo(HOUR * 3), started_at: _isoAgo(MIN * 2), uptime_seconds: 0,
      stack: 'workspaces', service: 'ws-frontend', sysbox: true, restart_count: 7,
      ports: [{ host: 9081, container: 3000, proto: 'tcp', published: true }],
      cpu_pct: 0, mem_used: 0, mem_limit: 6 * GiB,
      labels: { 'com.docker.compose.project': 'workspaces' },
      env: [{ k: 'PUID', v: '1001' }, { k: 'PGID', v: '1001' }],
      mounts: [{ type: 'bind', source: '/home/codx-junior-projects/frontend', destination: '/home/codx-junior-projects/frontend', mode: 'rw' }],
      networks: [{ name: 'workspaces_default', ip: '172.25.0.4' }]
    }),
    C({
      id: 'e6f5a1b2c3d4', name: 'chrome-browser', image: 'linuxserver/chromium:latest',
      state: 'running', health: 'unhealthy', created: _isoAgo(DAY * 2), started_at: _isoAgo(HOUR * 6),
      uptime_seconds: 6 * 3600, stack: 'browser', service: 'chromium', url: 'http://localhost:3001',
      ports: [{ host: 3001, container: 3000, proto: 'tcp', published: true },
              { host: 3002, container: 3001, proto: 'tcp', published: true }],
      cpu_pct: 4.5, mem_used: 900 * MiB, mem_limit: 2 * GiB, pids: 38,
      net_rx: 240 * MiB, net_tx: 110 * MiB,
      healthcheck: { test: 'curl -f http://localhost:3000', interval: '60s', retries: 3 },
      labels: { 'com.docker.compose.project': 'browser' },
      env: [{ k: 'PUID', v: '1001' }, { k: 'CHROME_CLI', v: '--no-sandbox' }],
      mounts: [{ type: 'volume', source: 'chrome_config', destination: '/config', mode: 'rw' }],
      networks: [{ name: 'browser_default', ip: '172.26.0.2' }]
    }),
    C({
      id: 'f6a1b2c3d4e6', name: 'metrics-agent', image: 'prom/node-exporter:v1.8.1',
      state: 'paused', created: _isoAgo(DAY * 30), started_at: _isoAgo(DAY * 5), uptime_seconds: 5 * 86400,
      stack: 'monitoring', service: 'node-exporter',
      ports: [{ host: 9101, container: 9100, proto: 'tcp', published: true }],
      cpu_pct: 0, mem_used: 22 * MiB, mem_limit: 128 * MiB, pids: 4,
      labels: { 'com.docker.compose.project': 'monitoring' },
      networks: [{ name: 'monitoring_default', ip: '172.23.0.5' }]
    }),
    C({
      id: 'a1c2e3f4b5d6', name: 'backup-cron', image: 'alpine:3.20',
      state: 'exited', created: _isoAgo(DAY * 9), started_at: _isoAgo(HOUR * 2), uptime_seconds: 0,
      status_text: 'Exited (0) 2 hours ago', restart_policy: 'no',
      stack: 'ops', service: 'backup', cpu_pct: 0, mem_used: 0, mem_limit: 128 * MiB,
      cmd: ['/bin/sh', '-c', 'pg_dump … | gzip > /backup/$(date +%F).sql.gz'],
      labels: { 'com.docker.compose.project': 'ops' },
      env: [{ k: 'BACKUP_DIR', v: '/backup' }, { k: 'RETENTION_DAYS', v: '7' }],
      mounts: [{ type: 'volume', source: 'backups', destination: '/backup', mode: 'rw' }],
      networks: [{ name: 'codx-junior_default', ip: '' }]
    }),
    C({
      id: 'b1d2f3a4c5e6', name: 'legacy-api', image: 'node:18-alpine',
      state: 'exited', created: _isoAgo(DAY * 60), started_at: _isoAgo(DAY * 1), uptime_seconds: 0,
      status_text: 'Exited (137) 1 day ago', restart_policy: 'no',
      stack: 'legacy', service: 'api', cpu_pct: 0, mem_used: 0, mem_limit: 512 * MiB,
      ports: [{ host: 4000, container: 4000, proto: 'tcp', published: true }],
      labels: { 'com.docker.compose.project': 'legacy' },
      env: [{ k: 'NODE_ENV', v: 'production' }, { k: 'PORT', v: '4000' }],
      networks: [{ name: 'legacy_default', ip: '' }]
    }),

    /* ---- remote host ---- */
    C({
      id: 'c1e2a3b4d5f6', name: 'builder-01', image: 'docker:27-dind',
      state: 'running', created: _isoAgo(DAY * 6), started_at: _isoAgo(DAY * 6), uptime_seconds: 6 * 86400,
      host_id: 'host-remote', stack: 'ci', service: 'dind', restart_policy: 'always',
      ports: [{ host: 2376, container: 2375, proto: 'tcp', published: true }],
      cpu_pct: 35.5, mem_used: 3.1 * GiB, mem_limit: 8 * GiB, pids: 62,
      net_rx: 2.4 * GiB, net_tx: 1.8 * GiB, block_read: 20 * GiB, block_write: 14 * GiB,
      labels: { 'com.docker.compose.project': 'ci' },
      env: [{ k: 'DOCKER_TLS_CERTDIR', v: '/certs' }],
      mounts: [{ type: 'volume', source: 'dind-storage', destination: '/var/lib/docker', mode: 'rw' }],
      networks: [{ name: 'ci_default', ip: '172.30.0.2' }]
    }),
    C({
      id: 'd1f2b3c4e5a6', name: 'cache-registry-mirror', image: 'registry:2',
      state: 'running', created: _isoAgo(DAY * 6), started_at: _isoAgo(DAY * 6), uptime_seconds: 6 * 86400,
      host_id: 'host-remote', stack: 'registry', service: 'mirror',
      ports: [{ host: 5001, container: 5000, proto: 'tcp', published: true }],
      cpu_pct: 1.4, mem_used: 60 * MiB, mem_limit: 256 * MiB, pids: 5,
      labels: { 'com.docker.compose.project': 'registry' },
      networks: [{ name: 'ci_default', ip: '172.30.0.3' }]
    })
  ],

  events: [
    { ts: _isoAgo(MIN * 2), type: 'container', action: 'restart', actor: 'workspace-frontend' },
    { ts: _isoAgo(MIN * 6), type: 'container', action: 'die', actor: 'workspace-frontend' },
    { ts: _isoAgo(MIN * 24), type: 'health_status', action: 'unhealthy', actor: 'chrome-browser' },
    { ts: _isoAgo(HOUR * 2), type: 'container', action: 'die', actor: 'backup-cron' },
    { ts: _isoAgo(HOUR * 6), type: 'container', action: 'start', actor: 'chrome-browser' },
    { ts: _isoAgo(HOUR * 8), type: 'container', action: 'create', actor: 'workspace-codx-junior' },
    { ts: _isoAgo(HOUR * 20), type: 'image', action: 'pull', actor: 'codxjunior/codx-junior-default-workspace:latest' },
    { ts: _isoAgo(DAY * 1), type: 'container', action: 'kill', actor: 'legacy-api' },
    { ts: _isoAgo(DAY * 2), type: 'volume', action: 'create', actor: 'ollama_models' },
    { ts: _isoAgo(DAY * 3), type: 'network', action: 'create', actor: 'workspaces_default' }
  ],

  images: [
    { repo: 'codxjunior/codx-junior', tag: 'latest', id: 'sha256:' + _rid(12), size: 1.42 * GiB, created: _isoAgo(DAY * 12), dangling: false },
    { repo: 'codxjunior/codx-junior-default-workspace', tag: 'latest', id: 'sha256:' + _rid(12), size: 3.18 * GiB, created: _isoAgo(DAY * 12), dangling: false },
    { repo: 'postgres', tag: '16-alpine', id: 'sha256:' + _rid(12), size: 274 * MiB, created: _isoAgo(DAY * 90), dangling: false },
    { repo: 'redis', tag: '7-alpine', id: 'sha256:' + _rid(12), size: 41 * MiB, created: _isoAgo(DAY * 90), dangling: false },
    { repo: 'traefik', tag: 'v3.0', id: 'sha256:' + _rid(12), size: 176 * MiB, created: _isoAgo(DAY * 60), dangling: false },
    { repo: 'ollama/ollama', tag: '0.3.12', id: 'sha256:' + _rid(12), size: 2.9 * GiB, created: _isoAgo(DAY * 20), dangling: false },
    { repo: 'grafana/grafana', tag: '11.1.0', id: 'sha256:' + _rid(12), size: 512 * MiB, created: _isoAgo(DAY * 40), dangling: false },
    { repo: 'prom/prometheus', tag: 'v2.53.0', id: 'sha256:' + _rid(12), size: 288 * MiB, created: _isoAgo(DAY * 40), dangling: false },
    { repo: 'registry', tag: '2', id: 'sha256:' + _rid(12), size: 24 * MiB, created: _isoAgo(DAY * 120), dangling: false },
    { repo: 'linuxserver/chromium', tag: 'latest', id: 'sha256:' + _rid(12), size: 1.06 * GiB, created: _isoAgo(DAY * 15), dangling: false },
    { repo: 'prom/node-exporter', tag: 'v1.8.1', id: 'sha256:' + _rid(12), size: 22 * MiB, created: _isoAgo(DAY * 40), dangling: false },
    { repo: 'node', tag: '18-alpine', id: 'sha256:' + _rid(12), size: 48 * MiB, created: _isoAgo(DAY * 200), dangling: false },
    { repo: '<none>', tag: '<none>', id: 'sha256:' + _rid(12), size: 812 * MiB, created: _isoAgo(DAY * 30), dangling: true },
    { repo: '<none>', tag: '<none>', id: 'sha256:' + _rid(12), size: 1.9 * GiB, created: _isoAgo(DAY * 21), dangling: true }
  ],

  volumes: [
    { name: 'pgdata', driver: 'local', scope: 'local', mountpoint: '/var/lib/docker/volumes/pgdata/_data', size: 3.6 * GiB, stack: 'codx-junior', anonymous: false, created: _isoAgo(DAY * 21) },
    { name: 'redis_data', driver: 'local', scope: 'local', mountpoint: '/var/lib/docker/volumes/redis_data/_data', size: 64 * MiB, stack: 'codx-junior', anonymous: false, created: _isoAgo(DAY * 21) },
    { name: 'ollama_models', driver: 'local', scope: 'local', mountpoint: '/var/lib/docker/volumes/ollama_models/_data', size: 48.2 * GiB, stack: 'ai', anonymous: false, created: _isoAgo(DAY * 14) },
    { name: 'prom_data', driver: 'local', scope: 'local', mountpoint: '/var/lib/docker/volumes/prom_data/_data', size: 9.4 * GiB, stack: 'monitoring', anonymous: false, created: _isoAgo(DAY * 30) },
    { name: 'grafana_data', driver: 'local', scope: 'local', mountpoint: '/var/lib/docker/volumes/grafana_data/_data', size: 120 * MiB, stack: 'monitoring', anonymous: false, created: _isoAgo(DAY * 30) },
    { name: 'registry_data', driver: 'local', scope: 'local', mountpoint: '/var/lib/docker/volumes/registry_data/_data', size: 14.6 * GiB, stack: 'registry', anonymous: false, created: _isoAgo(DAY * 45) },
    { name: 'traefik_acme', driver: 'local', scope: 'local', mountpoint: '/var/lib/docker/volumes/traefik_acme/_data', size: 4 * 1024, stack: 'edge', anonymous: false, created: _isoAgo(DAY * 40) },
    { name: 'chrome_config', driver: 'local', scope: 'local', mountpoint: '/var/lib/docker/volumes/chrome_config/_data', size: 340 * MiB, stack: 'browser', anonymous: false, created: _isoAgo(DAY * 2) },
    { name: 'backups', driver: 'local', scope: 'local', mountpoint: '/var/lib/docker/volumes/backups/_data', size: 22.1 * GiB, stack: 'ops', anonymous: false, created: _isoAgo(DAY * 9) },
    { name: 'dind-storage', driver: 'local', scope: 'local', mountpoint: '/var/lib/docker/volumes/dind-storage/_data', size: 96 * GiB, stack: 'ci', anonymous: false, created: _isoAgo(DAY * 6), host_id: 'host-remote' },
    { name: 'a4f8d2c1e9b7', driver: 'local', scope: 'local', mountpoint: '/var/lib/docker/volumes/a4f8d2c1e9b7/_data', size: 2 * MiB, stack: 'legacy', anonymous: true, created: _isoAgo(DAY * 60) }
  ],

  networks: [
    { id: 'net_cj', name: 'codx-junior_default', driver: 'bridge', scope: 'local', subnet: '172.18.0.0/16', internal: false, created: _isoAgo(DAY * 21) },
    { id: 'net_edge', name: 'edge', driver: 'bridge', scope: 'local', subnet: '172.20.0.0/16', internal: false, created: _isoAgo(DAY * 40) },
    { id: 'net_ai', name: 'ai_default', driver: 'bridge', scope: 'local', subnet: '172.22.0.0/16', internal: false, created: _isoAgo(DAY * 14) },
    { id: 'net_mon', name: 'monitoring_default', driver: 'bridge', scope: 'local', subnet: '172.23.0.0/16', internal: false, created: _isoAgo(DAY * 30) },
    { id: 'net_ws', name: 'workspaces_default', driver: 'bridge', scope: 'local', subnet: '172.25.0.0/16', internal: false, created: _isoAgo(DAY * 8) },
    { id: 'net_ci', name: 'ci_default', driver: 'bridge', scope: 'local', subnet: '172.30.0.0/16', internal: false, created: _isoAgo(DAY * 6), host_id: 'host-remote' },
    { id: 'net_host', name: 'host', driver: 'host', scope: 'local', subnet: '—', internal: false, created: _isoAgo(DAY * 200) },
    { id: 'net_none', name: 'none', driver: 'null', scope: 'local', subnet: '—', internal: true, created: _isoAgo(DAY * 200) }
  ]
}

/* ── mock derivation helpers ─────────────────────────────────────────────── */

function _fmtDur(sec) {
  if (sec == null) return '—'
  const d = Math.floor(sec / 86400), h = Math.floor((sec % 86400) / 3600), m = Math.floor((sec % 3600) / 60)
  if (d) return d + 'd ' + h + 'h'
  if (h) return h + 'h ' + m + 'm'
  if (m) return m + 'm'
  return Math.floor(sec) + 's'
}

function _applyDerived() {
  MOCK.containers.forEach((c) => {
    c.short = c.id.slice(0, 12)
    c.mem_pct = c.mem_limit ? Math.min(100, Math.round((c.mem_used / c.mem_limit) * 100)) : 0
    if (c.state === 'running' && c.started_at) {
      c.uptime_seconds = Math.max(0, Math.floor((Date.now() - new Date(c.started_at).getTime()) / 1000))
    }
    if (c.state === 'running') c.status_text = 'Up ' + _fmtDur(c.uptime_seconds)
    else if (c.state === 'restarting') c.status_text = 'Restarting (' + (c.restart_count || 1) + ')'
    else if (c.state === 'paused') c.status_text = 'Up ' + _fmtDur(c.uptime_seconds) + ' (Paused)'
    else if (c.state === 'exited') c.status_text = c.status_text || 'Exited (0)'
    else if (c.state === 'created') c.status_text = 'Created'
  })
}
_applyDerived()

function _findContainer(idOrName) {
  return MOCK.containers.find((c) => c.id === idOrName || c.name === idOrName)
}

function _hostContainers(hostId) {
  return MOCK.containers.filter((c) => c.host_id === hostId)
}

function _buildSummary(hostId) {
  const host = MOCK.hosts.find((h) => h.id === hostId) || MOCK.hosts[0]
  const list = _hostContainers(hostId)
  const running = list.filter((c) => c.state === 'running')
  return {
    host,
    engine: host.engine,
    cpu_pct: host.cpu_pct,
    cpu_cores: host.cpu_cores,
    mem_used: host.mem_used,
    mem_total: host.mem_total,
    disk_used: host.disk_used,
    disk_total: host.disk_total,
    counts: {
      total: list.length,
      running: running.length,
      stopped: list.filter((c) => c.state === 'exited' || c.state === 'created').length,
      paused: list.filter((c) => c.state === 'paused').length,
      restarting: list.filter((c) => c.state === 'restarting').length,
      unhealthy: list.filter((c) => c.health === 'unhealthy').length,
      images: _activeImages(hostId).filter((i) => !i.dangling).length,
      volumes: _activeVolumes(hostId).length,
      networks: _activeNetworks(hostId).length
    }
  }
}

function _activeImages(hostId) {
  return MOCK.images.filter((i) => {
    const used = MOCK.containers.some((c) => c.host_id === hostId && c.image === i.repo + ':' + i.tag)
    return used || i.dangling
  }).map((i) => Object.assign({}, i, {
    containers: MOCK.containers.filter((c) => c.host_id === hostId && c.image === i.repo + ':' + i.tag).length
  }))
}

function _activeVolumes(hostId) {
  return MOCK.volumes
    .filter((v) => (v.host_id || 'host-local') === hostId)
    .map((v) => Object.assign({}, v, {
      in_use: MOCK.containers.some((c) => c.host_id === hostId && c.mounts.some((m) => m.source === v.name))
    }))
}

function _activeNetworks(hostId) {
  return MOCK.networks
    .filter((n) => (n.host_id || 'host-local') === hostId)
    .map((n) => Object.assign({}, n, {
      containers: MOCK.containers
        .filter((c) => c.host_id === hostId && c.networks.some((cn) => cn.name === n.name))
        .map((c) => c.name)
    }))
}

function _buildStacks(hostId) {
  const map = {}
  _hostContainers(hostId).forEach((c) => {
    if (!c.stack) return
    map[c.stack] = map[c.stack] || { name: c.stack, host_id: hostId, services: [] }
    map[c.stack].services.push({ service: c.service, name: c.name, state: c.state, health: c.health, id: c.id })
  })
  return Object.values(map).map((s) => {
    const running = s.services.filter((x) => x.state === 'running').length
    s.status = running === s.services.length ? 'running' : running === 0 ? 'stopped' : 'degraded'
    s.running = running
    s.total = s.services.length
    s.path = '/opt/codx-junior/' + s.name + '/docker-compose.yaml'
    return s
  }).sort((a, b) => a.name.localeCompare(b.name))
}

function _genLogs(c, tail) {
  if (!c) return []
  const n = Math.min(tail || 120, 200)
  const svc = c.service || c.name
  const pool = {
    db: [['INFO', 'database system is ready to accept connections'],
         ['INFO', 'checkpoint starting: time'],
         ['INFO', 'checkpoint complete: wrote 41 buffers (0.3%)'],
         ['DEBUG', 'autovacuum: table "chats" pages: 120 removed, 480 remain']],
    cache: [['INFO', 'Background saving started by pid 42'], ['INFO', 'DB saved on disk'], ['DEBUG', 'AOF rewrite finished successfully']],
    app: [['INFO', 'chat request completed model=llama3.1 duration=1.42s tokens=812'],
          ['INFO', 'knowledge search project=codx-junior results=6'],
          ['WARN', 'llm provider slow response (>5s), retrying with fallback model'],
          ['INFO', 'websocket connected user=ada clients=3'],
          ['DEBUG', 'index watcher: 0 files changed']],
    embed: [['INFO', 'embedding batch size=32 tokens=4096'], ['DEBUG', 'model loaded: nomic-embed-text'], ['WARN', 'kv cache near capacity, evicting oldest entry']],
    proxy: [['INFO', 'router codx service=codx loadbalancer=172.18.0.4:8001'], ['INFO', 'Traefik version v3.0 starting'], ['DEBUG', 'certificate renewed domain=codx.local']],
    grafana: [['INFO', 'HTTP Server Listen address=[::]:3000'], ['INFO', 'alerting: rule evaluation completed']],
    prometheus: [['INFO', 'Completed loading of configuration file size=4096'], ['DEBUG', 'scrape target up job=node']],
    registry: [['INFO', 'response completed http.request.method=GET uri=/v2/']],
    chromium: [['INFO', 'websockify: client connected'], ['WARN', 'healthcheck: 3 consecutive failures (unhealthy)']],
    backup: [['INFO', 'pg_dump complete size=1.2GB'], ['INFO', 'uploaded to /backup/2025-05-28.sql.gz'], ['INFO', 'retention: removed 1 old backup']]
  }
  const key = Object.keys(pool).find((k) => svc.includes(k) || (c.image || '').includes(k))
  const base = pool[key] || [['INFO', svc + ' started'],
    ['WARN', 'deprecation notice: legacy config key detected'],
    ['ERROR', 'connection refused to upstream, will retry in 5s'],
    ['INFO', 'healthy']]
  const out = []
  for (let i = n - 1; i >= 0; i--) {
    const tpl = base[Math.floor(_rnd() * base.length)]
    out.push({ ts: _isoAgo(i * 1300 + Math.floor(_rnd() * 900)), level: tpl[0], msg: tpl[1] })
  }
  return out
}

function _genStats(c) {
  if (!c) return { current: {}, series: [] }
  const series = []
  let cpu = c.cpu_pct || 1
  let mem = c.mem_used || 0
  for (let i = 39; i >= 0; i--) {
    cpu = Math.max(0, cpu + (_rnd() - 0.5) * Math.max(0.4, (c.cpu_pct || 1) * 0.25))
    mem = Math.max(0, mem + (_rnd() - 0.5) * (c.mem_limit || GiB) * 0.02)
    series.push({ t: _isoAgo(MIN * i * 1.5), cpu: +cpu.toFixed(1), mem: Math.round(Math.min(mem, c.mem_limit || GiB)) })
  }
  return {
    current: {
      cpu_pct: c.cpu_pct || 0, mem_used: c.mem_used || 0, mem_limit: c.mem_limit || 0,
      net_rx: c.net_rx || 0, net_tx: c.net_tx || 0,
      block_read: c.block_read || 0, block_write: c.block_write || 0, pids: c.pids || 0
    },
    series
  }
}

function _doAction(id, action) {
  const c = _findContainer(id)
  if (!c) return null
  if (action === 'start' || action === 'restart') {
    c.state = 'running'
    if (c.health !== 'unhealthy') c.health = c.healthcheck ? 'starting' : c.health
    c.started_at = new Date().toISOString()
    c.uptime_seconds = 0
    if (action === 'restart') c.restart_count = (c.restart_count || 0) + 1
  } else if (action === 'stop' || action === 'kill') {
    c.state = 'exited'; c.health = null; c.cpu_pct = 0; c.mem_used = 0
  } else if (action === 'pause') {
    c.state = 'paused'; c.cpu_pct = 0
  } else if (action === 'unpause') {
    c.state = 'running'
  }
  c.status_text = ''
  _applyDerived()
  MOCK.events.unshift({ ts: new Date().toISOString(), type: 'container', action, actor: c.name })
  return Object.assign({}, c)
}

function _createContainer(body) {
  const c = C({
    id: _rid(12), name: body.name, image: body.image,
    state: 'running', health: body.healthcheck ? 'starting' : null,
    created: new Date().toISOString(), started_at: new Date().toISOString(), uptime_seconds: 0,
    host_id: body.host_id || 'host-local', stack: body.stack || 'adhoc', service: body.name,
    ports: (body.ports || []).filter(Boolean).map((p) => ({ host: p.host, container: p.container, proto: p.proto || 'tcp', published: true })),
    cpu_pct: 0.6, mem_used: 32 * MiB, mem_limit: 512 * MiB,
    env: (body.env || []).filter(Boolean),
    cmd: (body.cmd || '').trim() ? body.cmd.trim().split(/\s+/) : []
  })
  MOCK.containers.push(c)
  _applyDerived()
  MOCK.events.unshift({ ts: new Date().toISOString(), type: 'container', action: 'create', actor: c.name })
  return Object.assign({}, c)
}

function _removeContainer(id) {
  const i = MOCK.containers.findIndex((x) => x.id === id || x.name === id)
  if (i < 0) return null
  const name = MOCK.containers[i].name
  MOCK.containers.splice(i, 1)
  MOCK.events.unshift({ ts: new Date().toISOString(), type: 'container', action: 'destroy', actor: name })
  return { ok: true }
}

function _listContainers(search) {
  const host = search.get('host') || 'host-local'
  let list = _hostContainers(host)
  const st = search.get('state')
  const stack = search.get('stack')
  const term = (search.get('q') || '').toLowerCase()
  if (st && st !== 'all') list = list.filter((c) => (st === 'unhealthy' ? c.health === 'unhealthy' : c.state === st))
  if (stack && stack !== 'all') list = list.filter((c) => c.stack === stack)
  if (term) {
    list = list.filter((c) =>
      c.name.toLowerCase().includes(term) ||
      c.image.toLowerCase().includes(term) ||
      c.service.toLowerCase().includes(term) ||
      c.stack.toLowerCase().includes(term))
  }
  return { total: list.length, containers: list.map((c) => Object.assign({}, c)) }
}

// MOCK: tiny router reproducing the REST contract above
function _route(method, pathname, search, body) {
  let m
  if (method === 'GET' && pathname === '/api/infra/hosts') return { hosts: MOCK.hosts }
  if (method === 'GET' && pathname === '/api/infra/summary') return _buildSummary(search.get('host') || 'host-local')
  if (method === 'GET' && pathname === '/api/infra/containers') return _listContainers(search)

  if (method === 'GET' && (m = pathname.match(/^\/api\/infra\/containers\/([^/]+)\/logs$/))) {
    return { id: m[1], lines: _genLogs(_findContainer(m[1]), Number(search.get('tail') || 120)) }
  }
  if (method === 'GET' && (m = pathname.match(/^\/api\/infra\/containers\/([^/]+)\/stats$/))) {
    return _genStats(_findContainer(m[1]))
  }
  if (method === 'POST' && (m = pathname.match(/^\/api\/infra\/containers\/([^/]+)\/actions$/))) {
    return _doAction(m[1], body && body.action)
  }
  if (method === 'GET' && (m = pathname.match(/^\/api\/infra\/containers\/([^/]+)$/))) {
    const c = _findContainer(m[1]); return c ? Object.assign({}, c) : null
  }
  if (method === 'DELETE' && (m = pathname.match(/^\/api\/infra\/containers\/([^/]+)$/))) {
    return _removeContainer(m[1])
  }
  if (method === 'POST' && pathname === '/api/infra/containers') return _createContainer(body || {})

  if (method === 'GET' && pathname === '/api/infra/stacks') return { stacks: _buildStacks(search.get('host') || 'host-local') }
  if (method === 'GET' && pathname === '/api/infra/images') return { images: _activeImages(search.get('host') || 'host-local') }
  if (method === 'GET' && pathname === '/api/infra/volumes') return { volumes: _activeVolumes(search.get('host') || 'host-local') }
  if (method === 'GET' && pathname === '/api/infra/networks') return { networks: _activeNetworks(search.get('host') || 'host-local') }
  if (method === 'GET' && pathname === '/api/infra/events') return { events: MOCK.events.slice(0, 60) }
  return null
}

function _mock(method, path, body) {
  return new Promise((resolve, reject) => {
    // MOCK: simulated latency so loading states are visible
    setTimeout(() => {
      try {
        const parsed = new URL(path, 'http://mock.local')
        const result = _route(method, parsed.pathname, parsed.searchParams, body)
        if (result == null) reject(new Error('infra mock: no route for ' + method + ' ' + path))
        else resolve(result)
      } catch (err) {
        reject(err)
      }
    }, 120 + Math.random() * 260)
  })
}

/* ──────────────────────────────────────────────────────────────────────────
 * 3. MODULE — the public API surface used by the UI
 * ────────────────────────────────────────────────────────────────────────── */

/**
 * Infrastructure module factory.
 * @param {object} API  The codx-junior API instance (see src/api/api.js).
 */
export function infraModule(API) {
  const get = (path) => (USE_MOCK ? _mock('GET', path) : API.get(path))
  const post = (path, body) => (USE_MOCK ? _mock('POST', path, body) : API.post(path, body))
  const del = (path) => (USE_MOCK ? _mock('DELETE', path) : API.delete(path))

  const slug = (id) => encodeURIComponent(id)
  const hostQs = (host) => 'host=' + encodeURIComponent(host || 'host-local')

  return {
    /** @type {boolean} true while the UI runs against in-file mock data. */
    isMock: USE_MOCK,
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
    events: (host = 'host-local') => get('/api/infra/events?' + hostQs(host))
  }
}
