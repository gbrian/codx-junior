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
    workspace: {
      list: () => ({ name: 'workspaces' }),
      open: (workspaceId, workspaceName) => ({
        name: 'workspace',
        params: { workspaceId, workspaceName }
      })
    },
    kanban: {
      open: () => ({ name: 'kanban' })
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

    get isWorkspaceView() {
      const name = $router.currentRoute.value.name
      return name === 'workspace' || name === 'workspaces'
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

    getWorkspaceId() {
      return $router.currentRoute.value.params.workspaceId || null
    },

    getWorkspaceName() {
      return $router.currentRoute.value.params.workspaceName || null
    },

    get hasChatContext() {
      return this.getChatId() !== null
    },

    get hasWorkspaceContext() {
      return this.getWorkspaceId() !== null
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

      openKanban() {
        if ($navigation.isDesktopMode) {
          $storex.ui.showTab('tasks')
        } else {
          $router.push(routes.kanban.open())
        }
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
    }
  }

  return $navigation
}