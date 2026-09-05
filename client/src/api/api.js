import { CodxJuniorConnection } from './connection'
import { SocketManager } from './socket'
import { filesModule } from './modules/files'
import { globalSettingsModule } from './modules/globalSettings'
import { analyticsModule } from './modules/analytics'
import { logsModule } from './modules/logs'
import { viewsModule } from './modules/views'
import { chatsModule } from './modules/chats'

/**
 * In-flight request deduplication map.
 * Key: "METHOD:url:serialized_body"
 * Value: Promise
 */
const _inflightRequests = new Map()

/**
 * Static, singleton socket manager shared across all API instances.
 */
let _staticSocketManager = null

/**
 * Build a stable cache key for a request.
 */
function _requestKey(method, url, data) {
  const body = data !== undefined ? JSON.stringify(data) : ''
  return `${method.toUpperCase()}:${url}:${body}`
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

    get(url) {
      return _dedupedRequest('GET', API.connection.prepareUrl(url), undefined, () => API.connection.get(url))
    },
    del(url) {
      return _dedupedRequest('DEL', API.connection.prepareUrl(url), undefined, () => API.connection.del(url))
    },
    post(url, data) {
      return _dedupedRequest('POST', API.connection.prepareUrl(url), data, () => API.connection.post(url, data))
    },
    put(url, data) {
      return _dedupedRequest('PUT', API.connection.prepareUrl(url), data, () => API.connection.put(url, data))
    },
    delete(url) {
      return _dedupedRequest('DELETE', API.connection.prepareUrl(url), undefined, () => API.connection.delete(url))
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
        API.workspaces = workspaces
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
      workspaces: {
        async list() {
          return API.get('/api/workspaces')
        },
        async get(workspaceId) {
          return API.get(`/api/workspaces/${workspaceId}`)
        },
        async create(workspace) {
          return API.post('/api/workspaces', workspace)
        },
        async update(workspace, reprovision = false) {
          return API.put(`/api/workspaces?reprovision=${reprovision ? 1 : 0}`, workspace)
        },
        async delete(workspaceId) {
          return API.del(`/api/workspaces/${workspaceId}`)
        },
        templates: {
          async list() {
            return API.get('/api/workspaces/templates')
          }
        },
        lifecycle: {
          async start(workspaceId) {
            return API.post(`/api/workspaces/${workspaceId}/start`, {})
          },
          async stop(workspaceId) {
            return API.post(`/api/workspaces/${workspaceId}/stop`, {})
          },
          async status(workspaceId) {
            return API.get(`/api/workspaces/${workspaceId}/status`)
          },
          async logs(workspaceId, tail = 200) {
            return API.get(`/api/workspaces/${workspaceId}/logs?tail=${tail}`)
          }
        },
        files: {
          async list(workspaceId) {
            return API.get(`/api/workspaces/${workspaceId}/files`)
          },
          async read(workspaceId, filePath) {
            return API.get(`/api/workspaces/${workspaceId}/file?path=${encodeURIComponent(filePath)}`)
          },
          async write(workspaceId, filePath, content) {
            return API.post(`/api/workspaces/${workspaceId}/file?path=${encodeURIComponent(filePath)}`, 
              { content }, 
              { embedBody: true }
            )
          }
        }
      }
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
    repo: {
      info() {
        return API.get('/api/git/repo/info')
      },
      branches() {
        return API.get('/api/git/repo/branches')
      },
      commits(branch) {
        return API.get(`/api/git/repo/branch/commits?branch=${encodeURIComponent(branch)}`)
      },
      changes({ from_branch, to_branch }) {
        return API.get(`/api/git/repo/changes?from_branch=${encodeURIComponent(from_branch)}&to_branch=${encodeURIComponent(to_branch)}`)
      },
      readFromBranch(path, branch) {
        return API.get(`/api/git/files/content?path=${encodeURIComponent(path)}&branch=${encodeURIComponent(branch)}`)
      },
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

    // CHANGED: Replace inline chats object with lazy-loaded module getter
    get chats() {
      if (!API._chatsModule) {
        API._chatsModule = chatsModule(API)
      }
      return API._chatsModule
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
        return API.post(`/api/profiles`, profile)
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
    browser: {
      message(chat) {
        return API.post('/api/browser', chat)
      },
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