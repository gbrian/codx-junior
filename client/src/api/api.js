import { CodxJuniorConnection } from './connection'
import { SocketManager } from './socket'
import { filesModule } from './modules/files'
import { globalSettingsModule } from './modules/globalSettings'
import { analyticsModule } from './modules/analytics'
import { logsModule } from './modules/logs'
import { viewsModule } from './modules/views'
import { chatsModule } from './modules/chats'
import { teamsModule } from './modules/teams'
import { workspacesModule } from './modules/workspaces'
import { browsersModule } from './modules/browsers'
import { meetsModule } from './modules/meets'
import { infraModule } from './modules/infra'
import { repoModule } from './modules/repo'
import { consoleModule } from './modules/console'
import { traefikModule } from './modules/traefik'
import { dshModule } from './modules/dsh'
import { RequestCache, hashBody } from './requestCache'
import { requestQueues } from './requestQueue'

/**
 * In-flight request deduplication map.
 * Key: "METHOD:url:body_hash"
 * Value: Promise
 */
const _inflightRequests = new Map()

/**
 * Short-term request cache shared by every API instance.
 *
 * It complements `_inflightRequests`: the dedupe map only lives while a
 * request is on the wire, while the cache keeps the resolved value for a few
 * seconds so the same file read / diff is not repeated by the editor, the diff
 * panel and the chat preview. See `api/requestCache.js`.
 */
const _requestCache = new RequestCache()

/**
 * Per-category request queues, shared by every API instance.
 *
 * The cache above removes *identical* calls; the queues remove the *parallelism*
 * between different ones: a whole diff panel re-rendering schedules dozens of
 * distinct diffs, and firing them all at once saturates the network and the
 * backend. A request that names a queue waits for its turn
 * (`files:read` and `files:diff` run one at a time, with `750 ms` of silence
 * between two consecutive calls so the small requests can go through).
 * See `api/requestQueue.js`.
 */
// `requestQueues` (imported) is the singleton registry: queue name -> queue.

/**
 * Static, singleton socket manager shared across all API instances.
 */
let _staticSocketManager = null

/**
 * Counter used to key requests whose body cannot be serialized (uploads).
 * Two `FormData` uploads are two different requests even when they look alike.
 */
let _uniqueRequestId = 0

/**
 * Build a stable cache key for a request.
 *
 * The body is **hashed** (never stored): a diff carries the whole file content
 * and comparing those strings on every call is exactly what this layer avoids.
 * When the body cannot be serialized a unique key is returned, so the request
 * is never merged with — or served from — another one.
 *
 * @param {string} method - HTTP method.
 * @param {string} url - Prepared url (includes `codx_path`).
 * @param {*} data - Request body.
 * @returns {string} Request key.
 */
function _requestKey(method, url, data) {
  const body = hashBody(data)
  const suffix = body === null ? `~${++_uniqueRequestId}` : body
  return `${method.toUpperCase()}:${url}:${suffix}`
}

/**
 * Dispatch a request to the connection layer.
 *
 * The connection is resolved at call time because it is recreated whenever the
 * active project or the user changes.
 *
 * @param {Object} API - API instance.
 * @param {string} method - HTTP method.
 * @param {string} url - Relative url.
 * @param {*} data - Request body.
 * @returns {Promise<*>} Request promise.
 */
function _send(API, method, url, data) {
  switch (method.toUpperCase()) {
    case 'GET':
      return API.connection.get(url)
    case 'DEL':
      return API.connection.del(url)
    case 'POST':
      return API.connection.post(url, data)
    case 'PUT':
      return API.connection.put(url, data)
    case 'DELETE':
      return API.connection.delete(url)
    default:
      throw new Error(`Unsupported method ${method}`)
  }
}

/**
 * Wrap a request factory in deduplication logic.
 * If an identical request is already in-flight, the new caller
 * receives the same Promise (and therefore the same resolved value).
 */
function _dedupedRequest(method, url, data, requestFn) {
  const key = _requestKey(method, url, data)

  if (_inflightRequests.has(key)) {
    return _inflightRequests.get(key)
  }

  const promise = requestFn().finally(() => {
    _inflightRequests.delete(key)
  })

  _inflightRequests.set(key, promise)
  return promise
}

const initializeAPI = ({ project, user } = {}) => {
  const API = {
    sid: "",
    connection: null,
    _user: user,

    get user () {
      return API._user
    },
    set user(user) {
      API._user = user
      API.initConnection()
    },

    _activeProject: project,
    get activeProject() {
      return this._activeProject
    },
    set activeProject(value) {
      this._activeProject = value
      API.initConnection()
    },

    set interceptors(value) {
      Object.assign(this.connection.interceptors, value)
    },

    initConnection() {
      API.connection = new CodxJuniorConnection({
        settings: API.activeProject,
        user: API.user
      })
    },

    // ─── HTTP helpers ────────────────────────────────────────────────────────

    /**
     * Single entry point of every request.
     *
     * Pipeline, in this order:
     *  1. **cache** — an identical call resolved a moment ago is served locally
     *     (when `ttl` is given). A hit never reaches the queue.
     *  2. **dedupe** — a caller of a request that is already queued or running
     *     receives that same promise instead of enqueuing a second job.
     *  3. **queue** — when `queue` is given the request waits for its turn; the
     *     queue's concurrency decides how many of that category may run at once
     *     (`files:read` and `files:diff` default to **1**, i.e. sequential) and
     *     its gap leaves `750 ms` of silence between two consecutive calls, so
     *     the lighter requests of the app are not stuck behind them.
     *
     * Applies to **POST as well**: the entry key is the hash of the body, so the
     * diff endpoint (`POST /api/files/diff`) is cached and queued exactly like a
     * GET.
     *
     * @param {string} method - HTTP method.
     * @param {string} url - Relative url.
     * @param {*} [data] - Request body.
     * @param {Object} [options] - Cache and queue options.
     * @param {string} [options.key] - Explicit cache key (`API.cacheKey`).
     * @param {number} [options.ttl] - Cache lifetime; omit to only dedupe.
     * @param {boolean} [options.force] - Bypass the cache and refresh the entry.
     * @param {string} [options.queue] - Queue name (`QUEUE_NAMES.fileDiff`, ...):
     * the request waits for a slot and never exceeds the queue concurrency.
     * @param {number} [options.concurrency] - Override the queue concurrency.
     * @param {number} [options.gap] - Override the queue gap (ms between two
     * consecutive requests of that queue).
     * @returns {Promise<*>} Resolved body (the connection unwraps `data`).
     *
     * @example
     * // GET, short-term cached
     * await API.request('GET', url, undefined, { key, ttl: 3000 })
     *
     * // POST, cached by body hash, one diff at a time
     * await API.request('POST', '/api/files/diff', { path, content }, {
     *   ttl: 4000,
     *   queue: 'files:diff'
     * })
     */
    request(method, url, data, { key, ttl, force = false, queue, concurrency, gap } = {}) {
      const preparedUrl = API.connection.prepareUrl(url)
      const send = () => _send(API, method, url, data)
      const requestFn = () => _dedupedRequest(
        method,
        preparedUrl,
        data,
        // The queue sits behind the dedupe map: a duplicate never takes a slot.
        () => (queue ? requestQueues.run(queue, send, { concurrency, gapMs: gap }) : send())
      )
      // No ttl: only concurrent identical calls are merged.
      if (!ttl) return requestFn()
      return _requestCache.run(
        key || _requestKey(method, preparedUrl, data),
        requestFn,
        { ttl, force }
      )
    },

    get(url, options) {
      return API.request('GET', url, undefined, options)
    },
    del(url, options) {
      return API.request('DEL', url, undefined, options)
    },
    post(url, data, options) {
      return API.request('POST', url, data, options)
    },
    put(url, data, options) {
      return API.request('PUT', url, data, options)
    },
    delete(url, options) {
      return API.request('DELETE', url, undefined, options)
    },

    // ─── Short-term cache ────────────────────────────────────────────────────

    /** Short-term request cache instance (see `api/requestCache.js`). */
    get cache() {
      return _requestCache
    },

    /**
     * Build a project-scoped, prefix-friendly cache key.
     *
     * Keys look like `kind|scope|part|part|`, so a prefix always ends on a
     * separator and can be used to invalidate a whole family of entries.
     *
     * @param {string} kind - Entry family (`files:read`, `repo:fileDiff`, ...).
     * @param {...string} parts - Key parts.
     * @returns {string} Cache key.
     *
     * @example
     * API.cacheKey('files:read', 'src/main.js')
     * // => 'files:read|/path/to/project|src/main.js|'
     */
    cacheKey(kind, ...parts) {
      const scope = API.activeProject?.codx_path || ''
      return [kind, scope, ...parts, ''].join('|')
    },

    /**
     * Serve a request through the short-term cache with an explicit key.
     *
     * Prefer `API.get(url, { key, ttl, queue })` / `API.post(url, data, { key, ttl, queue })`
     * in new code: they run through the same cache **and** the in-flight dedupe
     * map **and** the queues. This helper is kept for callers that compose their
     * own request.
     *
     * @param {string} key - Cache key (`cacheKey`).
     * @param {Function} requestFn - Factory returning the request promise.
     * @param {Object} [options] - `{ ttl, force }`.
     * @returns {Promise<*>} Resolved value.
     */
    cached(key, requestFn, options) {
      return _requestCache.run(key, requestFn, options)
    },

    /**
     * Invalidate cached entries: an exact key, a key prefix, a RegExp or a
     * predicate.
     *
     * @param {string|RegExp|Function} matcher - What to invalidate.
     * @returns {string[]} Removed keys.
     *
     * @example
     * API.invalidateCache(API.cacheKey('files:read', path))
     */
    invalidateCache(matcher) {
      return _requestCache.invalidate(matcher)
    },

    /**
     * Subscribe to the cache updates of a key (`'*'` receives every key).
     * Use it to reload a view after a write invalidated the entry.
     *
     * @param {string} key - Cache key or `'*'`.
     * @param {Function} handler - Receives `{ key, value, event }`.
     * @returns {Function} Unsubscribe function.
     */
    onCacheUpdate(key, handler) {
      return _requestCache.subscribe(key, handler)
    },

    // ─── Request queues ──────────────────────────────────────────────────────

    /** Per-category request queues (see `api/requestQueue.js`). */
    get queues() {
      return requestQueues
    },

    /**
     * Change the concurrency of a queue at runtime (`1` = strictly sequential).
     *
     * Useful when a view needs more throughput, e.g. two reads at a time while a
     * large file list loads.
     *
     * @param {string} name - Queue name (`QUEUE_NAMES.fileRead`, ...).
     * @param {number} concurrency - Max requests on the wire.
     * @returns {Object} The queue.
     *
     * @example
     * API.setQueueConcurrency('files:read', 2)
     */
    setQueueConcurrency(name, concurrency) {
      return requestQueues.setConcurrency(name, concurrency)
    },

    /**
     * Change the idle time left between two consecutive heavy requests of a
     * queue (`0` = back-to-back, no breathing room).
     *
     * The gap is what lets the small calls of the app go through while a diff
     * panel is loading: while the queue cools down nothing of that category is on
     * the wire.
     *
     * @param {string} name - Queue name (`QUEUE_NAMES.fileDiff`, ...).
     * @param {number} gapMs - Milliseconds to wait after a request finishes.
     * @returns {Object} The queue.
     *
     * @example
     * API.setQueueGap('files:diff', 0)      // no spacing
     * API.setQueueGap('files:read', 1500)   // even gentler
     */
    setQueueGap(name, gapMs) {
      return requestQueues.setGap(name, gapMs)
    },

    /**
     * Snapshot of every queue:
     * `{ concurrency, gapMs, cooldownMs, active, pending, queued, peak }`.
     * Handy from the dev tools console while tuning the limits.
     *
     * @returns {Object} Stats per queue name.
     *
     * @example
     * console.table(API.queueStats)
     */
    get queueStats() {
      return requestQueues.stats()
    },

    // ─── Socket management (static/singleton) ────────────────────────────────

    initSocket({ onConnect, onDisconnect, onEvent } = {}) {
      if (_staticSocketManager) {
        _staticSocketManager.disconnect()
      }

      _staticSocketManager = new SocketManager({
        onConnect(socketId) {
          API.sid = socketId
          if (typeof onConnect === 'function') onConnect(socketId)
        },
        onDisconnect() {
          API.sid = ''
          if (typeof onDisconnect === 'function') onDisconnect()
        },
        onEvent(payload) {
          if (typeof onEvent === 'function') onEvent(payload)
        }
      })

      _staticSocketManager.connect()
      return _staticSocketManager
    },

    get socket() {
      return _staticSocketManager
    },

    disconnectSocket() {
      if (_staticSocketManager) {
        _staticSocketManager.disconnect()
        _staticSocketManager = null
      }
    },

    // ─── Domain helpers ──────────────────────────────────────────────────────

    oauth: {
      async getOAuthLoginUrl(provider) {
        const redirect_uri = encodeURIComponent(window.location.origin + `/auth/${provider}`)
        return await API.get(`/api/users/oauth-login-url/${provider}?redirect_uri=${redirect_uri}`)
      },
      async oauthLogin({ oauth_provider, code, state }) {
        const redirect_uri = encodeURIComponent(window.location.origin + `/auth/${oauth_provider}`)
        const data = await API.post('/api/users/oauth-login', {
          oauth_provider,
          code,
          state,
          redirect_uri
        })
        API.user = data
        localStorage.setItem("CODX_USER", JSON.stringify(API.user))
        await API.onUserLogin()
        return data
      }
    },
    users: {
      async list() {
        API.userNetwork = await API.get('/api/users')
        return API.userNetwork
      },
      async login(user) {
        if (!user) {
          try {
            user = API.user = JSON.parse(localStorage.getItem("CODX_USER"))
            API.initConnection()
          } catch {}
          if (!user) return null
        }
        const data = await API.post('/api/users/login', user)
        API.user = data
        localStorage.setItem("CODX_USER", JSON.stringify(API.user))
        await API.onUserLogin()
        return data
      },
      async save(user) {
        const data = await API.put('/api/users', user)
        API.user = data
        localStorage.setItem("CODX_USER", JSON.stringify(API.user))
        return data
      },
      async logout() {
        API.user = null
        API.activeProject = {}
        localStorage.removeItem("CODX_USER")
      },
      async refreshInfo() {
        const data = await API.get('/api/users/me/refresh')
        if (data && API.user) {
          API.user = {
            ...API.user,
            token_usage_today: data.token_usage_today,
            token_limits_today: data.token_limits_today,
            token_limit_rules: data.token_limit_rules,
            token_limit_requests: data.token_limit_requests,
          }
        }
        return data
      }
    },
    apps: {
      async list() {
        const apps = await API.get('/api/apps')
        return apps
      },
      async run(appName) {
        const data = await API.get(`/api/apps/run?app=${appName}`)
        return data
      },
      async runScript(script) {
        const data = await API.post('/api/run/script', { script })
        return data
      }
    },
    async project(projectOrId) {
      if (!projectOrId.codx_path) {
        const existingProject = API.allProjects.find(p => p.id === projectOrId || p.project_name === projectOrId)
        if (!existingProject) {
          throw new Error("Invalid projectOrId: " + JSON.stringify(projectOrId))
        }
        projectOrId = existingProject
      }
      if (projectOrId.codx_path === API.settings.codx_path) {
        return API
      }
      return initializeAPI({ ...API, project: projectOrId })
    },
    projects: {
      async list(withMetrics) {
        const { projects, workspaces } = await API.get(`/api/projects?with_metrics=${withMetrics ? 1 : 0}`)
        API.allProjects = projects
        API.allWorkspaces = workspaces
        API.allProjects.forEach(p => {
          const projectPath = p.abs_project_path
          p.parentProject = API.allProjects
            .filter(p => p.abs_project_path != projectPath && projectPath.startsWith(p.abs_project_path))
            .sort((a, b) => a.abs_project_path > b.abs_project_path ? -1 : 1)[0]
        })
        return API.allProjects
      },
      create(projectPath) {
        return API.post('/api/projects?project_path=' + encodeURIComponent(projectPath), {})
      },
      delete() {
        localStorage.setItem("API_SETTINGS", "")
        API.del('/api/projects')
        API.activeProject = null
      },
      async readme() {
        const data = await API.get('/api/projects/readme')
        return data
      },
      async watch(watching) {
        const settings = await API.settings.read()
        settings.watching = watching
        API.settings.save(settings)
      },
      test() {
        return API.get('/api/project/script/test')
      },
      loadIssue(url) {
        return API.get('/api/github/issues/read?issue_url=' + encodeURIComponent(url))
      },
      ai: {
        models: {
          list() {
            return API.get('/api/projects/ai/models')
          },
          reload(model) {
            return API.post('/api/projects/ai/models/reload', model)
          }
        }
      },
      async metrics() {
        const data = await API.get('/api/projects/metrics')
        return data
      },
      get workspaces() {
        if (!API._workspaceModule) {
          API._workspaceModule = workspacesModule(API)
        }
        return API._workspaceModule
      },
    },

    /**
     * Traefik maintenance: merged routes, target catalog and the global /
     * per-project custom rule stores. See api/modules/traefik.js.
     */
    get traefik() {
      if (!API._traefikModule) {
        API._traefikModule = traefikModule(API)
      }
      return API._traefikModule
    },

    github: {
      issues: {
        helpWanted(query) {
          const qs = query ? `?query=${encodeURIComponent(query)}` : ''
          return API.get(`/api/github/issues/help-wanted${qs}`)
        },
        read(issueUrl) {
          return API.get(`/api/github/issues/read?issue_url=${encodeURIComponent(issueUrl)}`)
        },
        async process(issueUrl) {
          return await API.get(`/api/github/issues/ai/process?issue_url=${encodeURIComponent(issueUrl)}`)
        }
      }
    },

    /**
     * DSH Harness bridge: connection settings, health, sync and task triggers.
     * See `api/modules/dsh.js`.
     */
    get dsh() {
      if (!API._dshModule) {
        API._dshModule = dshModule(API)
      }
      return API._dshModule
    },

    /**
     * Git repository API: branches, commits, graph, working tree, remotes
     * and the local PR lifecycle. See `api/modules/repo.js`.
     */
    get repo() {
      if (!API._repoModule) {
        API._repoModule = repoModule(API)
      }
      return API._repoModule
    },

    /**
     * Console API: run shell commands and project console scripts on the host
     * (`GET /api/console/info`, `POST /api/console/execute`).
     * See `api/modules/console.js`.
     */
    get console() {
      if (!API._consoleModule) {
        API._consoleModule = consoleModule(API)
      }
      return API._consoleModule
    },

    settings: {
      async read() {
        const data = await API.get('/api/settings')
        API.activeProject = { ...API.activeProject || {}, ...data }
        if (API.activeProject) {
          localStorage.setItem("API_SETTINGS", JSON.stringify(data))
        }
        return data
      },
      async save(settings) {
        await API.put('/api/settings?', settings || { ...API.activeProject, $api: null, $state: null })
        return API.settings.read()
      },
      get global() {
        if (!API._globalSettingsModule) {
          API._globalSettingsModule = globalSettingsModule(API)
        }
        return API._globalSettingsModule
      }
    },
    knowledge: {
      status() {
        return API.get('/api/knowledge/status')
      },
      files() {
        return API.get('/api/knowledge/files')
      },
      reload() {
        return API.get('/api/knowledge/reload')
      },
      reloadFolder(path) {
        return API.post(`/api/knowledge/reload-path`, { path })
      },
      indexFilesBackground(filePaths) {
        if (!_staticSocketManager) {
          throw new Error('Socket not connected')
        }
        return new Promise((resolve, reject) => {
          const timeoutId = setTimeout(() => {
            reject(new Error('Index operation timed out'))
          }, 30000)
          
          _staticSocketManager.emit('codx-junior-index-knowledge', {
            file_paths: filePaths,
            codx_path: API.activeProject?.codx_path
          }, (response) => {
            clearTimeout(timeoutId)
            if (response?.error) {
              reject(new Error(response.error))
            } else {
              resolve(response)
            }
          })
        })
      },
      search({
        searchTerm: search_term,
        searchType: search_type,
        documentSearchType: document_search_type,
        cutoffScore: document_cutoff_score,
        cutoffRag: document_cutoff_rag,
        documentCount: document_count
      }) {
        return API.post(`/api/knowledge/reload-search`, {
          search_term,
          search_type,
          document_search_type,
          document_cutoff_score,
          document_cutoff_rag,
          document_count
        })
      },
      aiSearch(query) {
        return API.get(`/api/knowledge/ai-search?query=${encodeURIComponent(query)}`)
      },
      agentSearch(request, maxIterations = 3) {
        return API.get(
          `/api/knowledge/agent-search?request=${encodeURIComponent(request)}&max_iterations=${maxIterations}`
        )
      },
      agentSearchBackground(request, maxIterations = 3) {
        if (!_staticSocketManager) {
          throw new Error('Socket not connected')
        }
        return new Promise((resolve, reject) => {
          const timeoutId = setTimeout(() => {
            reject(new Error('Agent search operation timed out'))
          }, 300000)
          
          _staticSocketManager.emit('codx-junior-agent-search', {
            request: request,
            max_iterations: maxIterations
          }, (response) => {
            clearTimeout(timeoutId)
            if (response?.error) {
              reject(new Error(response.error))
            } else {
              resolve(response)
            }
          })
        })
      },
      onAgentSearchProgress(callback) {
        if (!_staticSocketManager) {
          throw new Error('Socket not connected')
        }
        _staticSocketManager.on('codx-junior-agent-search-progress', callback)
      },
      onAgentSearchComplete(callback) {
        if (!_staticSocketManager) {
          throw new Error('Socket not connected')
        }
        _staticSocketManager.on('codx-junior-agent-search-complete', callback)
      },
      onAgentSearchError(callback) {
        if (!_staticSocketManager) {
          throw new Error('Socket not connected')
        }
        _staticSocketManager.on('codx-junior-agent-search-error', callback)
      },
      delete(sources) {
        return API.post(`/api/knowledge/delete`, { sources })
      },
      deleteIndex(index) {
        return API.del(`/api/knowledge/delete?index=${index}`)
      },
      keywords() {
        return API.get(`/api/knowledge/keywords`)
      },
      searchKeywords(searchQuery) {
        return API.get(`/api/knowledge/keywords?query=${searchQuery}`)
      },
      query(searchQuery) {
        return API.get(`/api/project/search?query=${searchQuery}`)
      },
      summary() {
        return API.get(`/api/knowledge/summary`)
      },
      rebuildSummary() {
        return API.post(`/api/knowledge/summary/rebuild`, {})
      },
      deleteSummary() {
        return API.delete(`/api/knowledge/summary`)
      }
    },

    get chats() {
      if (!API._chatsModule) {
        API._chatsModule = chatsModule(API)
      }
      return API._chatsModule
    },

    get teams() {
      if (!API._teamsModule) {
        API._teamsModule = teamsModule(API)
      }
      return API._teamsModule
    },

    get meets() {
      if (!API._meetsModule) {
        API._meetsModule = meetsModule(API)
      }
      return API._meetsModule
    },

    run: {
      improve(chat) {
        return API.post('/api/run/improve?', chat)
      },
      patch({ file_path, partial_content }) {
        return API.post('/api/run/improve/patch?', { file_path, partial_content })
      },
      edit(chat) {
        return API.post('/api/run/edit?', chat)
      },
      liveEdit({ chat, html, url, message }) {
        return API.post('/api/run/live-edit?', { chat_name: chat.name, html, url, message })
      },
      changesSummary({ branch, rebuild }) {
        return API.get(`/api/run/changes/summary?branch=${branch}&refresh=${rebuild}`).then(({ data }) => data)
      }
    },
    profiles: {
      list() {
        return API.get('/api/profiles')
      },
      load(name) {
        return API.get(`/api/profiles/${name}`)
      },
      save(profile) {
        return API.post('/api/profiles', profile)
      },
      async delete(name) {
        await API.del(`/api/profiles/${name}`)
      },
      tools() {
        return API.get('/api/profiles/tools')
      }
    },
    coder: {
      openFile(file) {
        API.get(`/api/code-server/file/open?file_name=${encodeURIComponent(file)}`)
      }
    },
    images: {
      async uploadFile(file) {
        let formData = new FormData()
        formData.append("file", file)
        const url = await API.post(`/api/images`, formData)
        return window.location.origin + url
      },
      async upload(formData) {
        return await API.post(`/api/images`, formData)
      }
    },
    data: {
      rawQuery({ filter, limit }) {
        return API.get(`/api//data/query?search_filter=${filter}&limit=${limit}`)
      }
    },
    wiki: {
      read(path) {
        return API.get(`/api/wiki?file_path=${path}`)
      },
      rebuild() {
        return API.get('/api/wiki-engine/rebuild')
      },
      build(settings) {
        const search = Object.keys(settings).map(k => `${k}=${settings[k]}`).join("&")
        return API.get('/api/wiki-engine/build?' + search)
      },
      config() {
        return API.get('/api/wiki-engine/config')
      },
      index() {
        return API.get('/api/wiki-engine/index')
      },
      buildDependencyGraph() {
        return API.get('/api/wiki-engine/build?step=build_dependency_graph')
      },
      buildDomains() {
        return API.get('/api/wiki-engine/build?step=build_domains')
      },
      buildModulePage(file_path) {
        return API.get(`/api/wiki-engine/build?step=build_module_page&file_path=${encodeURIComponent(file_path)}`)
      },
      save(wikiSettings) {
        return API.put('/api/wiki-engine', wikiSettings)
      }
    },
    tokenLimits: {
      list() {
        return API.get('/admin/token-limits')
      },
      get(username) {
        return API.get(`/admin/token-limits/${username}`)
      },
      saveRules(username, rules) {
        return API.put(`/admin/token-limits/${username}/rules`, rules)
      },
      deleteRules(username) {
        return API.delete(`/admin/token-limits/${username}/rules`)
      },
      setExtension(username, ruleIndex, extension) {
        return API.post(
          `/admin/token-limits/${username}/rules/${ruleIndex}/extension`,
          { extension }
        )
      },
      listRequests(username, status) {
        const qs = status ? `?status=${status}` : ''
        return API.get(`/admin/token-limits/${username}/requests${qs}`)
      },
      resolveRequest(username, requestId, { status, admin_note }) {
        return API.post(
          `/admin/token-limits/${username}/requests/${requestId}`,
          { status, admin_note }
        )
      }
    },
    get analytics() {
      if (!API._analyticsModule) {
        API._analyticsModule = analyticsModule(API)
      }
      return API._analyticsModule
    },
    get logs() {
      if (!API._logsModule) {
        API._logsModule = logsModule(API)
      }
      return API._logsModule
    },
    engine: {
      update() {
        return API.get('/api/update')
      }
    },
    get browsers() {
      if (!API._browsersModule) {
        API._browsersModule = browsersModule(API)
      }
      return API._browsersModule
    },
    tools: {
      async imageToText(file) {
        const formData = new FormData()
        formData.append("file", file)
        return (await API.post(`/api/image-to-text`, formData)).data
      }
    },
    async onUserLogin() {
      API.allProjects = []
      API.activeProject = null
      await Promise.all([
        API.screen.getScreenResolution(),
        API.settings.global.read(),
        API.users.list()
      ])
    },
    async setActiveProject({ project_id }) {
      if (project_id !== API.activeProject?.project_id) {
        API.activeProject = API.allProjects?.find(p => p.project_id === project_id)
        await API.settings.read()
      }
      return API
    },

    get files() {
      if (!API._filesModule) {
        API._filesModule = filesModule(API)
      }
      return API._filesModule
    },

    get views() {
      if (!API._viewsModule) {
        API._viewsModule = viewsModule(API)
      }
      return API._viewsModule
    },

    get infra() {
      if (!API._infraModule) {
        API._infraModule = infraModule(API)
      }
      return API._infraModule
    },

    screen: {
      display: null,
      async setScreenResolution(resolution) {
        await API.post('/api/screen', { resolution })
        return API.screen.getScreenResolution()
      },
      async getScreenResolution() {
        const display = await API.get('/api/screen')
        API.screen.display = display
        return API.screen.display
      }
    },
    async restart() {
      await API.post("/api/restart")
      let waitTime = 3
      return new Promise((ok, ko) => {
        const ix = setInterval(async () => {
          if (--waitTime) {
            try {
              await API.init()
              clearInterval(ix)
              ok()
            } catch { }
          } else {
            clearInterval(ix)
            ko()
          }
        }, 5000)
      })
    },
    get permissions() {
      const permissions = API.activeProject?.permissions || []
      const isAdmin = API.user?.role === 'admin'
      const isProjectAdmin = permissions.includes("admin")
      return {
        isAdmin,
        isProjectAdmin
      }
    },
  }

  API.initConnection()
  return API
}

export const API = initializeAPI()