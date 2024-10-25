import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

const CODX_JUNIOR_UI_SIZES = [...new Array(12)].map((_, ix) => `w-${ix+1}/12`)

export const state = () => ({
  showApp: null,
  expandCodxJunior: false,
  tabIx: 'home',
  floatingCodxJunior: false,
  codxJuniorWidthIndex: 3,
  isMobile: false,
  orientation: 'portrait'
})

export const getters = getterTree(state, {
  showCoder: state => state.showApp === 'coder',
  showPreview: state => state.showApp === 'preview',
  sideBarMode: state => state.showApp && !state.expandCodxJunior,
  codxJuniorWidth: state => CODX_JUNIOR_UI_SIZES[state.codxJuniorWidthIndex],
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
    if (app) {
      state.expandCodxJunior = false
    }
    $storex.ui.saveState()
  },
  toggleCodxJunior(state) {
    if (state.showApp) {
      state.expandCodxJunior = !state.expandCodxJunior
    } else {
      state.expandCodxJunior = true
    }
    $storex.ui.saveState()
  },
  setActiveTab(state, tabIx) {
    state.tabIx = tabIx
    if (state.tabIx !== 'app') {
      state.showApp = null
    }
  },
  toggleFloating(state) {
    state.floatingCodxJunior = !state.floatingCodxJunior
    if (state.floatingCodxJunior) {
      state.expandCodxJunior = false
    }
    $storex.ui.saveState()
  },
  incrementCodxJuniorWidth(state) {
    state.codxJuniorWidthIndex = Math.min(state.codxJuniorWidthIndex + 1, CODX_JUNIOR_UI_SIZES.length-1)
    $storex.ui.saveState()
  },
  decrementCodxJuniorWidth(state) {
    state.codxJuniorWidthIndex = Math.max(state.codxJuniorWidthIndex - 1, 0)
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