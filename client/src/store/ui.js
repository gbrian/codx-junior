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
  },
  togglePreview(state) {
    state.showPreview = !state.showPreview
    if (state.showCoder && state.showPreview) {
      state.showCoder = false
    }
  }
})

export const getters = getterTree(state, {
  spliView: () => $storex.ui.showCoder || $storex.ui.showPreview
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }) {
    },
  },
)