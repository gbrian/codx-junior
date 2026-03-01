import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import store, { $storex } from '.'

export const namespaced = true

export const state = () => ({
  chats: null,
})

export const getters = getterTree(state, {
})

export const mutations = mutationTree(state, {
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }) {
    },
    async readFile({ state }, { chat, file }) {
      const project = await $storex.projects.getChatProject(chat)
      return project.$api.files.read(file)
    },
    async writeFile({ state }, { chat, file, content }) {
      const project = await $storex.projects.getChatProject(chat)
      return project.$api.files.write(file, content)
    }
  }
)