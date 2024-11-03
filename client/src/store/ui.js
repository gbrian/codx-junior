import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

export const state = () => ({
  showCoder: false,
  showBrowser: false,
  tabIx: 'home',
  codxJuniorWidth: 30,
  isMobile: false,
  orientation: 'portrait'
})

export const getters = getterTree(state, {
  showApp: state => state.showBrowser || state.showCoder,
  isLandscape: state => state.orientation !== 'portrait'
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
    state.showCoder = !state.showCoder
    $storex.ui.saveState()
  },
  toggleBrowser(state) {
    state.showBrowser = !state.showBrowser
    $storex.ui.saveState()
  },
  setActiveTab(state, tabIx) {
    state.tabIx = tabIx
    if (state.tabIx !== 'app' && state.isMobile) {
      state.showCoder = false
      state.showBrowser = false
    }
  },
  setShowCoder(state, show) {
    state.showCoder = show
    if (show && state.showBrowser && state.isMobile) {
      state.showBrowser = false
    }
    $storex.ui.saveState()
  },
  setShowBrowser(state, show) {
    state.showBrowser = show
    if (show && state.showCoder && state.isMobile) {
      state.showCoder = false
    }
    $storex.ui.saveState()
  },
  setCodxJuniorWidth(state, width) {
    state.codxJuniorWidth = width
    $storex.ui.saveState()
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
    }
  },
)