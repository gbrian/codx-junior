import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

export const state = () => ({
  showCoder: false,
  showPreview: false
})

export const mutations = mutationTree(state, {
  toggleCoder(state) {
    state.showCoder = !state.showCoder
    if (state.showCoder && state.showPreview) {
      state.showPreview = false
    }
    $storex.ui.saveState()
  },
  togglePreview(state) {
    state.showPreview = !state.showPreview
    if (state.showCoder && state.showPreview) {
      state.showCoder = false
    }
    $storex.ui.saveState()
  },
  loadState(state) {
    const savedState = localStorage.getItem('uiState')
    if (savedState) {
      const parsedState = JSON.parse(savedState)
      state.showCoder = parsedState.showCoder
      state.showPreview = parsedState.showPreview
    }
  }
})

export const getters = getterTree(state, {
  splitView: () => $storex.ui.showCoder || $storex.ui.showPreview
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init () {
      $storex.ui.loadState()
    },
    saveState({ state }) {
      localStorage.setItem('uiState', JSON.stringify(state))
    }
  },
)
