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
  appShowMode: null
})

export const getters = getterTree(state, {
  isLandscape: state => state.orientation !== 'portrait',
  monitorToken: state => state.monitors[state.monitor],
  isSharedScreen: () => window.location.pathname === '/shared',
  enableFileManger: () => API.globalSettings?.enable_file_manager,
  activeApps: () => Object.values($storex.ui.openApps)
})

export const mutations = mutationTree(state, {
  setActiveTab(state, tab) {
    tab = tab || 'home'
    if (state.activeTab === tab) {
      if (state.activeApp) {
        state.activeTab = null
      }
    } else {
      state.activeTab = tab
    }
    $storex.ui.showApp({
      name: tab,
      component: tab
    })
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
  setVoiceLanguage(state, voiceLanguage) {
    state.voiceLanguage = voiceLanguage
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
      existing.ts = moment().format("hh:mm:ss")
      return
    }
    const notif = {
      ts: moment().format("hh:mm:ss"),
      text,
      type
    }
    state.notifications.push(notif)
    setTimeout(() => $storex.ui.removeNotification(notif) , 30000)
  },
  removeNotification(state, notification) {
    state.notifications.splice(
      state.notifications.findIndex(n => n === notification), 1)
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
    app.tabId = app.tabId || `${app.key || app.name}-${(new Date().getTime())}`
    app.params = app.params || {}
    state.openApps = {
      ...state.openApps,
      [app.tabId]: app
    }
  },
  closeApp(state, app) {
    delete state.openApps[app.tabId]
    if (state.activeApp?.tabId === app.tabId) {
      state.activeApp = state.openApps[Object.keys(state.openApps).reverse()[0]]
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
  openChat(state, chat) {
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
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }, $storex) {
      $storex.ui.handleResize()
      window.addEventListener('resize', () => $storex.ui.handleResize())
      state.activeApp = "home"
      if (API.user?.theme) {
        state.theme = API.user.theme
      }
      state.coderProjectCodxPath = null
    },
    saveState({ state }) {
      if (!state.uiReady) {
        // Ignore this calls as they can come from initialization
        return
      }
      const data = { 
        ...state, 
        uiReady: false,
        activeApp: null,
        openApps: Object.keys(state.openApps),
        activeProject: $storex.projects.activeProject?.project_id,
        activeChat:  $storex.projects.activeChat?.id,
        openApps: {} // Stored in layouts
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
      state.activeApp = Object.values(state.openApps)[0]
      
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
      state.resolution = API.screen.display?.resolution,
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
        const blob = await item.getType(itemType);
        return await blob.text();
      }
      const allTexts = await Promise.all(
                        items.filter(i => i.types.includes(itemType))
                              .map(i => getText(i)))
      return allTexts.reduce((a, b) => a + b, "")
    },
    async shareScreen() {
      // Note: This requires a user gesture (like a button click)
      const stream = await navigator.mediaDevices.getDisplayMedia({
        preferCurrentTab: true,
      });
      // Crop the stream to a specific element using CropTarget (if supported)
      const [track] = stream.getVideoTracks();
      // const cropTarget = await CropTarget.fromElement(document.querySelector(`.app-${encodeURIComponent(app.name)}`));
      // await track.cropTo(cropTarget);
      // this.videoThumb = track;
    },
    openNewWindowAppPanel(_, app) {
      const { origin } = window.location
      const url = `${origin}${app.path}`
      window.open(url, app.name)
    }
  },
)