import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

const CODX_JUNIOR_UI_SIZES = ['w-1/6','w-2/6','w-3/6','w-4/6','w-5/6']

export const state = () => ({
  showApp: null,
  expandCodxJunior: false,
  tabIx: null,
  floatingCodxJunior: false,
  codxJuniorWidthIndex: 3
})

export const getters = getterTree(state, {
  showCoder: state => state.showApp === 'coder',
  showPreview: state => state.showApp === 'preview',
  sideBarMode: state => state.showApp && !state.expandCodxJunior,
  codxJuniorWidth: state => CODX_JUNIOR_UI_SIZES[state.codxJuniorWidthIndex]
})

export const mutations = mutationTree(state, {
  loadState(state) {
    const savedState = localStorage.getItem('uiState')
    if (savedState) {
      const parsedState = JSON.parse(savedState)
      Object.keys(parsedState).forEach(k => state[k] = parsedState[k])
    }
  },
  toggleCoder() {
    $storex.ui.toggleApp('coder')
  },
  togglePreview() {
    $storex.ui.toggleApp('preview')
  },
  toggleApp(state, app) {
    state.showApp = state.showApp === app ? null: app
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
    if (state.showApp && !state.expandCodxJunior) {
      state.expandCodxJunior = true
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
  }
  ,
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
    },
    saveState({ state }) {
      localStorage.setItem('uiState', JSON.stringify(state))
    }
  },
)
