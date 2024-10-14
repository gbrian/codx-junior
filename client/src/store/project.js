import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import { API } from '../api/api'

export const namespaced = true

export const state = () => ({
  activeProject: null,
  allProjects: []
})

export const mutations = mutationTree(state, {
  setAllProjects(state, allProjects) {
    state.allProjects = allProjects
  }
})

export const getters = getterTree(state, {
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }) {
        await API.init()
        $storex.project.setAllProjects(API.allProjects)
        state.activeProject = API.lastSettings
    },
    async setActiveProject ({ state }, project) {
      await API.init(project?.codx_path)
      state.activeProject = API.lastSettings
    },
  },
)