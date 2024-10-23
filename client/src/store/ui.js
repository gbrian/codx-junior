import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

export const state = () => ({
  showApp: null,
  expandCodxJunior: false
})

export const getters = getterTree(state, {
  showCoder: state => state.showApp === 'coder',
  showPreview: state => state.showApp === 'preview'
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
