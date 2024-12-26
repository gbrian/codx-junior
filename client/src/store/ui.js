import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import { API } from '../api/api'

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
  appDivided: 'none',
  resolution: API.screen.display?.resolution,
  resolutions: API.screen.display?.resolutions,
  monitor: "preview",
  monitors: {
    "preview": "CODX-SCREEN-PREVIEW",
    "shared": "CODX-SCREEN-SHARED"
  },
  colorsMap: {},
  coderPath: null
})

export const getters = getterTree(state, {
  showApp: state => state.showBrowser || state.showCoder,
  isLandscape: state => state.orientation !== 'portrait',
  monitorToken: state => state.monitors[state.monitor],
  isSharedScreen: () => window.location.pathname === '/shared'
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
    state.tabIx = tabIx
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
    $storex.ui.saveState()
  },
  setShowBrowser(state, show) {
    state.showBrowser = show
    if (state.showBrowser) {
      state.appActives = ['browser', ...state.appActives]
    } else {
      state.appActives = state.appActives.filter(a => a !== 'browser')
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
  coderOpenPath(state, path) {
    state.coderPath = path
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
      state.showLogs = false    
    },
    saveState({ state }) {
      localStorage.setItem('uiState', JSON.stringify(state))
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
      $storex.projects.loadChat(task)
    },
    async openFile({ state }, file) {
      if (state.isMobile) {
        state.tabIx = 'app'
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
    }
  },
)