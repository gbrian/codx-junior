export default function Navigate({ $router, $storex }) {

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
      open: () => ({ name: 'home' })
    }
  }

  // ════════════════════════════════════════════════════════════════
  // STATE GETTERS
  // ════════════════════════════════════════════════════════════════

  const $navigation = {
    get activeProject() {
      return $storex.projects.activeProject
    },

    get isDesktopMode() {
      return $router.currentRoute.value.name === 'codx-junior-split'
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
      return $router.currentRoute.value.name === 'home'
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
          return '/'
        }

        try {
          await $storex.users.oauthLogin({ provider, code, state })
          return '/'
        } catch (error) {
          $storex.session.onError('Failed to complete OAuth login')
          return '/'
        }
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
        return { name: 'home', replace: true }
      }

      return true
    },

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

        if ($navigation.isDesktopMode) {
          // Desktop mode: show as app panel
          $storex.ui.showApp({
            tabId: chatId,
            name: name,
            component: 'chat',
            params: {
              chat: {
                id: chatId,
                name: name,
                owner_project_id: $navigation.activeProject?.project_id
              }
            }
          })
        } else {
          // Router mode: push to chat route
          $router.push(routes.chat.open(chatId, name))
        }
      },

      openWithWorkspace(chatId, chatName, workspaceId, workspaceName) {
        if (!chatId || !workspaceId) {
          console.warn('[Navigation] chats.openWithWorkspace: invalid chat or workspace', { chatId, workspaceId })
          return
        }

        const chatName_ = chatName || `chat-${chatId}`
        const workspaceName_ = workspaceName || `workspace-${workspaceId}`

        if ($navigation.isDesktopMode) {
          // Desktop mode: show chat with workspace context
          $storex.ui.showApp({
            tabId: chatId,
            name: chatName_,
            component: 'chat',
            params: {
              chat: {
                id: chatId,
                name: chatName_,
                owner_project_id: $navigation.activeProject?.project_id
              },
              workspace: {
                id: workspaceId,
                name: workspaceName_
              }
            }
          })
        } else {
          // Router mode: push to chat-workspace route
          $router.push(routes.chat.openWithWorkspace(chatId, chatName_, workspaceId, workspaceName_))
        }
      }
    },

    // ════════════════════════════════════════════════════════════════
    // MEET NAVIGATION
    // ════════════════════════════════════════════════════════════════

    meets: {
      list() {
        if ($navigation.isDesktopMode) {
          $storex.ui.showApp({
            tabId: 'meet',
            name: 'Meet',
            component: 'meet',
            params: {}
          })
        } else {
          $router.push(routes.meet.list())
        }
      },

      open(meetId) {
        if (!meetId) {
          console.warn('[Navigation] meets.open: invalid meetId', meetId)
          return
        }

        if ($navigation.isDesktopMode) {
          $storex.ui.showApp({
            tabId: `meet-${meetId}`,
            name: `Meet ${meetId.slice(0, 8)}`,
            component: 'meet',
            params: { meetId }
          })
        } else {
          $router.push(routes.meet.open(meetId))
        }
      }
    },

    // ════════════════════════════════════════════════════════════════
    // WORKSPACE NAVIGATION
    // ════════════════════════════════════════════════════════════════

    workspaces: {
      list() {
        if ($navigation.isDesktopMode) {
          // Desktop mode: show as app panel
          $storex.ui.showApp({
            tabId: 'workspaces',
            name: 'Workspaces',
            component: 'workspaces',
            params: {}
          })
        } else {
          // Router mode: navigate to route
          $router.push(routes.workspace.list())
        }
      },

      open(workspaceId, workspaceName) {
        if (!workspaceId) {
          console.warn('[Navigation] workspaces.open: invalid workspaceId', workspaceId)
          return
        }

        const name = workspaceName || `workspace-${workspaceId}`

        // Check if currently in chat view
        if ($navigation.isChatView) {
          // In chat view: open workspace with chat context
          const chatId = $navigation.getChatId()
          const chatName = $navigation.getChatName()

          if (chatId) {
            $navigation.chats.openWithWorkspace(chatId, chatName, workspaceId, name)
            return
          }
        }

        // Not in chat view: open workspace normally
        if ($navigation.isDesktopMode) {
          // Desktop mode: show as app panel
          $storex.ui.showApp({
            tabId: `workspace-${workspaceId}`,
            name: name,
            component: 'workspace',
            params: {
              workspace: {
                id: workspaceId,
                name: name
              }
            }
          })
        } else {
          // Router mode: navigate to workspace route
          $router.push(routes.workspace.open(workspaceId, name))
        }
      }
    },

    // ════════════════════════════════════════════════════════════════
    // BROWSER NAVIGATION
    // ════════════════════════════════════════════════════════════════

    browsers: {
      list() {
        if ($navigation.isDesktopMode) {
          // Desktop mode: show as app panel
          $storex.ui.showApp({
            tabId: 'browsers',
            name: 'Browser Sessions',
            component: 'browsers',
            params: {}
          })
        } else {
          // Router mode: navigate to route
          $router.push(routes.browser.list())
        }
      },

      open(sessionId, sessionName) {
        if (!sessionId) {
          console.warn('[Navigation] browsers.open: invalid sessionId', sessionId)
          return
        }

        const name = sessionName || `session-${sessionId}`

        if ($navigation.isDesktopMode) {
          // Desktop mode: show session viewer
          $storex.ui.showApp({
            tabId: `browser-${sessionId}`,
            name: name,
            component: 'browser-viewer',
            params: {
              sessionId: sessionId,
              session: {
                id: sessionId,
                name: name
              }
            }
          })
        } else {
          // Router mode: navigate to session route
          $router.push(routes.browser.open(sessionId, name))
        }
      }
    },

    // ════════════════════════════════════════════════════════════════
    // PRIMARY APP NAVIGATION
    // ════════════════════════════════════════════════════════════════

    apps: {
      openHome() {
        $router.push(routes.home.open())
      },

      openDesktop() {
        $router.push(routes.desktop.open())
      },

      openMessenger() {
        if ($navigation.isDesktopMode) {
          $storex.ui.showApp({
            tabId: 'messenger',
            name: 'Messenger',
            component: 'messenger',
            params: {}
          })
        } else {
          $router.push(routes.messenger.open())
        }
      },

      openMeet() {
        if ($navigation.isDesktopMode) {
          $storex.ui.openMeet()
        } else {
          $router.push(routes.meet.list())
        }
      },

      openKanban() {
        if ($navigation.isDesktopMode) {
          $storex.ui.showTab('tasks')
        } else {
          $router.push(routes.kanban.open())
        }
      },

      // Open the Task Manager directly on the Planning view
      openPlanning() {
        $storex.ui.openPlanning()
      },

      openMobile() {
        $router.push(routes.mobile.open())
      },

      openFileExplorer() {
        if ($navigation.isDesktopMode) {
          $storex.ui.showTab('files')
        } else {
          $router.push({ path: '/files' })
        }
      },

      openWiki() {
        if ($navigation.isDesktopMode) {
          $storex.ui.showTab('wiki')
        } else {
          $router.push({ path: '/wiki' })
        }
      },

      openTeam() {
        if ($navigation.isDesktopMode) {
          $storex.ui.showApp({
            tabId: 'team',
            name: 'Team',
            component: 'team',
            params: {}
          })
        } else {
          $router.push({ path: '/team' })
        }
      },

      openViews() {
        if ($navigation.isDesktopMode) {
          $storex.ui.showApp({
            tabId: 'views',
            name: 'Views',
            component: 'views',
            params: {}
          })
        } else {
          $router.push({ path: '/views' })
        }
      },

      openProfiles() {
        if ($navigation.isDesktopMode) {
          $storex.ui.showApp({
            tabId: 'profiles',
            name: 'Profiles',
            component: 'profiles',
            params: {}
          })
        } else {
          $router.push({ path: '/profiles' })
        }
      },

      openKnowledge() {
        if ($navigation.isDesktopMode) {
          $storex.ui.showApp({
            tabId: 'knowledge',
            name: 'Knowledge',
            component: 'knowledge',
            params: {}
          })
        } else {
          $router.push({ path: '/knowledge' })
        }
      },

      openAnalytics() {
        if ($navigation.isDesktopMode) {
          $storex.ui.showApp({
            tabId: 'analytics',
            name: 'Analytics',
            component: 'analytics',
            params: {}
          })
        } else {
          $router.push({ path: '/analytics' })
        }
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