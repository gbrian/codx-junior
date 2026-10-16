import { APPS, setPendingParams } from '../config/apps'

export default function Navigate({ $router, $storex }) {

  // ════════════════════════════════════════════════════════════════
  // PROJECT BASE PATH HELPERS
  // Routes are mounted under the active project name, e.g.
  //   /codx-junior/chats   /my.project/desktop   /my-project/settings
  // ════════════════════════════════════════════════════════════════

  // Return the RAW active project name. vue-router percent-encodes route
  // params when it builds the URL, so pre-encoding here would double-encode
  // names with special characters (e.g. "my project" → "my%2520project").
  function activeProjectSegment() {
    return $storex.projects.activeProject?.project_name || ''
  }

  // Location for the project-scoped home, or the unscoped root while no
  // project is active yet (the guard/store scope it once one loads).
  function homeLocation() {
    const projectName = activeProjectSegment()
    return projectName
      ? { name: 'home', params: { projectName } }
      : { name: 'root' }
  }

  // ════════════════════════════════════════════════════════════════
  // ROUTE BUILDERS - Centralized route path generation
  // ════════════════════════════════════════════════════════════════

  const routes = {
    chat: {
      list: () => ({ name: 'chats' }),
      open: (chatId, chatName) => ({
        name: 'chat',
        params: { chatId, chatName }
      }),
      openWithWorkspace: (chatId, chatName, workspaceId, workspaceName) => ({
        name: 'chat-workspace',
        params: { chatId, chatName, workspaceId, workspaceName }
      })
    },
    meet: {
      list: () => ({ name: 'meet' }),
      open: (meetId) => ({
        name: 'meet-session',
        params: { meetId }
      })
    },
    workspace: {
      list: () => ({ name: 'workspaces' }),
      open: (workspaceId, workspaceName) => ({
        name: 'workspace',
        params: { workspaceId, workspaceName }
      })
    },
    browser: {
      list: () => ({ name: 'browsers' }),
      open: (sessionId, sessionName) => ({
        name: 'browser-session',
        params: { sessionId, sessionName }
      })
    },
    kanban: {
      open: () => ({ name: 'kanban' }),
      // Opens the Task Manager directly on the Planning view
      planning: () => ({ name: 'kanban', query: { view: 'planning' } })
    },
    messenger: {
      open: () => ({ name: 'messenger' })
    },
    desktop: {
      open: () => ({ name: 'codx-junior-split' })
    },
    mobile: {
      open: () => ({ name: 'mobile' })
    },
    home: {
      open: () => homeLocation()
    }
  }

  // ════════════════════════════════════════════════════════════════
  // MODE DETECTION - Single vs Desktop
  //
  // The ACTIVE ROUTE defines the mode (never the screen width or a ui
  // store flag):
  //
  //   • Desktop mode → the URL ends with ".../desktop" (route name
  //     "codx-junior-split"). The dockview workspace is mounted, so MANY
  //     apps can stay open at once as side-by-side panels.
  //
  //   • Single mode  → EVERY other route (chats, kanban, messenger, wiki,
  //     file-explorer, mobile…). ONE app at a time, addressed only by its
  //     route path: opening an app replaces the current one.
  //
  // openApp() reads this to decide between creating a panel and pushing a
  // route, so app links behave the same from any screen.
  // ════════════════════════════════════════════════════════════════

  function isDesktopMode() {
    return $router.currentRoute.value.name === 'codx-junior-split'
  }

  // ════════════════════════════════════════════════════════════════
  // UNIFIED APP OPENER
  // The single place that decides between a dockview panel and a route,
  // based on the current mode (Desktop vs Single - see above).
  // Everything else (UI store openers, launchers) funnels here.
  // ════════════════════════════════════════════════════════════════

  function openApp(appKey, payload = {}) {
    const def = APPS[appKey]

    if (!def) {
      console.warn(`[Navigation] openApp: unknown app "${appKey}"`)
      return
    }

    const params = def.desktopParams ? def.desktopParams(payload) : (payload.params || {})

    // ── Single mode (any route but ".../desktop") → update the route ──
    // One app at a time: the app lives in the URL (plus a transient
    // payload hand-off for rich objects that can't be encoded there).
    if (!isDesktopMode()) {
      setPendingParams(def.id, params)
      // The project prefix is injected centrally by the router's push wrapper.
      $router.push(def.route(payload))
      return
    }

    // ── Desktop mode (".../desktop") → open a dockview panel ─────────
    // Panels are additive: opening an app never closes the others.
    const key = def.desktopKey ? def.desktopKey(payload) : appKey
    const tabId = def.desktopTabId ? def.desktopTabId(payload) : payload.tabId

    $storex.ui.showApp({
      key,
      tabId,
      name: payload.name || def.title,
      component: def.component,
      params
    })
  }

  // ════════════════════════════════════════════════════════════════
  // STATE GETTERS
  // ════════════════════════════════════════════════════════════════

  const $navigation = {
    get activeProject() {
      return $storex.projects.activeProject
    },

    get isDesktopMode() {
      // Mode is derived from the route - single source of truth.
      return isDesktopMode()
    },

    get isMobileMode() {
      return $router.currentRoute.value.name === 'mobile'
    },

    get isChatView() {
      const name = $router.currentRoute.value.name
      return name === 'chat' || name === 'chat-workspace'
    },

    get isMeetView() {
      const name = $router.currentRoute.value.name
      return name === 'meet' || name === 'meet-session'
    },

    get isWorkspaceView() {
      const name = $router.currentRoute.value.name
      return name === 'workspace' || name === 'workspaces'
    },

    get isBrowserView() {
      const name = $router.currentRoute.value.name
      return name === 'browsers' || name === 'browser-session'
    },

    get isKanbanView() {
      return $router.currentRoute.value.name === 'kanban'
    },

    get isMessengerView() {
      return $router.currentRoute.value.name === 'messenger'
    },

    get isHomeView() {
      const name = $router.currentRoute.value.name
      return name === 'home' || name === 'root'
    },

    getProjectName() {
      return $storex.projects.activeProject?.project_name || null
    },

    getCurrentRoute() {
      return $router.currentRoute.value
    },

    getChatId() {
      return $router.currentRoute.value.params.chatId || null
    },

    getChatName() {
      return $router.currentRoute.value.params.chatName || null
    },

    getMeetId() {
      return $router.currentRoute.value.params.meetId || null
    },

    getWorkspaceId() {
      return $router.currentRoute.value.params.workspaceId || null
    },

    getWorkspaceName() {
      return $router.currentRoute.value.params.workspaceName || null
    },

    getSessionId() {
      return $router.currentRoute.value.params.sessionId || null
    },

    getSessionName() {
      return $router.currentRoute.value.params.sessionName || null
    },

    get hasChatContext() {
      return this.getChatId() !== null
    },

    get hasMeetContext() {
      return this.getMeetId() !== null
    },

    get hasWorkspaceContext() {
      return this.getWorkspaceId() !== null
    },

    get hasSessionContext() {
      return this.getSessionId() !== null
    },

    // ════════════════════════════════════════════════════════════════
    // INITIALIZATION
    // ════════════════════════════════════════════════════════════════

    init() {
      // Initialize history state on first load
      if (window.history.length === 1) {
        window.history.replaceState(null, '', '/')
        window.history.pushState(null, '', window.location.href)
      }
    },

    async onRouteChanged({ from, to }) {
      // ── OAuth callback ────────────────────────────────────────────
      if (to.path.startsWith('/auth')) {
        const { code, state } = to.query
        const provider = to.path.split('/').reverse()[0]

        if (!provider || !code) {
          $storex.session.onError('Missing OAuth provider or code')
          return homeLocation()
        }

        try {
          await $storex.users.oauthLogin({ provider, code, state })
          return homeLocation()
        } catch (error) {
          $storex.session.onError('Failed to complete OAuth login')
          return homeLocation()
        }
      }

      // ── Unscoped root → project-scoped home ───────────────────────
      if (to.name === 'root') {
        const projectName = activeProjectSegment()
        if (projectName) {
          return { name: 'home', params: { projectName }, replace: true }
        }
        return true
      }

      // ── Standalone routes with name (opt-out of mobile/desktop redirect) ─
      if (!!to.name) {
        return true
      }

      // ── Mobile redirect ──────────────────────────────────────────
      if ($storex.ui.isMobile && to.name !== 'mobile') {
        return { name: 'mobile', replace: true }
      }

      // ── Desktop: redirect /mobile → home ─────────────────────────
      if (!$storex.ui.isMobile && to.name === 'mobile') {
        return { ...homeLocation(), replace: true }
      }

      return true
    },

    // ════════════════════════════════════════════════════════════════
    // UNIFIED APP OPEN (exposed to the UI store & components)
    // ════════════════════════════════════════════════════════════════

    openApp,

    // ════════════════════════════════════════════════════════════════
    // CHAT NAVIGATION
    // ════════════════════════════════════════════════════════════════

    chats: {
      list() {
        $router.push(routes.chat.list())
      },

      open(chatId, chatName) {
        if (!chatId) {
          console.warn('[Navigation] chats.open: invalid chatId', chatId)
          return
        }

        const name = chatName || `chat-${chatId}`
        openApp('chat', {
          chat: {
            id: chatId,
            name,
            owner_project_id: $navigation.activeProject?.project_id
          }
        })
      },

      openWithWorkspace(chatId, chatName, workspaceId, workspaceName) {
        if (!chatId || !workspaceId) {
          console.warn('[Navigation] chats.openWithWorkspace: invalid chat or workspace', { chatId, workspaceId })
          return
        }

        openApp('chat', {
          chat: {
            id: chatId,
            name: chatName || `chat-${chatId}`,
            owner_project_id: $navigation.activeProject?.project_id
          },
          workspace: {
            id: workspaceId,
            name: workspaceName || `workspace-${workspaceId}`
          }
        })
      }
    },

    // ════════════════════════════════════════════════════════════════
    // MEET NAVIGATION
    // ════════════════════════════════════════════════════════════════

    meets: {
      list() {
        openApp('meet', {})
      },

      open(meetId) {
        if (!meetId) {
          console.warn('[Navigation] meets.open: invalid meetId', meetId)
          return
        }
        openApp('meet', { meetId })
      }
    },

    // ════════════════════════════════════════════════════════════════
    // WORKSPACE NAVIGATION
    // ════════════════════════════════════════════════════════════════

    workspaces: {
      list() {
        openApp('workspaces')
      },

      open(workspaceOrId, workspaceName) {
        // Accept either a full workspace object (preferred: it carries name,
        // path and any other metadata) or a legacy (id, name) pair.
        const workspace = (workspaceOrId && typeof workspaceOrId === 'object')
          ? workspaceOrId
          : { key: workspaceOrId, name: workspaceName }

        if (!workspace?.key) {
          console.warn('[Navigation] workspaces.open: invalid workspace', workspaceOrId)
          return
        }

        const name = workspace.name || `workspace-${workspace.key}`

        // Check if currently in chat view
        if ($navigation.isChatView) {
          const chatId = $navigation.getChatId()
          const chatName = $navigation.getChatName()

          if (chatId) {
            $navigation.chats.openWithWorkspace(chatId, chatName, workspace.key, name)
            return
          }
        }

        // Forward the whole workspace under the `workspace` key (same
        // convention as `chat`) so name/path reach the panel params.
        openApp('workspace', { workspace })
      }
    },

    // ════════════════════════════════════════════════════════════════
    // BROWSER NAVIGATION
    // ════════════════════════════════════════════════════════════════

    browsers: {
      list() {
        openApp('browser-sessions')
      },

      open(sessionId, sessionName) {
        if (!sessionId) {
          console.warn('[Navigation] browsers.open: invalid sessionId', sessionId)
          return
        }

        const name = sessionName || `session-${sessionId}`
        const location = $storex.ui.isMobile
          ? routes.browser.open(sessionId, name)
          : null

        if (location) {
          $router.push(location)
          return
        }

        $storex.ui.showApp({
          tabId: `browser-${sessionId}`,
          name,
          component: 'browser-viewer',
          params: {
            sessionId,
            session: { id: sessionId, name }
          }
        })
      }
    },

    // ════════════════════════════════════════════════════════════════
    // PRIMARY APP NAVIGATION
    // ════════════════════════════════════════════════════════════════

    apps: {
      // Generic entry point – used by the UI store (setActiveTab, openers…)
      openApp,

      openHome() {
        $router.push(routes.home.open())
      },

      openDesktop() {
        $router.push(routes.desktop.open())
      },

      openMessenger() {
        openApp('messenger')
      },

      openMeet(meetId) {
        openApp('meet', { meetId })
      },

      openKanban() {
        openApp('tasks')
      },

      // Open the Task Manager directly on the Planning view
      openPlanning() {
        openApp('planning')
      },

      openMobile() {
        $router.push(routes.mobile.open())
      },

      openFileExplorer() {
        openApp('file-explorer')
      },

      openWiki() {
        openApp('wiki')
      },

      openTeam() {
        openApp('team')
      },

      openViews() {
        console.warn('[Navigation] openViews: no Views route yet')
      },

      openProfiles() {
        openApp('profiles')
      },

      openKnowledge() {
        openApp('knowledge')
      },

      openAnalytics() {
        openApp('analytics')
      }
    },

    // ════════════════════════════════════════════════════════════════
    // WORKSPACE CONTEXT (for reading current state)
    // ════════════════════════════════════════════════════════════════

    workspace: {
      getCurrentWorkspace() {
        const workspaceId = $navigation.getWorkspaceId()
        const workspaceName = $navigation.getWorkspaceName()

        if (workspaceId) {
          return { id: workspaceId, name: workspaceName }
        }
        return null
      },

      hasContext() {
        return $navigation.hasWorkspaceContext
      }
    },

    // ════════════════════════════════════════════════════════════════
    // SESSION CONTEXT (for reading current state)
    // ════════════════════════════════════════════════════════════════

    session: {
      getCurrentSession() {
        const sessionId = $navigation.getSessionId()
        const sessionName = $navigation.getSessionName()

        if (sessionId) {
          return { id: sessionId, name: sessionName }
        }
        return null
      },

      hasContext() {
        return $navigation.hasSessionContext
      }
    }
  }

  return $navigation
}