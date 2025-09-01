import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

import { API } from '../api/api'
export const state = () => ({
  onlineUsers: {}
})

export const getters = getterTree(state, {
  user: () => API.user,
  isAdmin: () => API.user?.role === 'admin',
  allUsers: ({ codxJunior, users }) => codxJunior ? [ codxJunior, ...users ] : [],
  codxJunior: () => (      state.codxJunior = { 
        userName: "codx-junior", 
        avatar: API.globalSettings?.codx_junior_avatar
      })
})

export const mutations = mutationTree(state, {
  setOnlineUsers(state, users) {
    state.onlineUsers = users
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }, $storex) {
    },
    async login({ _ }, user) {
      try {
        await API.users.login(user)
      } catch(ex) {
        $storex.session.onError("Login error")
      }
      $storex.init()
    },
    async oauthLogin({ _ }, { provider, code, state }) {
      try {
        await API.oauth.oauthLogin({ oauth_provider: provider, code, state });
        window.location.reload()
      } catch (ex) {
        $storex.session.onError("OAuth login error")
        throw ex;
      }
      $storex.init()
    },
    async logout() {
      await API.users.logout()
      $storex.init()
    },
    async saveUser({ state }, user) {
      await API.users.save(user)
      $storex.session.onInfo("User account updated")
    }
  }
)