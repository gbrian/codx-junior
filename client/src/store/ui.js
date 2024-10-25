import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

export const state = () => ({
  showApp: null,
  tabIx: 'home',
  codxJuniorWidth: 30,
  isMobile: false,
  orientation: 'portrait'
})

export const getters = getterTree(state, {
  showCoder: state => state.showApp === 'coder',
  showPreview: state => state.showApp === 'preview',
  isSplitView: state => !!state.showApp,
  isLandscape: state => state.orientation !== 'portrait'
})

export const mutations = mutationTree(state, {
  loadState(state) {
    const savedState = localStorage.getItem('uiState')
    if (savedState) {
      const parsedState = JSON.parse(savedState)
      Object.keys(parsedState).forEach(k => state[k] = parsedState[k])
    }
  },
  toggleApp(state, app) {
    $storex.ui.setActiveApp(state.showApp === app ? null : app)
  },
  setActiveApp(state, app) {
    state.showApp = app
    $storex.ui.saveState()
  },
  setActiveTab(state, tabIx) {
    state.tabIx = tabIx
    if (state.tabIx !== 'app' && state.isMobile) {
      state.showApp = null
    }
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
      state.tabIx = 'home'
      state.showApp = null
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
      $storex.projects.loadChat(task.name)
    }
  },
)