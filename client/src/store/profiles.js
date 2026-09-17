import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

export const state = () => ({
  profilesByProject: {}
})

export const getters = getterTree(state, {
  allProfiles: state => Object.keys(state.profilesByProject).reduce((acc, key) => acc.concat(state.profilesByProject[key]), []),
  profiles: state => state.profilesByProject[$storex.projects.activeProject?.project_id] || []
})

export const mutations = mutationTree(state, {
  setProjectProfiles(state, { projectId, profiles }) {
    state.profilesByProject[projectId] = profiles
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }, $storex) {
    },
    async loadProjectProfiles({ state, commit }, project) {
      if (!project) return []
      
      const projectId = project.project_id
      
      // Check if profiles already loaded for this project
      if (state.profilesByProject[projectId] && state.profilesByProject[projectId].length > 0) {
        return state.profilesByProject[projectId]
      }

      try {
        const api = project.$api || $storex.api
        if (!api) return []
        
        const profiles = await api.profiles.list()
        commit('setProjectProfiles', { projectId, profiles: profiles || [] })
        return profiles || []
      } catch (err) {
        console.error(`Failed to load profiles for project ${projectId}:`, err)
        commit('setProjectProfiles', { projectId, profiles: [] })
        return []
      }
    },
    async saveProfile({ state, commit }, { project, profile }) {
      const projectId = project.project_id
      const data = await project.$api.profiles.save(profile)
      
      // Reload profiles after save
      const profiles = await this.dispatch('profiles/loadProjectProfiles', project, { root: true })
      return profiles.find(p => p.name === data.name)
    },
    async deleteProfile({ state, commit }, { project, profile }) {
      const projectId = project.project_id
      await project.$api.profiles.delete(profile.name)
      
      // Reload profiles after delete
      const profiles = await this.dispatch('profiles/loadProjectProfiles', project, { root: true })
      return profiles
    }
  }
)