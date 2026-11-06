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
 * Every request goes through the regular `API.get/post/put/delete` helpers, so
 * authentication (cookie/bearer), base URL and interceptors all apply.
 *
 * All routes are gated server-side to users with the `admin` role: container
 * start/stop/kill, container creation, host registration, SSH key management,
 * cloud provisioning and any prune/removal are privileged operations. A
 * non-admin caller receives `403`.
 *
 * HOSTS ARE THE ROOT OF THE TREE
 * ------------------------------
 * Every resource endpoint is scoped by `?host=<InfraHost.id>`, so the UI reads
 * `GET /api/infra/hosts` FIRST and sends the selected id on all the following
 * requests. A host id that does not exist answers `404`.
 *
 * SSH KEYS ARE NOT HOST SCOPED
 * ----------------------------
 * A key pair must exist BEFORE the machine it unlocks: cloud provisioning
 * injects the public key during the first boot, and the host entry can only be
 * registered once the machine answers. Keys therefore live in their own
 * collection (`/api/infra/ssh-keys/:id`) and hosts point at one via
 * `InfraHost.ssh_key_id`. The private material NEVER travels to the browser:
 * only the public key line and the server-side file path are exposed.
 *
 * CLOUD CREDENTIALS ARE TRANSIENT
 * -------------------------------
 * `CloudServerRequest.credentials` is forwarded to the provider for that single
 * operation. The backend MUST NOT persist, log or cache it, and the UI keeps it
 * in memory only (wiped as soon as the server was accepted).
 *
 * Error statuses worth handling in the UI:
 *   - `403` predefined Docker network cannot be removed / not an admin.
 *   - `404` the resource (or the host id) does not exist.
 *   - `409` the resource is still in use (image referenced by a container,
 *           volume still mounted, network with attached endpoints, SSH key
 *           assigned to a host).
 *   - `422` host definition or key rejected (unreachable, bad SSH key, bad
 *           port, key material unreadable…).
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
 *
 * ── Identity ──────────────────────────────────────────────────────────────
 * @property {string}  id             Stable host key, e.g. "host-local".
 * @property {string}  name           Human readable host name.
 * @property {'local'|'ssh'} kind     How the daemon is reached: the local
 *                                    socket or a remote machine over SSH.
 * @property {boolean} enabled        Listed/queried by the UI (default true).
 * @property {boolean} is_local       Whether this is the local daemon.
 * @property {string}  notes          Free-form operator notes.
 *
 * ── SSH connection (kind === 'ssh') ───────────────────────────────────────
 * @property {string}  hostname       Hostname or IP of the remote machine.
 * @property {number}  ssh_port       SSH port (default 22).
 * @property {string}  ssh_user       SSH login user (default "root").
 * @property {string}  ssh_key_id     Managed key pair (see InfraSshKey). Takes
 *                                    precedence over `ssh_key_file`.
 * @property {string}  ssh_key_file   Path to a key already present on the
 *                                    codx-junior server (legacy / manual).
 *
 * ── Docker endpoint + TLS ─────────────────────────────────────────────────
 * @property {string}  endpoint       Docker host URI:
 *                                    "unix:///var/run/docker.sock" (local),
 *                                    "ssh://user@host:22" (tunnelled) or
 *                                    "tcp://host:2376" (TLS protected).
 * @property {boolean} tls_verify     Verify the daemon certificate.
 * @property {string}  tls_ca_file    CA certificate path.
 * @property {string}  tls_cert_file  Client certificate path.
 * @property {string}  tls_key_file   Client key path.
 *
 * ── Cloud metadata (filled for provisioned hosts) ─────────────────────────
 * @property {'aws'|'azure'|'hetzner'|null} provider  Provisioning provider.
 * @property {string}  server_id      Provider instance id ("" when manual).
 * @property {string}  region         Provider region / location.
 *
 * ── Read-only engine gauges (filled by GET /summary) ──────────────────────
 * @property {string}  engine         Docker engine version.
 * @property {string}  os             OS / arch string.
 * @property {number}  cpu_cores      Total CPU cores.
 * @property {number}  cpu_pct        Aggregate CPU usage percentage (0-100).
 * @property {number}  mem_total      Total memory in bytes.
 * @property {number}  mem_used       Used memory in bytes.
 * @property {number}  disk_total     Total disk in bytes.
 * @property {number}  disk_used      Used disk in bytes.
 */

/**
 * @typedef {Object} InfraHostPayload
 * Body accepted by POST/PUT /api/infra/hosts and POST /api/infra/hosts/test.
 * @property {string}  [id]
 * @property {string}  name
 * @property {'local'|'ssh'} kind
 * @property {boolean} enabled
 * @property {string}  [hostname]
 * @property {number}  [ssh_port]
 * @property {string}  [ssh_user]
 * @property {string}  [ssh_key_id]
 * @property {string}  [ssh_key_file]
 * @property {string}  [endpoint]
 * @property {boolean} [tls_verify]
 * @property {string}  [tls_ca_file]
 * @property {string}  [tls_cert_file]
 * @property {string}  [tls_key_file]
 * @property {string}  [notes]
 */

/**
 * @typedef {Object} InfraSshKey
 * A managed key pair. The private material stays on the codx-junior server —
 * only its path is reported, so the browser can never leak it.
 *
 * @property {string}  id                Stable key id ("key-…").
 * @property {string}  name              Human readable name (used for files).
 * @property {'rsa'|'ed25519'} algorithm Key algorithm.
 * @property {number}  bits              Key size (256 for ed25519, 4096 for rsa).
 * @property {string}  fingerprint       OpenSSH fingerprint, e.g. "SHA256:ab12…".
 * @property {'generated'|'uploaded'} source  How the pair was created.
 * @property {string}  public_key        OpenSSH public key line ("" for
 *                                       uploaded keys without a .pub file —
 *                                       the backend should derive it).
 * @property {string}  private_key_file  Absolute path on the codx-junior host.
 * @property {string}  public_key_file   Absolute path of the .pub file.
 * @property {string}  created_at        ISO 8601.
 * @property {string[]} hosts            Ids of the hosts using this key.
 */

/**
 * @typedef {Object} SshKeyGenerateRequest
 * @property {string}  name        Base name for the key files.
 * @property {'rsa'|'ed25519'} algorithm
 * @property {number}  [bits]      4096 for rsa, ignored for ed25519.
 * @property {string}  [comment]   Trailing comment of the public key line.
 */

/**
 * @typedef {Object} CloudCredentialField
 * Describes ONE credential input. The wizard renders itself from this, so a
 * new provider needs no front-end change.
 *
 * @property {string}  key          Payload key inside `credentials`.
 * @property {string}  label        Visible label.
 * @property {'text'|'password'|'textarea'} type
 * @property {boolean} required
 * @property {boolean} [secret]     Masked by default (password style).
 * @property {string}  [placeholder]
 * @property {string}  [help]       Where to find the value / required scope.
 */

/**
 * @typedef {Object} CloudProvider
 * @property {'aws'|'azure'|'hetzner'} id
 * @property {string}  name
 * @property {string}  icon              Font Awesome solid class ("fa-cloud").
 * @property {string}  summary           One-line pitch shown on the card.
 * @property {CloudCredentialField[]} credentials
 * @property {{value:string,label:string}[]} regions
 * @property {{value:string,label:string,note?:string}[]} sizes
 * @property {{value:string,label:string}[]} images
 * @property {string}  [default_region]
 * @property {string}  [default_size]
 * @property {string}  [default_image]
 * @property {string}  [ssh_user]        Login user of the image ("ubuntu").
 * @property {boolean} [uploads_key]     The public key is registered at the
 *                                       provider so the instance boots with it.
 */

/**
 * @typedef {Object} CloudServerRequest
 * @property {'aws'|'azure'|'hetzner'} provider
 * @property {Object.<string,string>} credentials  TRANSIENT — never persisted.
 * @property {string}  region
 * @property {string}  name            Hostname / instance name.
 * @property {string}  size            Instance type / SKU / server type.
 * @property {string}  image           Image id, alias or URN.
 * @property {string}  ssh_key_id      Key pair whose public half is injected.
 * @property {string}  [ssh_user]      Login user used to finish the setup.
 * @property {boolean} [install_docker] Install Docker Engine during bootstrap.
 * @property {number[]} [open_ports]   Extra firewall ports (22 is implicit).
 * @property {Object.<string,string>} [tags]
 */

/**
 * @typedef {Object} CloudServerJob
 * @property {string} id
 * @property {string} provider
 * @property {'queued'|'creating'|'booting'|'installing_docker'|'registering'|'ready'|'error'} status
 * @property {number} progress         0-100.
 * @property {string} message          Human readable current step.
 * @property {string} [ip]
 * @property {string} [hostname]
 * @property {string} [host_id]        InfraHost registered once provisioning ends.
 * @property {InfraHost} [host]        The host document itself (optional).
 * @property {{ts:string, level:string, msg:string}[]} logs
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
 * @typedef {Object} InfraStack
 * One docker compose project (a compose file with N services).
 *
 * `source` distinguishes a stack known through its running containers
 * (`runtime`) from a compose file discovered by scanning the active project
 * (`project`). A discovered project that was never started is still listed,
 * with `status: 'stopped'` and `declared_services`, so the UI can start it.
 *
 * The command surface mirrors `docker compose <action>`:
 * `up` (labelled "Start" in the UI — it is the only action that CREATES the
 * missing containers), `stop`, `restart`, `build`, `pull` and `down`
 * (containers + networks removed, named volumes kept).
 *
 * @property {string}  name           Compose project name (defaults to the folder).
 * @property {string}  [label]        Display label (disambiguated on name clashes).
 * @property {string}  path           Compose file path on the host.
 * @property {'running'|'degraded'|'stopped'} status
 * @property {number}  running        Services currently running.
 * @property {number}  total          Services declared by the compose file.
 * @property {InfraContainer[]} services  One entry per service (container subset).
 * @property {'runtime'|'project'} [source]
 * @property {string[]} [files]       Compose files passed to the CLI (base + override).
 * @property {string}  [project]      codx-junior project that owns the files.
 * @property {string}  [project_root] Project root the files live under.
 * @property {string}  [relative_path] Primary compose file, relative to the root.
 * @property {string[]} [declared_services] Services declared by the file(s).
 * @property {string}  [error]        Parse error of the compose file(s).
 */

/**
 * @typedef {Object} InfraDockerfile
 * A Dockerfile discovered by scanning the active project.
 *
 * @property {string}  name
 * @property {string}  path
 * @property {string}  relative_path
 * @property {string}  directory
 * @property {string}  context          Build context directory.
 * @property {string}  project          codx-junior project that owns the file.
 * @property {string}  project_root
 * @property {string[]} base_images     FROM references.
 * @property {string[]} stages          Named stages.
 * @property {number}  stage_count
 * @property {boolean} has_dockerignore
 * @property {string}  compose_project  Compose project that builds this file.
 * @property {string}  compose_service  Compose service that builds this file.
 */

/**
 * @typedef {Object} InfraProjectDocker
 * Response of `GET /api/infra/project/docker`.
 *
 * @property {{name:string, path:string, codx_path:string}|null} project
 * @property {string[]} roots
 * @property {InfraStack[]} compose
 * @property {InfraDockerfile[]} dockerfiles
 * @property {string} scanned_at
 * @property {boolean} cached
 * @property {string} message
 */

/**
 * @typedef {Object} InfraStats
 * @property {{cpu_pct:number, mem_used:number, mem_limit:number, net_rx:number, net_tx:number, block_read:number, block_write:number, pids:number}} current
 * @property {{t:string, cpu:number, mem:number}[]} series  Time series (ISO ts + values).
 */

/**
 * Machine-readable endpoint contract. Ship this array to the backend team.
 * @type {{method:string, path:string, desc:string, body?:string, query?:string, response:string}[]}
 */
export const INFRA_ENDPOINTS = [
  { method: 'GET',    path: '/api/infra/hosts',              desc: 'List Docker hosts/endpoints.',                     response: '{ hosts: InfraHost[] }' },
  { method: 'POST',   path: '/api/infra/hosts',              desc: 'Register a Docker host (local socket or SSH).',    body: 'InfraHostPayload', response: 'InfraHost' },
  { method: 'PUT',    path: '/api/infra/hosts/:id',          desc: 'Update a Docker host connection settings.',        body: 'InfraHostPayload', response: 'InfraHost' },
  { method: 'DELETE', path: '/api/infra/hosts/:id',          desc: 'Remove a Docker host (containers keep running).',  response: '{ ok: true }' },
  { method: 'POST',   path: '/api/infra/hosts/test',         desc: 'Probe an unsaved host definition (SSH + daemon).', body: 'InfraHostPayload', response: '{ ok: boolean, message: string, engine?: string, os?: string }' },
  { method: 'GET',    path: '/api/infra/ssh-keys',           desc: 'List managed key pairs (public halves only).',     response: '{ keys: InfraSshKey[] }' },
  { method: 'POST',   path: '/api/infra/ssh-keys/generate',  desc: 'Generate an ED25519 / RSA key pair.',              body: 'SshKeyGenerateRequest', response: 'InfraSshKey' },
  { method: 'POST',   path: '/api/infra/ssh-keys/upload',    desc: 'Import an existing PRIVATE key (multipart).',      body: 'multipart: name, private_key (file), public_key (file, optional)', response: 'InfraSshKey' },
  { method: 'GET',    path: '/api/infra/ssh-keys/:id',       desc: 'Key detail, includes the public key line.',        response: 'InfraSshKey' },
  { method: 'GET',    path: '/api/infra/ssh-keys/:id/public-key', desc: 'Download the .pub file.',                     response: 'text/plain' },
  { method: 'DELETE', path: '/api/infra/ssh-keys/:id',       desc: 'Delete a key pair (409 while a host uses it).',    response: '{ ok: true }' },
  { method: 'GET',    path: '/api/infra/cloud/providers',    desc: 'Cloud provider catalog (credential fields, regions, sizes, images).', response: '{ providers: CloudProvider[] }' },
  { method: 'POST',   path: '/api/infra/cloud/validate',     desc: 'Check transient credentials (nothing is stored).', body: '{ provider, credentials, region? }', response: '{ ok: boolean, account?: string, message: string }' },
  { method: 'POST',   path: '/api/infra/cloud/servers',      desc: 'Create a Docker server (async job).',              body: 'CloudServerRequest', response: 'CloudServerJob' },
  { method: 'GET',    path: '/api/infra/cloud/servers/:id',  desc: 'Provisioning progress + resulting host.',           response: 'CloudServerJob' },
  { method: 'DELETE', path: '/api/infra/cloud/servers/:id',  desc: 'Destroy a cloud server and its host entry.',        response: '{ ok: true }' },
  { method: 'GET',    path: '/api/infra/summary',            desc: 'Host gauges + container/image/volume/network counts.', query: 'host', response: '{ host: InfraHost, engine, cpu_pct, cpu_cores, mem_used, mem_total, disk_used, disk_total, counts: {...} }' },
  { method: 'GET',    path: '/api/infra/containers',         desc: 'List containers (filterable).',                    query: 'host,state,stack,q', response: '{ total: number, containers: InfraContainer[] }' },
  { method: 'GET',    path: '/api/infra/containers/:id',     desc: 'Container detail.',                                response: 'InfraContainer' },
  { method: 'GET',    path: '/api/infra/containers/:id/logs',desc: 'Recent log lines.',                                query: 'tail', response: '{ id, lines: { ts, level, msg }[] }' },
  { method: 'GET',    path: '/api/infra/containers/:id/stats',desc: 'CPU / memory time series.',                       response: 'InfraStats' },
  { method: 'POST',   path: '/api/infra/containers/:id/actions', desc: 'start | stop | restart | pause | unpause | kill.', body: '{ action }', response: 'InfraContainer' },
  { method: 'POST',   path: '/api/infra/containers',         desc: 'Create & run a container.',                        body: '{ name, image, ports[]{host,container,proto}, env[]{k,v}, cmd, stack, host_id }', response: 'InfraContainer' },
  { method: 'DELETE', path: '/api/infra/containers/:id',     desc: 'Remove a container.',                              response: '{ ok: true }' },
  { method: 'GET',    path: '/api/infra/stacks',             desc: 'Compose projects (running + compose files found in the active project).', query: 'host, refresh', response: '{ stacks: InfraStack[] }' },
  { method: 'POST',   path: '/api/infra/stacks/:name/actions', desc: 'Run a compose command: up | stop | restart | build | pull | down.', body: '{ action, host_id, path? }', response: 'InfraStack' },
  { method: 'GET',    path: '/api/infra/stacks/:name/logs',  desc: 'Aggregated compose logs (every service of the stack).', query: 'tail, host', response: '{ name, lines: { ts, level, msg }[] }' },
  { method: 'GET',    path: '/api/infra/project/docker',     desc: 'Compose files + Dockerfiles scanned from the active project (and child projects).', query: 'host, refresh', response: 'InfraProjectDocker' },
  { method: 'POST',   path: '/api/infra/project/dockerfiles/build', desc: 'Build a Dockerfile discovered in the active project.', body: '{ path, tag, context?, target?, build_args?, host_id? }', response: '{ ok, image, tag, dockerfile, context, output[] }' },
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
  const put = (path, body) => API.put(path, body)
  const del = (path) => API.delete(path)

  const slug = (id) => encodeURIComponent(id)
  const hostQs = (host) => 'host=' + encodeURIComponent(host || 'host-local')

  return {
    /** @type {typeof INFRA_ENDPOINTS} machine-readable backend contract. */
    endpoints: INFRA_ENDPOINTS,

    /* ── Hosts (resolve these FIRST — everything else is host scoped) ────── */

    /**
     * @returns {Promise<{hosts: InfraHost[]} | InfraHost[]>}
     * The UI tolerates both shapes: a bare array or `{ hosts: [...] }`.
     */
    hosts: () => get('/api/infra/hosts'),

    /**
     * Register a new Docker host (local socket or remote over SSH).
     * @param {InfraHostPayload} payload
     * @returns {Promise<InfraHost>}
     */
    createHost: (payload) => post('/api/infra/hosts', payload),

    /**
     * Update the connection settings of an existing host.
     * @param {string} id
     * @param {InfraHostPayload} payload
     * @returns {Promise<InfraHost>}
     */
    updateHost: (id, payload) => put('/api/infra/hosts/' + slug(id), payload),

    /**
     * Remove a host. Containers on that machine are left untouched — only the
     * codx-junior registration disappears.
     * @param {string} id
     * @returns {Promise<{ok: true}>}
     */
    deleteHost: (id) => del('/api/infra/hosts/' + slug(id)),

    /**
     * Probe an unsaved host definition (SSH handshake + daemon ping + version).
     * @param {InfraHostPayload} payload
     * @returns {Promise<{ok:boolean, message:string, engine?:string, os?:string}>}
     */
    testHost: (payload) => post('/api/infra/hosts/test', payload),

    /* ── SSH key pairs (host independent: created before the machine) ────── */

    /**
     * @returns {Promise<{keys: InfraSshKey[]} | InfraSshKey[]>}
     * The UI tolerates both shapes. Private material is never included.
     */
    sshKeys: () => get('/api/infra/ssh-keys'),

    /** @param {string} id @returns {Promise<InfraSshKey>} */
    sshKey: (id) => get('/api/infra/ssh-keys/' + slug(id)),

    /**
     * Download the `.pub` file as plain text. Used as a fallback when the list
     * endpoint did not include `public_key` (e.g. an imported key without a
     * companion `.pub`).
     * @param {string} id
     * @returns {Promise<string>}
     */
    sshKeyPublicKey: (id) => get('/api/infra/ssh-keys/' + slug(id) + '/public-key'),

    /**
     * Generate a key pair on the server.
     * @param {SshKeyGenerateRequest} payload
     * @returns {Promise<InfraSshKey>} Includes the public key line.
     */
    generateSshKey: (payload) => post('/api/infra/ssh-keys/generate', payload),

    /**
     * Import an existing private key.
     * @param {FormData} formData `name`, `private_key` (file), `public_key` (file, optional)
     * @returns {Promise<InfraSshKey>}
     */
    uploadSshKey: (formData) => post('/api/infra/ssh-keys/upload', formData),

    /**
     * Delete a key pair. Rejects with `409` while a host still uses it.
     * @param {string} id
     * @returns {Promise<{ok: true}>}
     */
    deleteSshKey: (id) => del('/api/infra/ssh-keys/' + slug(id)),

    /* ── Cloud providers (credentials are transient) ─────────────────────── */

    /**
     * Provider catalog driving the wizard UI.
     * @returns {Promise<{providers: CloudProvider[]} | CloudProvider[]>}
     */
    cloudProviders: () => get('/api/infra/cloud/providers'),

    /**
     * Validate credentials without storing anything.
     * @param {{provider:string, credentials:Object, region?:string}} payload
     * @returns {Promise<{ok:boolean, account?:string, message:string}>}
     */
    validateCloud: (payload) => post('/api/infra/cloud/validate', payload),

    /**
     * Create a Docker server. Returns a job — poll `cloudServer(id)` until
     * `status === 'ready'`.
     * @param {CloudServerRequest} payload
     * @returns {Promise<CloudServerJob>}
     */
    createCloudServer: (payload) => post('/api/infra/cloud/servers', payload),

    /** @param {string} id @returns {Promise<CloudServerJob>} */
    cloudServer: (id) => get('/api/infra/cloud/servers/' + slug(id)),

    /** @param {string} id @returns {Promise<{ok: true}>} */
    destroyCloudServer: (id) => del('/api/infra/cloud/servers/' + slug(id)),

    /* ── Host snapshot & resources ───────────────────────────────────────── */

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

    /** @param {{name:string,image:string,ports?:any[],env?:any[],cmd?:string,stack?:string,host_id?:string}} payload */
    create: (payload) => post('/api/infra/containers', payload),
    remove: (id) => del('/api/infra/containers/' + slug(id)),

    /**
     * Compose projects of the host, merged with the compose files discovered
     * in the active project (so a project that was never started is listed
     * too).
     *
     * @param {string} [host='host-local']
     * @param {{refresh?:boolean}} [options] `refresh` bypasses the scan cache.
     * @returns {Promise<{stacks: InfraStack[]}>}
     */
    stacks: (host = 'host-local', { refresh = false } = {}) =>
      get('/api/infra/stacks?' + hostQs(host) + (refresh ? '&refresh=true' : '')),

    /**
     * Runs ONE compose command against a stack (`docker compose <action>`).
     *
     * `up` is what the UI labels "Start": it is the only action that CREATES
     * the missing containers, which is why a stack that was brought `down` is
     * revived with `up` and not with `start`. `down` removes the containers and
     * the networks — named volumes are KEPT (no `--volumes` flag is sent), so
     * the equivalent of `down -v` is deliberately not exposed.
     *
     * `path` identifies the compose file when the stack was discovered in the
     * project scan (it may have no container yet). The backend validates it
     * against the scan roots before using it.
     *
     * Long running on purpose (build, pull, down): the request resolves once
     * the command settles, and the caller reloads the host snapshot afterwards.
     *
     * @param {string} name   Compose project name.
     * @param {'up'|'stop'|'restart'|'build'|'pull'|'down'} action
     * @param {string} [host='host-local'] InfraHost.id the stack lives on.
     * @param {string} [path] Compose file discovered in the project scan.
     * @returns {Promise<InfraStack|{ok: true}>} refreshed stack (or `{ok:true}`
     *          when the project is gone after `down`).
     */
    stackAction: (name, action, host = 'host-local', path = '') =>
      post('/api/infra/stacks/' + slug(name) + '/actions', {
        action,
        host_id: host,
        ...(path ? { path } : {})
      }),

    /**
     * Aggregated logs of every service in the stack. Compose prefixes each line
     * with its service name in `msg`, so the UI can keep rendering 3 columns.
     * @param {string} name
     * @param {number} [tail=200]
     * @param {string} [host='host-local']
     * @returns {Promise<{name:string, lines:{ts:string,level:string,msg:string}[]}>}
     */
    stackLogs: (name, tail = 200, host = 'host-local') =>
      get('/api/infra/stacks/' + slug(name) + '/logs?tail=' + tail + '&' + hostQs(host)),

    /**
     * Docker assets scanned from the ACTIVE project (scoped by `codx_path`,
     * which the connection appends automatically).
     *
     * @param {string} [host='host-local']
     * @param {{refresh?:boolean}} [options] `refresh` bypasses the scan cache.
     * @returns {Promise<InfraProjectDocker>}
     */
    projectDocker: (host = 'host-local', { refresh = false } = {}) =>
      get('/api/infra/project/docker?' + hostQs(host) + (refresh ? '&refresh=true' : '')),

    /**
     * Build a Dockerfile discovered in the active project.
     *
     * Long running on purpose: the request resolves once `docker build`
     * settles and returns the tail of its output.
     *
     * @param {{path:string, tag?:string, context?:string, target?:string,
     *          build_args?:Object<string,string>, host_id?:string}} payload
     * @returns {Promise<{ok:boolean, image:string, tag:string, dockerfile:string,
     *                    context:string, output:string[]}>}
     */
    buildDockerfile: (payload) => post('/api/infra/project/dockerfiles/build', payload),

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