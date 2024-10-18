import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
export const namespaced = true

export const state = () => ({
})

export const getters = getterTree(state, {
  $$storex: () => ($storex.$parent || $storex),
  showCoder: () => ($storex.$parent || $storex).app.$route.path === '/split/coder',
  showPreview: () => ($storex.$parent || $storex).app.$route.path === '/split/preview'
})

export const mutations = mutationTree(state, {
  loadState(state) {
    const savedState = localStorage.getItem('uiState')
    if (savedState) {
      const parsedState = JSON.parse(savedState)
      state.showCoder = parsedState.showCoder
      state.showPreview = parsedState.showPreview
    }
  }
})

function setPath(path) {
  ($storex.$parent || $storex).ui.navigate(path)
}

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }) {
      $storex.ui.loadState()
    },
    saveState({ state }) {
      localStorage.setItem('uiState', JSON.stringify(state))
    },
    toggleCoder() {
      if ($storex.ui.showCoder) {
        setPath("/")
      } else {
        setPath("/split/coder")
      }
    },
    togglePreview() {
      if ($storex.ui.showPreview) {
        setPath("/")
      } else {
        setPath("/split/preview")
      }
    },
    navigate(_, path) {
      window.location = path
    }
  },
)
