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

function getProjectChat({ owner_project_id, project_id }) {
  return $storex.projects.allProjectsById[owner_project_id, project_id] ||
            $storex.projects.activeProject
}

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }) {
    },
    async readFile({ state }, { chat, file }) {
      const project = getProjectChat(chat) 
      return project.$api.files.read(file)
    },
    async writeFile({ state }, { chat, file, content }) {
      const project = getProjectChat(chat) 
      return project.$api.files.write(file, content)
    }
  }
)