import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import { API } from '../api/api'
import moment from 'moment'

export const namespaced = true

export const state = () => ({
  showCoder: false,
  showBrowser: false,
  tabIx: 'home',
  codxJuniorWidth: 30,
  isMobile: false,
  orientation: 'portrait',
  openedFile: null,
  kanban: null,
  showLogs: false,
  voiceLanguage: 'en-US',
  voiceLanguages: {
    "en-US": "English",
    "es-SP": "Español"
  },
  appActives: [],
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
    resize: 'scale'
  },
  theme: 'dark'
})

export const getters = getterTree(state, {
  showApp: state => state.showBrowser || state.showCoder,
  isLandscape: state => state.orientation !== 'portrait',
  monitorToken: state => state.monitors[state.monitor],
  isSharedScreen: () => window.location.pathname === '/shared',
  enableFileManger: () => API.globalSettings?.enable_file_manager,
  activeTab: state => state.tabIx
})

export const mutations = mutationTree(state, {
  loadState(state) {
    const savedState = localStorage.getItem('uiState')
    if (savedState) {
      const parsedState = JSON.parse(savedState)
      Object.keys(parsedState)
        .forEach(k => state[k] = parsedState[k])
    }
    $storex.ui.handleResize()
    if (state.isMobile && state.tabIx !== 'app') {
      state.showCoder = false
      state.showBrowser = false
    }
  },
  toggleCoder(state) {
    $storex.ui.setShowCoder(!state.showCoder)
  },
  toggleBrowser(state) {
    $storex.ui.setShowBrowser(!state.showBrowser)
  },
  setActiveTab(state, tabIx) {
    if (state.tabIx === tabIx) {
      if (!$storex.ui.isMobile && $storex.ui.showApp) {
        state.tabIx = null
      }
    } else {
      state.tabIx = tabIx
    }
    if (state.tabIx !== 'app' && state.isMobile) {
      state.showCoder = false
      state.showBrowser = false
    }
    $storex.ui.saveState()
  },
  setShowCoder(state, show) {
    state.showCoder = show
    if (state.showCoder) {
      state.appActives = ['coder', ...state.appActives]
    } else {
      state.appActives = state.appActives.filter(a => a !== 'coder')
    }
    if (state.showCoder && state.isMobile && state.showBrowser) {
      $storex.ui.setShowBrowser(false)
    }
    $storex.ui.saveState()
  },
  setShowBrowser(state, show) {
    state.showBrowser = show
    if (state.showBrowser) {
      state.appActives = ['browser', ...state.appActives]
    } else {
      state.appActives = state.appActives.filter(a => a !== 'browser')
    }
    if (state.showCoder && state.isMobile && state.showBrowser) {
      $storex.ui.setShowCoder(false)
    }
    $storex.ui.saveState()
  },
  setCodxJuniorWidth(state, width) {
    state.codxJuniorWidth = width
    $storex.ui.saveState()
  },
  setKanban(state, kanban) {
    state.kanban = kanban
    $storex.ui.saveState()
  },
  toggleLogs(state) {
    state.showLogs = !state.showLogs
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
    state.uiReady = true
    // If no user projects, go to help
    if (!state.tabIx || !$storex.projects.allProjects?.find(p => p.project_path.indexOf("codx-junior") === -1)) {
      $storex.ui.setActiveTab('help')
    }
  },
  setFloatinCodxJunior(state, floating) {
    state.floatingCodxJunior = floating
    $storex.ui.saveState()
  },
  addNotification(state, { text, type }) {
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
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }, $storex) {
      $storex.ui.loadState()
      $storex.ui.handleResize()
      window.addEventListener('resize', () => $storex.ui.handleResize())
      if (!state.tabIx) {
        state.tabIx = 'home'
      }
    },
    saveState({ state }) {
      const data = { ...state, uiReady: false }
      localStorage.setItem('uiState', JSON.stringify(data))
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
      $storex.ui.setActiveTab('tasks')
      $storex.projects.setActiveChat(task)
    },
    async openFile({ state }, file) {
      if (state.isMobile) {
        state.tabIx = 'help'
        state.openedFile = file
      } else {
        await API.coder.openFile(file)
      }
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
    }
  },
)