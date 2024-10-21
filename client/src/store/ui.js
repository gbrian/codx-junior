import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

const getParentStorex = () => window.$parentStorex

export const state = () => ({
  showApp: null,
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
  toggleCoder(state) {
    if (getParentStorex()) {
      getParentStorex().ui.toggleApp('coder')
      state.showApp = getParentStorex().ui.showApp
    } else {
      $storex.toggleApp('coder')
    }
  },
  togglePreview(state) {
    if (getParentStorex()) {
      getParentStorex().ui.toggleApp('preview')
      state.showApp = getParentStorex().ui.showApp
    } else {
      $storex.toggleApp('preview')
    }
  },
  toggleApp(state, app) {
    if (getParentStorex()) {
      getParentStorex().ui.toggleCoder()
      state.showApp = getParentStorex().ui.showApp
    } else {
      state.showApp = state.showApp === app ? null: app
      $storex.ui.saveState()
    }
  },
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
