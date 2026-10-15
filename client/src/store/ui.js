import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import { API } from '../api/api'
import moment from 'moment'
import { APPS, isMultiInstance } from '../config/apps'

export const namespaced = true

export const state = () => ({
  showCoder: false,
  showBrowser: false,
  lastActiveTab: "",
  codxJuniorWidth: 30,
  isMobile: false,
  orientation: 'portrait',
  openedFile: null,
  showLogs: false,
  voiceLanguage: 'en-US',
  voiceLanguages: {
    "en-US": "English",
    "es-SP": "Español"
  },
  viewMode: 'expert',
  openApps: {},
  appDivided: 'horizontal',
  resolution: API.screen.display?.resolution,
  resolutions: API.screen.display?.resolutions,
  monitor: "preview",
  monitors: {
    "preview": "CODX-SCREEN-PREVIEW",
    "shared": "CODX-SCREEN-SHARED"
  },
  colorsMap: {},
  coderProjectCodxPath: null,
  uiReady: false,
  floatingCodxJunior: false,
  notifications: [],
  noVNCSettings: {
    resize: 'remote',
  },
  theme: 'dark',
  activeTab: 'home',
  newProject: false,
  activeApp: null,
  appShowMode: null,
  viewEditor: null,
  activeTeam: null,
  teamBarCollapsed: false,
  panelWidths: {
    chat: 30,
    changes: 33,
    preview: 37
  },
  sidebarCollapsed: false,
  // Projects pinned by the user for quick switching. Persisted in localStorage
  // through the uiState snapshot (saveState/loadState), so it survives reloads.
  pinnedProjects: [],
  projectLoadingState: {
    isLoading: false,
    projectName: '',
    currentStep: null,
    error: null
  },
  // Call device preferences
  callDevicePreferences: {
    microphone: 'default',
    speaker: 'default',
    autoMute: false
  },
  // Active call panel on chat
  activeChatCallPanelWidth: 30
})

export const getters = getterTree(state, {
  isLandscape: state => state.orientation !== 'portrait',
  monitorToken: state => state.monitors[state.monitor],
  isSharedScreen: () => window.location.pathname === '/shared',
  enableFileManger: () => API.globalSettings?.enable_file_manager,
  activeApps: () => Object.values($storex.ui.openApps),
  isVibeMode: state => state.viewMode === 'vibe',
  isExpertMode: state => state.viewMode === 'expert',
  isDesktopMode: () => $storex.$router.currentRoute.value.name === 'codx-junior-split',
  // Pinned projects resolved to full project objects (keeps only pins that still exist)
  pinnedProjectsList: state => (state.pinnedProjects || [])
    .map(id => $storex.projects.allProjectsById?.[id] ||
                $storex.projects.allProjects?.find(p => p.project_id === id))
    .filter(Boolean),
  // Whether the currently active project is pinned
  isActiveProjectPinned: state => {
    const projectId = $storex.projects.activeProject?.project_id
    return !!projectId && (state.pinnedProjects || []).includes(projectId)
  },
  // Whether the sidebar is expanded (desktop icon rail / mobile overlay).
  // `sidebarCollapsed` is the single, persisted source of truth shared by
  // App.vue (mobile overlay) and DesktopSidebar.vue (desktop rail).
  isSidebarExpanded: state => !state.sidebarCollapsed,
})

// ══════════════════════════════════════════════════════════════════════════
// APP PARAMS PERSISTENCE
//
// An open app may update its own params at runtime (the project it points at,
// the last file/URL an embedded app was browsing, the active board, …). Those
// params live in two places:
//
//   • the store app object (`state.openApps[tabId].params`), which components
//     read through the `$app` mixin, and
//   • the hosting dockview panel params, which are what gets serialized into
//     the saved layout (dockview's `toJSON()` returns `panel.params` by
//     reference, so mutating that object updates both the live panel and the
//     serialized layout).
//
// Applying an update to both keeps the UI in sync, and persisting the layout
// afterwards is what makes the change survive a reload. Without it the panel
// would be restored with the params captured when it was first opened.
// ══════════════════════════════════════════════════════════════════════════
function applyAppParams(app, params, panel = null) {
  if (!app || !params) return

  // Skip no-op updates so we don't persist the layout for nothing
  const changed = Object.keys(params).some(key => app.params?.[key] !== params[key])
  if (!changed) return

  // Merge into the *same* app object instead of replacing it: dockview panels
  // keep a reference to it (`panel.params.app`), so replacing the object would
  // leave the panel — and the layout that gets persisted — with a stale
  // snapshot (e.g. the active board would be lost on reload).
  app.params = { ...(app.params || {}), ...params }

  // Keep the hosting dockview panel params in sync too. They are the values
  // serialized into the saved layout, so a reload restores the last params
  // instead of the ones captured when the panel was first opened.
  const targetPanel = panel || $storex.views._desktopApi?.getPanel?.(app.tabId)
  const panelParams = targetPanel?.params || targetPanel?.api?.params
  if (panelParams) {
    Object.assign(panelParams, params)
  }

  // Save the view so the change is kept for next time.
  $storex.views.onLayoutChanged()
}

// Resolve the app registry definition for an app object. Apps are looked up by
// their registry id first, then by the plain `key` (e.g. "tasks", "planning"),
// and only then by the shared component — which is how derived, per-instance
// keys such as "tasks-<board>" or "chat-<id>" find their definition.
function appDefinition(app) {
  if (!app) return null
  return APPS[app.id] ||
    APPS[app.key] ||
    Object.values(APPS).find(def => def.component === app.component) ||
    null
}

// Identity used to decide whether two app objects refer to the SAME open panel.
//
//   • Single-instance apps → their `key` (one app = one panel).
//   • Multi-instance apps → the per-instance key the registry derives from the
//     params (e.g. Task Manager → "tasks-<board>", one panel per board).
//
// Using the registry's per-instance key instead of the stored `key` is what
// keeps several panels of the same app apart: duplicated Task Manager panels
// all carry `key: 'tasks'` (only the board differs in their params), so
// matching on `key` collapsed every board but one on reload.
function appInstanceKey(app) {
  if (!app) return null
  const def = appDefinition(app)
  if (def?.multiInstance && typeof def.desktopKey === 'function') {
    return def.desktopKey(app.params || {}) || app.key
  }
  return app.key
}

export const mutations = mutationTree(state, {
  setActiveTab(state, tab) {
    tab = tab || 'home'

    // Home is not an app: it clears the active app on desktop and is just a
    // route on mobile.
    if (tab === 'home') {
      state.activeTab = null
      state.activeApp = null
      if (state.isMobile) {
        $storex.ui.openApp('home')
      }
      $storex.ui.saveState()
      return
    }

    // Unified opener: every other tab goes through openApp so the same key
    // works on both modes (dockview panel on desktop, route on mobile),
    // including aliased apps such as 'planning' → tasks panel w/ planning view.
    state.activeTab = tab
    $storex.ui.openApp(tab)
    $storex.ui.saveState()
  },
  showTab(state, tab) {
    // setActiveTab now resolves the correct panel/route for any mode.
    $storex.ui.setActiveTab(tab)
  },
  closeTab(state) {
    state.activeTab = null
  },
  setCodxJuniorWidth(state, width) {
    state.codxJuniorWidth = width
    $storex.ui.saveState()
  },
  toggleLogs(state) {
    state.showLogs = !state.showLogs
    $storex.ui.openApp('log-viewer')
  },
  openChatLogs(state) {
    state.showLogs = !state.showLogs
    $storex.ui.openApp('chat-logs')
  },
  setVoiceLanguage(state, voiceLanguage) {
    state.voiceLanguage = voiceLanguage
    $storex.ui.saveState()
  },
  setVibeMode(state) {
    state.viewMode = 'vibe'
    $storex.ui.saveState()
  },
  setExpertMode(state) {
    state.viewMode = 'expert'
    $storex.ui.saveState()
  },
  setViewMode(state, mode) {
    state.viewMode = mode
    $storex.ui.saveState()
  },
  setAppDivided(state, divided) {
    state.appDivided = divided
    $storex.ui.saveState()
  },
  setMonitor(state, monitor) {
    state.monitor = monitor
    $storex.ui.saveState()
  },
  setColorsMap(state, colorsMap) {
    state.colorsMap = colorsMap
    $storex.ui.saveState()
  },
  coderOpenPath(state, project) {
    state.coderProjectCodxPath = project.codx_path
  },
  setUIready(state) {
    $storex.ui.loadState()
    state.uiReady = true
  },
  setFloatinCodxJunior(state, floating) {
    state.floatingCodxJunior = floating
    $storex.ui.saveState()
  },
  toggleFloatinCodxJunior(state) {
    state.floatingCodxJunior = !state.floatingCodxJunior
    $storex.ui.saveState()
  },
  addNotification(state, { text, type }) {
    const existing = state.notifications?.find(n => n.text === text)
    if (existing) {
      existing.ts = moment().format("HH:mm:ss")
      return
    }
    const notif = {
      ts: moment().format("HH:mm:ss"),
      text,
      type: type || 'info'
    }
    state.notifications.push(notif)
    setTimeout(() => $storex.ui.removeNotification(notif), 30000)
  },
  removeNotification(state, notification) {
    state.notifications.splice(
      state.notifications.findIndex(n => n === notification), 1)
  },
  clearNotifications(state, notifications) {
    state.notifications = state.notifications.filter(n => !notifications.includes(n))
  },
  setNoVNCSettings(state, settings) {
    state.noVNCSettings = { ...state.noVNCSettings, ...settings }
  },
  setTheme(state, theme) {
    state.theme = theme
  },
  showNewProject(state, show) {
    state.newProject = show
  },
  cloneApp(state, app) {
    // "Duplicate" only makes sense for apps declared as multi-instance in
    // config/apps.js (e.g. the Task Manager, one panel per board). For every
    // other app we just focus the panel that is already open — showApp
    // de-duplicates by `key` — so the menu item never spawns a second,
    // indistinguishable panel.
    if (!isMultiInstance(app)) {
      $storex.ui.showApp({ ...app })
      return
    }
    // `newInstance` tells showApp to skip its "same key is already open"
    // de-duplication, so a brand-new panel is created for this instance.
    $storex.ui.showApp({ ...app, tabId: null, newInstance: true })
  },
  resetOpenApps(state) {
    state.openApps = {}
    state.activeApp = null
  },
  showApp(state, app) {
    // A duplicate/clone explicitly asks for a new instance. Consume the flag
    // here so it is neither stored on the app object nor persisted in the saved
    // layout.
    const forceNewInstance = app.newInstance === true
    delete app.newInstance

    app.tabId = app.tabId || `${app.key || app.name}-${Date.now()}`
    app.params = app.params || {}
    // Auto-inject project_id if not present
    if (!app.params.project_id && $storex.projects.activeProject?.project_id) {
      app.params.project_id = $storex.projects.activeProject.project_id
    }
    app.initialParams = app.initialParams || JSON.parse(JSON.stringify(app.params))
    app.openedAt = Date.now()

    // De-duplication focuses an already-open instance of the SAME app.
    //
    // For single-instance apps the identity is `key`. For multi-instance apps
    // (e.g. the Task Manager, one panel per board) the identity is the
    // per-instance key derived from the params — matching on `key` alone
    // collapsed every board but one when a layout holding several Task Manager
    // panels was restored (syncAppsFromLayout passes each restored panel
    // through here).
    const multiInstance = !!appDefinition(app)?.multiInstance

    if (!forceNewInstance && state.viewMode !== 'vibe' && !state.isMobile) {
      const instanceKey = appInstanceKey(app)

      // Check if the same app instance already exists in openApps state
      const existingApp = Object.values(state.openApps).find(openApp => {
        const existingInstanceKey = appInstanceKey(openApp)
        if (instanceKey && existingInstanceKey) {
          return existingInstanceKey === instanceKey
        }
        return openApp.component === app.component &&
              JSON.stringify(openApp.initialParams) === JSON.stringify(app.initialParams)
      })

      if (existingApp) {
        // The app is already open: keep the params it just received (and save
        // them) instead of discarding them.
        applyAppParams(existingApp, app.params)
        state.activeApp = existingApp
        $storex.views.activatePanel(existingApp.tabId)
        return
      }

      // Check if panel already exists in Desktop API by checking component and initialParams.
      // Only meaningful for single-instance apps: a multi-instance app legitimately owns
      // several panels, so we must never collapse them here.
      const desktopApi = $storex.views._desktopApi
      if (!multiInstance && desktopApi && desktopApi.panels) {
        const existingPanel = desktopApi.panels.find(panel => {
          if (app.key && panel.key) {
            return panel.key === app.key
          }
          const panelParams = panel.params?.params || panel.params || {}
          return panel.component === app.component &&
                JSON.stringify(panelParams.initialParams || panelParams) === JSON.stringify(app.initialParams)
        })

        if (existingPanel) {
          // The panel may belong to an app the store tracks (panels keep a
          // reference at `panel.params.app`): apply & save the new params.
          applyAppParams(existingPanel.params?.app, app.params, existingPanel)
          state.activeApp = app
          $storex.views.activatePanel(existingPanel.id)
          return
        }
      }
    }

    state.openApps = {
      ...state.openApps,
      [app.tabId]: app
    }
    state.activeApp = app
  },
  updateAppParams(state, { tabId, params }) {
    // The app owns the params; the helper keeps the dockview panel (i.e. the
    // saved layout) in sync and persists the view.
    applyAppParams(state.openApps[tabId], params)
  },
  closeApp(state, app) {
    if (!app) return
    delete state.openApps[app.tabId]
    if (state.activeApp?.tabId === app.tabId) {
      const remainingApps = Object.values(state.openApps)
      if (remainingApps.length > 0) {
        state.activeApp = remainingApps.reduce((latest, current) =>
          current.openedAt > latest.openedAt ? current : latest
        )
      } else {
        state.activeApp = null
      }
    }
    if (!Object.keys(state.openApps).length) {
      if (!state.activeTab) {
        $storex.ui.showTab(state.lastActiveTab || 'tasks')
      }
    }
    $storex.ui.saveState()
  },
  setAppShowMode(state, mode) {
    state.appShowMode = mode
  },
  setSidebarCollapsed(state, collapsed) {
    state.sidebarCollapsed = collapsed
    $storex.ui.saveState()
  },
  // ── Sidebar collapse controls ────────────────────────────────────────────
  // Clicking the arrow on DesktopSidebar.vue flips these; App.vue drives the
  // mobile overlay with them too. They all funnel through the persisted
  // `sidebarCollapsed` flag (via setSidebarCollapsed) so the shell and the
  // sidebar share a single source of truth.
  expandSidebar() {
    $storex.ui.setSidebarCollapsed(false)
  },
  collapseSidebar() {
    $storex.ui.setSidebarCollapsed(true)
  },
  toggleSidebar(state) {
    $storex.ui.setSidebarCollapsed(!state.sidebarCollapsed)
  },
  // ════════════════════════════════════════════════════════════════
  // PINNED PROJECTS (quick project switcher)
  // ════════════════════════════════════════════════════════════════
  setPinnedProjects(state, projectIds) {
    state.pinnedProjects = Array.isArray(projectIds) ? projectIds : []
    $storex.ui.saveState()
  },
  pinProject(state, projectId) {
    if (!projectId || (state.pinnedProjects || []).includes(projectId)) return
    state.pinnedProjects = [...(state.pinnedProjects || []), projectId]
    $storex.ui.saveState()
  },
  unpinProject(state, projectId) {
    state.pinnedProjects = (state.pinnedProjects || []).filter(id => id !== projectId)
    $storex.ui.saveState()
  },
  togglePinProject(state, projectId) {
    if (!projectId) return
    if ((state.pinnedProjects || []).includes(projectId)) {
      state.pinnedProjects = state.pinnedProjects.filter(id => id !== projectId)
    } else {
      state.pinnedProjects = [...(state.pinnedProjects || []), projectId]
    }
    $storex.ui.saveState()
  },
  openChat(_, chat) {
    if (!chat?.id) return
    // Mark the chat active BEFORE opening it, so the panel/route that opens
    // shows THIS chat (e.g. when navigating here from an activity card).
    // `setActiveChatId` is a plain mutation, so it never re-enters openChat —
    // only the `chats.setActiveChat` action calls back into this helper.
    $storex.chats.setActiveChatId(chat.id)
    // Unified: panel on desktop, route on mobile
    $storex.ui.openApp({ appKey: 'chat', payload: { chat } })
  },
  openFileInViewer(_, filePath) {
    $storex.ui.openApp({ appKey: 'file-viewer', payload: { filePath } })
  },
  openViewEditor(state, view = null) {
    state.viewEditor = { view: view || null }
  },
  closeViewEditor(state) {
    state.viewEditor = null
  },
  setActiveTeam(state, team) {
    state.activeTeam = team
    $storex.ui.saveState()
  },
  setTeamBarCollapsed(state, collapsed) {
    state.teamBarCollapsed = collapsed
    $storex.ui.saveState()
  },
  setPanelWidth(state, { panel, width }) {
    state.panelWidths = {
      ...state.panelWidths,
      [panel]: width
    }
    $storex.ui.saveState()
  },
  setProjectLoadingState(state, loadingState) {
    state.projectLoadingState = {
      ...state.projectLoadingState,
      ...loadingState
    }
  },
  setCallDevicePreferences(state, preferences) {
    state.callDevicePreferences = { ...state.callDevicePreferences, ...preferences }
    $storex.ui.saveState()
  },
  setActiveChatCallPanelWidth(state, width) {
    state.activeChatCallPanelWidth = width
    $storex.ui.saveState()
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }) {
      $storex.ui.handleResize()
      window.addEventListener('resize', () => $storex.ui.handleResize())
      if (API.user?.theme) {
        state.theme = API.user.theme
      }
      state.coderProjectCodxPath = null
    },
    saveState({ state }) {
      if (!state.uiReady) {
        return
      }
      try {
        const data = {
          ...state,
          uiReady: false,
          openApps: {},
          viewEditor: null,
          projectLoadingState: {
            isLoading: false,
            projectName: '',
            currentStep: null,
            error: null
          }
        }
        localStorage.setItem('uiState', JSON.stringify(data))
      } catch (error) {
        console.error('Failed to save UI state:', error)
      }
    },
    async loadState({ state }) {
      try {
        const savedState = localStorage.getItem('uiState')
        if (savedState) {
          const parsedState = JSON.parse(savedState)
          Object.keys(parsedState)
            .forEach(k => state[k] = parsedState[k])
        }
      } catch (error) {
        console.error('Failed to parse saved UI state:', error)
      }
      $storex.ui.showNewProject(false)
      $storex.ui.handleResize()
    },
    handleResize({ state }) {
      const width = window.innerWidth
      const height = window.innerHeight
      const isMobile = width <= 1024
      const orientation = width > height ? 'landscape' : 'portrait'
      state.isMobile = isMobile
      state.orientation = orientation
    },
    loadTask (_, task) {
      $storex.projects.setActiveChat(task)
    },

    // ════════════════════════════════════════════════════════════════
    // UNIFIED APP OPENER
    // ════════════════════════════════════════════════════════════════

    openApp(_, payload) {
      // Vuex passes the action context as the first argument, so the real
      // payload arrives here (second). Accept either a bare app key ("wiki")
      // or an object ({ appKey, payload }) so call sites stay terse.
      const appKey = typeof payload === 'string' ? payload : payload?.appKey
      const data = typeof payload === 'string' ? {} : (payload?.payload || {})

      if (!appKey) {
        console.warn('[UI] openApp: missing app key', payload)
        return
      }

      const navigation = $storex.$navigation
      if (!navigation || typeof navigation.openApp !== 'function') {
        console.warn('[UI] openApp: navigation not ready for', appKey)
        return
      }
      return navigation.openApp(appKey, data)
    },

    async openFile({ state }, file) {
      if (state.isMobile) {
        state.openedFile = file
      } else {
        await API.coder.openFile(file)
      }
      state.showCoder = true
    },
    async openProjectFile({ state }, file) {
      const { project_path } = $storex.projects.activeProject
      if (!file.startsWith(project_path)) {
        if (!file.startsWith("/") && !project_path.endsWith("/")) {
          file = "/" + file
        }
        file = project_path + file
      }
      await API.coder.openFile(file)
      state.showCoder = true
    },
    setScreenResolution(_, resolution) {
      API.screen.setScreenResolution(resolution)
    },
    async readScreenResolutions ({ state }) {
      await API.screen.getScreenResolution()
      state.resolution = API.screen.display?.resolution
      state.resolutions = API.screen.display?.resolutions
    },
    copyTextToClipboard(_, text) {
      const textArea = document.createElement('textarea')
      textArea.value = text
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      $storex.ui.addNotification({ text: "Text copied" })
    },
    async readClipboardText(_, itemType = "text/plain") {
      const items = await navigator.clipboard.read()
      const getText = async item => {
        const blob = await item.getType(itemType)
        return await blob.text()
      }
      const allTexts = await Promise.all(
                        items.filter(i => i.types.includes(itemType))
                              .map(i => getText(i)))
      return allTexts.reduce((a, b) => a + b, "")
    },
    async shareScreen() {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        preferCurrentTab: true,
      })
      const [track] = stream.getVideoTracks()
    },
    openNewWindowAppPanel(_, app) {
      const { origin } = window.location
      const url = `${origin}${app.path}`
      window.open(url, app.name)
    },

    openTeamChannel(_, { team, channel }) {
      $storex.ui.openApp({ appKey: 'team-channel', payload: { team, channel } })
    },

    async openTeamDM(_, { team, member }) {
      const chatId = await $storex.teams.openDirectMessage({ teamId: team.id, member })
      $storex.ui.openApp({ appKey: 'team-dm', payload: { team, member, chatId } })
    },

    openTeamMediaLibrary(_, { team }) {
      $storex.ui.openApp({ appKey: 'team-media-library', payload: { team } })
    },

    openVibeCoding() {
      $storex.ui.openApp('vibe-coding')
    },

    openProjects() {
      $storex.ui.openApp('projects')
    },

    // Open the Git view (repository changes / history).
    openGitView() {
      $storex.ui.openApp('git-view')
    },

    // Open the Team screen. Pass an optional team id to focus a specific team
    // ("/:projectName/team/:teamId"); without it the Team view opens with every
    // team visible. Routed through the unified openApp() so the same call works
    // as a dockview panel on desktop and as a route in single/mobile mode.
    openTeams(_, teamId) {
      $storex.ui.openApp({ appKey: 'team', payload: teamId ? { teamId } : {} })
    },

    openWorkspaces() {
      $storex.ui.openApp('workspaces')
    },

    openWorkspace(_, workspace) {
      if (!workspace || !workspace.key) {
        console.warn('[UI] openWorkspace: invalid workspace', workspace)
        return
      }
      // Forward the whole workspace under the `workspace` key so the app's
      // desktopParams can lift name/path into the panel params.
      $storex.ui.openApp({ appKey: 'workspace', payload: { workspace } })
    },

    openMeet(_, meetId) {
      $storex.ui.openApp({ appKey: 'meet', payload: { meetId } })
    },

    openTasks() {
      $storex.ui.setActiveTab('tasks')
    },

    // Open the Task Manager directly on the Planning view.
    openPlanning() {
      $storex.ui.openApp('planning')
    },

    openWiki() {
      $storex.ui.setActiveTab('wiki')
    },

    openMediaLibrary() {
      $storex.ui.showApp({
        tgabId: 'media-library',
        name: 'Media Library',
        compotabIdnent: 'media-library',
        params: {}
      })
    },

    openHome() {
      $storex.ui.setActiveTab('home')
    },

    openTutorial(_, tutorialId) {
      $storex.ui.openApp({ appKey: 'knowledge', payload: { params: { tutorial: tutorialId } } })
    },

    setProjectLoading(_, isLoading) {
      $storex.ui.setProjectLoadingState({ isLoading })
    },

    updateProjectLoadingStep(_, { stepId, status, options = {} }) {
      window.dispatchEvent(new CustomEvent('project-loading-step', {
        detail: { stepId, status, options }
      }))
    },

    setProjectLoadingError(_, error) {
      $storex.ui.setProjectLoadingState({ error })
    },

    /**
     * Update call device preferences and persist to localStorage
     */
    updateCallDevicePreferences({ commit }, preferences) {
      commit('setCallDevicePreferences', preferences)
    },

    /**
     * Get saved call device preferences
     */
    getCallDevicePreferences({ state }) {
      return state.callDevicePreferences
    },

    /**
     * Set active call panel width
     */
    setActiveChatCallPanelWidth({ commit }, width) {
      commit('setActiveChatCallPanelWidth', width)
    }
  },
)