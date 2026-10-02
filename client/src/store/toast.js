import { getterTree, mutationTree, actionTree } from 'typed-vuex'

export const namespaced = true

export const state = () => ({
  _toastInstance: null
})

export const mutations = mutationTree(state, {
  setToastInstance(state, instance) {
    state._toastInstance = instance
  }
})

export const getters = getterTree(state, {
  toastApi: state => ({
    success: (msg, duration) => state._toastInstance?.success(msg, duration),
    error: (msg, duration) => state._toastInstance?.error(msg, duration),
    warning: (msg, duration) => state._toastInstance?.warning(msg, duration),
    info: (msg, duration) => state._toastInstance?.info(msg, duration),
    clear: () => state._toastInstance?.clear()
  })
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    // FIXED: use the mutation instead of direct state assignment
    registerInstance({ commit }, instance) {
      commit('setToastInstance', instance)
    }
  }
)