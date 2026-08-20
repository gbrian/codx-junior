import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import { API } from '../api/api'

export const namespaced = true

export const state = () => ({
  views: [],
  currentView: {},
  lastView: null
})

export const getters = getterTree(state, {
  viewNames: state => state.views.map(v => v.name),
  hasViews: state => state.views.length > 0,
  currentViewName: state => state.currentView?.name || null,
  projectViews: state => {
    const projectId = $storex.projects?.activeProject?.project_id
    return projectId ? state.views.filter(v => v.project_id === projectId) : []
  }
})

export const mutations = mutationTree(state, {
  setViews(state, views) {
    state.views = views || []
  },
  setCurrentView(state, view) {
    state.currentView = view || {}
  },
  setLastView(state, view) {
    state.lastView = view || null
  },
  addView(state, view) {
    if (!state.views.find(v => v.name === view.name && v.project_id === view.project_id)) {
      state.views.push(view)
    }
  },
  updateView(state, view) {
    const index = state.views.findIndex(v => v.name === view.name && v.project_id === view.project_id)
    if (index >= 0) {
      state.views[index] = view
    }
  },
  removeView(state, { viewName, projectId }) {
    state.views = state.views.filter(v => !(v.name === viewName && v.project_id === projectId))
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init() {
      await $storex.views.loadViews()
      
      // ADDED: Watch for active project changes
      $storex.store.subscribe((mutation, state) => {
        if (mutation.type === 'projects/setActiveProject') {
          $storex.views.onActiveProjectChanged()
        }
      })
    },

    async loadViews() {
      try {
        const api = $storex.projects?.activeProject?.$api || API
        const views = await api.views.list()
        $storex.views.setViews(views || [])
      } catch (error) {
        console.error('Failed to load views:', error)
        $storex.views.setViews([])
      }
    },

    // ADDED: Respond to active project changes
    async onActiveProjectChanged() {
      try {
        const projectId = $storex.projects?.activeProject?.project_id
        if (!projectId) {
          $storex.views.setCurrentView({})
          $storex.views.setLastView(null)
          return
        }

        // Load all views from active project
        await $storex.views.loadViews()
        
        // Get project's views
        const projectViews = state.views.filter(v => v.project_id === projectId)
        
        if (projectViews.length === 0) {
          // Create default view if none exist
          await $storex.views.createDefaultView()
        } else {
          // Load most recent view
          const lastView = await $storex.views.getProjectLastView()
          if (lastView) {
            await $storex.views.loadView(lastView)
          }
        }
      } catch (error) {
        console.error('Failed to handle active project change:', error)
      }
    },

    // ADDED: Get or create last view for active project
    async getProjectLastView() {
      try {
        const projectId = $storex.projects?.activeProject?.project_id
        if (!projectId) return null
        
        const projectViews = state.views.filter(v => v.project_id === projectId)
        if (projectViews.length === 0) {
          return null
        }
        
        // Return the most recently updated view
        return projectViews.reduce((latest, current) => 
          (current.last_update || 0) > (latest.last_update || 0) ? current : latest
        )
      } catch (error) {
        console.error('Failed to get project last view:', error)
        return null
      }
    },

    async saveView(_, viewName) {
      try {
        const layout = $storex.ui._desktopApi?.toJSON()
        if (!layout) {
          throw new Error('No layout to save')
        }
        const projectId = $storex.projects?.activeProject?.project_id
        const api = $storex.projects?.activeProject?.$api || API
        
        const view = {
          name: viewName,
          layout: layout,
          project_id: projectId,
          last_update: Date.now()
        }
        
        // CHANGED: Use activeProject.$api
        await api.views.save(view)
        $storex.views.addView(view)
        $storex.views.setLastView(view)
      } catch (error) {
        console.error('Failed to save view:', error)
        throw error
      }
    },

    // ADDED: Auto-save current view with updated layout
    async autoSaveCurrentView() {
      try {
        const view = state.lastView || state.currentView
        if (!view?.name) return
        
        const layout = $storex.ui._desktopApi?.toJSON()
        if (!layout) return
        
        const projectId = $storex.projects?.activeProject?.project_id
        const api = $storex.projects?.activeProject?.$api || API
        
        const updatedView = {
          ...view,
          layout: layout,
          project_id: projectId,
          last_update: Date.now()
        }
        
        // CHANGED: Use activeProject.$api
        await api.views.save(updatedView)
        $storex.views.updateView(updatedView)
        $storex.views.setLastView(updatedView)
      } catch (error) {
        console.error('Failed to auto-save view:', error)
      }
    },

    async loadView(_, view) {
      try {
        $storex.views.setCurrentView(view)
        $storex.views.setLastView(view)
        if (view.layout && $storex.ui._desktopApi) {
          $storex.ui._desktopApi.fromJSON(view.layout)
        }
      } catch (error) {
        console.error('Failed to load view:', error)
        throw error
      }
    },

    async deleteView(_, { viewName, projectId }) {
      try {
        const api = $storex.projects?.activeProject?.$api || API
        
        // CHANGED: Use activeProject.$api
        await api.views.delete(viewName)
        $storex.views.removeView({ viewName, projectId })
        if (state.currentView?.name === viewName) {
          $storex.views.setCurrentView({})
        }
      } catch (error) {
        console.error('Failed to delete view:', error)
        throw error
      }
    },

    async renameView(_, { oldName, newName }) {
      try {
        const api = $storex.projects?.activeProject?.$api || API
        
        // CHANGED: Use activeProject.$api
        await api.views.rename(oldName, newName)
        const view = state.views.find(v => v.name === oldName)
        if (view) {
          view.name = newName
          $storex.views.updateView(view)
          if (state.currentView?.name === oldName) {
            $storex.views.setCurrentView(view)
          }
          if (state.lastView?.name === oldName) {
            $storex.views.setLastView(view)
          }
        }
      } catch (error) {
        console.error('Failed to rename view:', error)
        throw error
      }
    },

    // ADDED: Create default empty view for active project
    async createDefaultView() {
      try {
        const projectId = $storex.projects?.activeProject?.project_id
        const api = $storex.projects?.activeProject?.$api || API
        
        if (!projectId) return

        // Create a basic empty layout
        const defaultLayout = {
          panels: [],
          layout: {
            type: 'branch',
            size: 1,
            data: [],
            children: []
          }
        }

        const view = {
          name: `Default View - ${new Date().toLocaleDateString()}`,
          layout: defaultLayout,
          project_id: projectId,
          last_update: Date.now()
        }

        // CHANGED: Use activeProject.$api
        await api.views.save(view)
        $storex.views.addView(view)
        $storex.views.setLastView(view)
        await $storex.views.loadView(view)
      } catch (error) {
        console.error('Failed to create default view:', error)
      }
    }
  }
)