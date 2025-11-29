import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

export const state = () => ({
  profiles: {}
})

export const getters = getterTree(state, {
  allProfiles: state => Object.keys(state.profiles).reduce((acc, key) => acc.concat(state.profiles[key]), [])
})

export const mutations = mutationTree(state, {
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }, $storex) {
    },
    async loadProjectProfiles({ state }, project) {
      const profiles = await $storex.api.project(project)
                        .then(p => p.profiles.list())
      state.profiles[project.project_id] = profiles
    },
    async saveProfile({ state }, { project, profile }) {
      const data = await project.$api.profiles.save(profile)
      const profiles = state.profiles[project.project_id]
      state.profiles[project.project_id] = [...profiles.filter(p => p.name !== data.name), data]
      return data
    },
    async deleteProfile({ state }, { project, profile }) {
      await project.$api.profiles.delete(profile.name)
    }
  }
)