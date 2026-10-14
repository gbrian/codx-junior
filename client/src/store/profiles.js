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
    async loadProjectProfiles({ state, commit }, payload) {
      // Accept either a raw project or an options object { project, force }
      const project = payload?.project || payload
      const force = payload?.force || false
      if (!project) return []

      const projectId = project.project_id

      // Return cached profiles unless a forced reload was requested
      if (!force && state.profilesByProject[projectId] && state.profilesByProject[projectId].length > 0) {
        return state.profilesByProject[projectId]
      }

      try {
        const api = project.$api || $storex.api
        if (!api) return []

        const profiles = await api.profiles.list()
        commit('setProjectProfiles', { projectId, profiles: profiles || [] })

        // Keep the per-project state in sync so getters and mentions stay fresh
        if (project.$state) {
          project.$state.profiles = profiles || []
          project.$state._mentionList = null
        }

        return profiles || []
      } catch (err) {
        console.error(`Failed to load profiles for project ${projectId}:`, err)
        commit('setProjectProfiles', { projectId, profiles: [] })
        return []
      }
    },
    async saveProfile({ state, commit }, { project, profile }) {
      const data = await project.$api.profiles.save(profile)

      // Force a reload so the saved changes are reflected in the store
      const profiles = await $storex.profiles.loadProjectProfiles({ project, force: true })
      return profiles.find(p => p.name === data.name)
    },
    async deleteProfile({ state, commit }, { project, profile }) {
      await project.$api.profiles.delete(profile.name)

      // Force a reload so the removed profile disappears from the store
      return await $storex.profiles.loadProjectProfiles({ project, force: true })
    }
  }
)
