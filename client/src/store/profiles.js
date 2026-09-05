import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

export const state = () => ({
  profilesByProject: {}
})

export const getters = getterTree(state, {
  allProfiles: state => Object.keys(state.profilesByProject).reduce((acc, key) => acc.concat(state.profilesByProject[key]), []),
  profiles: state => state.profilesByProject[$storex.projects.activeProject.project_id]
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
      state.profilesByProject[project.project_id] = profiles
      return profiles
    },
    async saveProfile({ state }, { project, profile }) {
      const data = await project.$api.profiles.save(profile)
      return $storex.profiles.loadProjectProfiles(project)
    },
    async deleteProfile({ state }, { project, profile }) {
      await project.$api.profiles.delete(profile.name)
      return $storex.profiles.loadProjectProfiles(project)
    }
  }
)