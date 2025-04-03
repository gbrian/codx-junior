import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

import { API } from '../api/api'
export const state = () => ({
  codxJunior: null,
  user: null,
  users: []
})

export const getters = getterTree(state, {
  allUsers: ({ codxJunior, users }) => codxJunior ? [ codxJunior, ...users ] : []
})

export const mutations = mutationTree(state, {
  setUsers (state, users) {
  },
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }, $storex) {
      state.codxJunior = { 
        userName: "codx-junior", 
        avatar: API.globalSettings.codx_junior_avatar
      }
    },
    async login({ state }, user) {
      state.user = await API.user.login(user)
    },
    async logout({ state }) {
      state.user = null
    },
    async saveUser({ state }, user) {
      state.user = await API.user.save(user)
    }
  }
)