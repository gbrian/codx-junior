import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import { API } from '../api/api'
import moment from 'moment'

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
  viewMode: 'vibe',
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
  views: [],
  lastView: null,
  _desktopApi: null,
  viewEditor: null,
  activeTeam: null,
  teamBarCollapsed: false,
  panelWidths: {
    chat: 30,
    changes: 33,
    preview: 37
  }
})

export const getters = getterTree(state, {
  isLandscape: state => state.orientation !== 'portrait',
  monitorToken: state => state.monitors[state.monitor],
  isSharedScreen: () => window.location.pathname === '/shared',
  enableFileManger: () => API.globalSettings?.enable_file_manager,
  activeApps: () => Object.values($storex.ui.openApps),
  isVibeMode: state => state.viewMode === 'vibe',
  isExpertMode: state => state.viewMode === 'expert',
})

export const mutations = mutationTree(state, {
  setActiveTab(state, tab) {
    tab = tab || 'home'
    if (tab !== 'home') {
      $storex.ui.showApp({
        name: tab,
        component: tab
      })
    } else {
      state.activeTab = null
      state.activeApp = null
    }
    $storex.ui.saveState()
  },
  showTab(state, tab) {
    if (tab !== state.activeTab) {
      $storex.ui.setActiveTab(tab)
    }
    if (!state.isMobile) {
      $storex.ui.showApp({
        name: tab,
        component: tab
      })
    }
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
    $storex.ui.showApp({
      name: 'Logs',
      component: 'log-viewer'
    })
  },
  openChatLogs(state) {
    state.showLogs = !state.showLogs
    $storex.ui.showApp({
      name: 'Chat logs',
      component: 'chat-logs'
    })
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
    $storex.ui.showApp({ ...app, tabId: null })
  },
  showApp(state, app) {
    // Check if panel already exists and activate it
    if (state._desktopApi && app.params?.chat?.id) {
      const existingPanel = state._desktopApi.panels
          .find(({ _params }) => _params?.chat?.id === app.params?.chat?.id
      )
      if (existingPanel) {
        existingPanel.api.setActive()
        state.activeApp = app
        return
      }
    }

    app.tabId = app.tabId || `${app.key || app.name}-${Date.now()}`
    app.params = app.params || {}
    app.openedAt = Date.now()
    if (state.viewMode !== 'vibe') {
      state.openApps = {
        ...state.openApps,
        [app.tabId]: app
      }
    }
    state.activeApp = app
  },
  updateAppParams(state, { tabId, params }) {
    const app = state.openApps[tabId]
    if (!app) return
    state.openApps = {
      ...state.openApps,
      [tabId]: {
        ...app,
        params: {
          ...app.params,
          ...params
        }
      }
    }
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
        $storex.ui.showTab(state.lastActiveTab || 'home')
      }
    }
    $storex.ui.saveState()
  },
  setAppShowMode(state, mode) {
    state.appShowMode = mode
  },
  openChat(_, chat) {
    $storex.ui.showApp({
      name: chat.name,
      component: 'chat',
      params: {
        chat: {
          id: chat.id,
          name: chat.name,
          owner_project_id: chat.owner_project_id
        }
      }
    })
  },
  setDesktopApi(state, api) {
    state._desktopApi = api
  },
  setViews(state, views) {
    state.views = views || []
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
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }, $storex) {
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
      const data = { 
        ...state, 
        uiReady: false,
        openApps: {},
        _desktopApi: null,
        views: [],
        viewEditor: null
      }
      localStorage.setItem('uiState', JSON.stringify(data))
    },
    async loadState({ state }) {
      const savedState = localStorage.getItem('uiState')
      if (savedState) {
        const parsedState = JSON.parse(savedState)
        Object.keys(parsedState)
          .forEach(k => state[k] = parsedState[k])
      }
      const {
        activeProject: project_id,
        activeChat: chatId
      } = state

      if (project_id && project_id !== $storex.projects.activeProject?.project_id) {
        await $storex.projects.setActiveProject({ project_id })
      }
      if (chatId && $storex.projects.activeProject) {
        $storex.projects.setActiveChat({ id: chatId })
      }
      
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

    // ── Team panel openers ────────────────────────────────────────────────────

    openTeamChannel(_, { team, channel }) {
      $storex.ui.showApp({
        key: `team-channel-${channel.id}`,
        name: `# ${channel.name}`,
        component: 'team-channel',
        params: { team, channel }
      })
    },

    async openTeamDM(_, { team, member }) {
      const chatId = await $storex.teams.openDirectMessage({ teamId: team.id, member })
      $storex.ui.showApp({
        key: `team-dm-${team.id}-${member.id}`,
        name: `@ ${member.username}`,
        component: 'team-dm',
        params: { team, member, chatId }
      })
    },

    openTeamMediaLibrary(_, { team }) {
      $storex.ui.showApp({
        key: `team-media-${team.id}`,
        name: `🖼 ${team.name} Media`,
        component: 'team-media-library',
        params: { team }
      })
    },

    // ── QuickBar app openers ──────────────────────────────────────────────────

    openVibeCoding() {
      $storex.ui.showApp({
        key: 'vibe-coding',
        name: 'Vibe Coding',
        component: 'vibe-coding',
        params: {}
      })
    },

    openProjects() {
      $storex.ui.showApp({
        key: 'projects',
        name: 'Projects',
        component: 'projects',
        params: {}
      })
    },

    openTeams() {
      $storex.ui.showApp({
        key: 'teams',
        name: 'Teams',
        component: 'teams',
        params: {}
      })
    },

    openTasks() {
      $storex.ui.setActiveTab('tasks')
    },

    openWiki() {
      $storex.ui.setActiveTab('wiki')
    },

    openMediaLibrary() {
      $storex.ui.showApp({
        key: 'media-library',
        name: 'Media Library',
        component: 'media-library',
        params: {}
      })
    },

    openHome() {
      $storex.ui.setActiveTab('home')
    },

    openTutorial(_, tutorialId) {
      $storex.ui.showApp({
        key: `tutorial-${tutorialId}`,
        name: 'Knowledge',
        component: 'knowledge',
        params: { tutorial: tutorialId }
      })
    },

    // --- Views actions ---

    async loadViews({ state }) {
      try {
        const projectApi = $storex.projects.activeProject?.$api
        if (!projectApi) return
        const views = await projectApi.views.list()
        state.views = views || []
      } catch (ex) {
        console.error("Error loading views", ex)
        state.views = []
      }
    },

    async saveView({ state }, name) {
      const project = $storex.projects.activeProject
      if (!project) return
      const projectApi = project.$api
      if (!projectApi) return
      const desktop = state._desktopApi ? state._desktopApi.toJSON() : {}
      const view = {
        name,
        project_id: project.project_id,
        desktop
      }
      await projectApi.views.save(view)
      await $storex.ui.loadViews()
      $storex.ui.persistLastView({ project_id: project.project_id, view })
      $storex.ui.addNotification({ text: `View "${name}" saved` })
      return view
    },

    resetDesktop({ state }) {
      const api = state._desktopApi
      if (!api) return
      const panelIds = api.panels.map(p => p.id)
      panelIds.forEach(id => {
        try {
          const panel = api.getPanel(id)
          if (panel) api.removePanel(panel)
        } catch (ex) {
          console.warn("Could not remove panel", id, ex)
        }
      })
      state.openApps = {}
    },

    async loadView({ state }, view) {
      if (!state._desktopApi || !view?.desktop) return
      try {
        state._desktopApi.fromJSON(view.desktop)
        state.lastView = view
        const project = $storex.projects.activeProject
        if (project) {
          $storex.ui.persistLastView({ project_id: project.project_id, view })
        }
        $storex.ui.addNotification({ text: `View "${view.name}" loaded` })
      } catch (ex) {
        console.error("Error loading view", ex)
      }
    },

    persistLastView(_, { project_id, view }) {
      try {
        const key = `lastView_${project_id}`
        localStorage.setItem(key, JSON.stringify({ name: view.name }))
      } catch (ex) {
        console.error("Error persisting last view", ex)
      }
    },

    async restoreLastView({ state }) {
      const project = $storex.projects.activeProject
      if (!project) return
      try {
        const key = `lastView_${project.project_id}`
        const stored = localStorage.getItem(key)
        if (!stored) return
        const { name } = JSON.parse(stored)
        const view = state.views.find(v => v.name === name)
        if (view) {
          await $storex.ui.loadView(view)
        }
      } catch (ex) {
        console.error("Error restoring last view", ex)
      }
    },

    async deleteView({ state }, name) {
      const projectApi = $storex.projects.activeProject?.$api
      if (!projectApi) return
      await projectApi.views.delete(name)
      await $storex.ui.loadViews()
      const project = $storex.projects.activeProject
      if (project) {
        const key = `lastView_${project.project_id}`
        const stored = localStorage.getItem(key)
        if (stored) {
          const { name: storedName } = JSON.parse(stored)
          if (storedName === name) {
            localStorage.removeItem(key)
            state.lastView = null
          }
        }
      }
      $storex.ui.addNotification({ text: `View "${name}" deleted` })
    },

    async renameView({ state }, { oldName, newName }) {
      const projectApi = $storex.projects.activeProject?.$api
      if (!projectApi) return
      await projectApi.views.rename(oldName, newName)
      await $storex.ui.loadViews()
      const project = $storex.projects.activeProject
      if (project) {
        const key = `lastView_${project.project_id}`
        const stored = localStorage.getItem(key)
        if (stored) {
          const { name: storedName } = JSON.parse(stored)
          if (storedName === oldName) {
            localStorage.setItem(key, JSON.stringify({ name: newName }))
          }
        }
      }
      $storex.ui.addNotification({ text: `View renamed to "${newName}"` })
    }
  },
)