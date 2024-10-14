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
    this.commit('save_state')
  },
  togglePreview(state) {
    state.showPreview = !state.showPreview
    if (state.showCoder && state.showPreview) {
      state.showCoder = false
    }
    this.commit('save_state')
  },
  save_state(state) {
    localStorage.setItem('uiState', JSON.stringify(state))
  }
})

export const getters = getterTree(state, {
  spliView: () => $storex.ui.showCoder || $storex.ui.showPreview
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state, commit }) {
      commit('load_state')
    },
    load_state({ state }) {
      const savedState = localStorage.getItem('uiState')
      if (savedState) {
        const parsedState = JSON.parse(savedState)
        state.showCoder = parsedState.showCoder
        state.showPreview = parsedState.showPreview
      }
    }
  },
)