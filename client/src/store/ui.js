import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
export const namespaced = true

export const state = () => ({
  showCoder: false,
  showPreview: false,
})

export const getters = getterTree(state, {
  $$storex: () => ($storex.$parent || $storex),
  isSplitView: () => ($storex.$parent || $storex).app.$route.path.startsWith('/split'),
})

export const mutations = mutationTree(state, {
  loadState(state) {
    const savedState = localStorage.getItem('uiState')
    if (savedState) {
      const parsedState = JSON.parse(savedState)
      state.showCoder = parsedState.showCoder
      state.showPreview = parsedState.showPreview
    }
  },
  setShowCoder(state, show) {
    state.showCoder = show
  },
  setShowPreview(state, show) {
    state.showPreview = show
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
      const { ui } = $storex.ui.$$storex
      ui.setShowCoder(!ui.showCoder)
      if (ui.showCoder) {
        ui.setShowPreview(false)
        if (!$storex.ui.isSplitView) {
          setPath("/split/coder")
        }
      }
    },
    togglePreview() {
      const { ui } = $storex.ui.$$storex
      ui.setShowPreview(!ui.showPreview)
      if (ui.showPreview) {
        ui.setShowCoder(false)
        if (!$storex.ui.isSplitView) {
          setPath("/split/preview")
        }
      }
    },
    navigate(_, path) {
      window.location = path
    }
  },
)
