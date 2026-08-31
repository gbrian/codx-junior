import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

const STORAGE_KEY_PREFIX = 'views'

export const state = () => ({
  views: [],
  currentView: null,
  lastView: null,
  _desktopApi: null,
  _layoutChangeDisposable: null,
  _activePanelDisposable: null,
  _panelAddDisposable: null,
  _panelRemoveDisposable: null,
  fullscreenPanelId: null
})

export const getters = getterTree(state, {
  viewNames: state => state.views.map(v => v.name),
  hasViews: state => state.views.length > 0,
  currentViewName: state => state.currentView?.name || null,
  isPanelFullscreen: state => panelId => state.fullscreenPanelId === panelId,
})

export const mutations = mutationTree(state, {
  setViews(state, views) {
    state.views = views || []
  },
  setCurrentView(state, view) {
    state.currentView = view || null
  },
  setLastView(state, view) {
    state.lastView = view || null
  },
  upsertView(state, view) {
    const index = state.views.findIndex(v => v.name === view.name)
    if (index >= 0) {
      state.views.splice(index, 1, view)
    } else {
      state.views.push(view)
    }
  },
  removeView(state, viewName) {
    state.views = state.views.filter(v => v.name !== viewName)
  },
  setDesktopApi(state, api) {
    // Cleanup old disposables
    if (state._layoutChangeDisposable?.dispose) {
      state._layoutChangeDisposable.dispose()
      state._layoutChangeDisposable = null
    }
    if (state._activePanelDisposable?.dispose) {
      state._activePanelDisposable.dispose()
      state._activePanelDisposable = null
    }
    if (state._panelAddDisposable?.dispose) {
      state._panelAddDisposable.dispose()
      state._panelAddDisposable = null
    }
    if (state._panelRemoveDisposable?.dispose) {
      state._panelRemoveDisposable.dispose()
      state._panelRemoveDisposable = null
    }

    state._desktopApi = api

    if (!api) return

    // Setup all event listeners
    if (api.onDidLayoutChange) {
      state._layoutChangeDisposable = api.onDidLayoutChange(() => {
        $storex.views.onLayoutChanged()
      })
    }

    if (api.onDidActivePanelChange) {
      state._activePanelDisposable = api.onDidActivePanelChange((event) => {
        $storex.views.onPanelActive(event)
      })
    }

    if (api.onDidAddPanel) {
      state._panelAddDisposable = api.onDidAddPanel(() => {
        $storex.views.onLayoutChanged()
      })
    }

    if (api.onDidRemovePanel) {
      state._panelRemoveDisposable = api.onDidRemovePanel((panel) => {
        $storex.views.onPanelRemoved(panel)
      })
    }
  },
  setFullscreenPanel(state, panelId) {
    state.fullscreenPanelId = panelId
  },
  clearFullscreenPanel(state) {
    state.fullscreenPanelId = null
  }
})

function getProjectStorageKey() {
  const projectName = $storex.projects?.activeProject?.project_name
  if (!projectName) return null
  return `${STORAGE_KEY_PREFIX}_${projectName}`
}

function extractAppsFromLayout(layout) {
  const apps = []
  if (!layout.panels) return apps

  for (const panel of Object.values(layout.panels)) {
    if (panel.params) {
      apps.push({
        tabId: panel.id || panel.tabId,
        name: panel.name || panel.componentName || 'Unknown',
        component: panel.componentName || 'unknown',
        key: panel.key,
        params: panel.params,
        openedAt: panel.openedAt || Date.now()
      })
    }
  }

  return apps
}

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init() {
      await $storex.views.restoreLastProject()
    },

    async restoreLastProject() {
      try {
        const lastProjectId = localStorage.getItem('lastActiveProject')
        if (lastProjectId) {
          const project = $storex.projects.allProjects?.find(p => p.project_id === lastProjectId)
          if (project) {
            await $storex.projects.activeProjectChanged(project)
            return
          }
        }
        
        const defaultProject = $storex.projects.allProjects?.find(p => p.project_name === 'codx-junior')
        if (defaultProject) {
          await $storex.projects.activeProjectChanged(defaultProject)
        }
      } catch (error) {
        console.error('Failed to restore last project:', error)
      }
    },

    async loadViews() {
      if (!$storex.projects?.activeProject) return
      try {
        const key = getProjectStorageKey()
        if (!key) return

        const stored = localStorage.getItem(key)
        const gridData = stored ? JSON.parse(stored) : { views: [], currentView: null, lastView: null }
        
        $storex.views.setViews(gridData.views || [])
        
        const lastViewName = gridData.lastView
        if (lastViewName) {
          const lastView = gridData.views.find(v => v.name === lastViewName)
          if (lastView) {
            $storex.views.setLastView(lastView)
          }
        }
      } catch (error) {
        console.error('Failed to load views from localStorage:', error)
        $storex.views.setViews([])
      }
    },

    async onActiveProjectChanged() {
      $storex.views.setCurrentView(null)
      $storex.views.setLastView(null)
      await $storex.projects.saveLastActiveProject()
      await $storex.views.loadViews()
      
      $storex.ui.resetOpenApps()
      await $storex.views.autoLoadLastView()
    },

    async autoLoadLastView({ state }) {
      const lastView = state.lastView
      if (!lastView?.layout) {
        console.warn('No last view found, creating empty layout')
        return
      }

      try {
        if (!state._desktopApi) {
          console.warn('Desktop API not yet available for auto-loading view')
          return
        }
        
        await $storex.views.loadView(lastView)
      } catch (error) {
        console.error('Failed to auto-load last view:', error)
      }
    },

    async saveView({ state }, viewName) {
      try {
        const desktopApi = state._desktopApi
        if (!desktopApi) throw new Error('Desktop API not available')

        const layout = desktopApi.toJSON()
        const key = getProjectStorageKey()
        if (!key) throw new Error('No active project')

        const view = {
          name: viewName,
          layout,
          last_update: Date.now()
        }

        $storex.views.upsertView(view)
        await $storex.views.persistViews()
        $storex.views.setLastView(view)
        
        return view
      } catch (error) {
        console.error('Failed to save view:', error)
        throw error
      }
    },

    async loadView({ state }, view) {
      try {
        if (!view?.layout) throw new Error('Invalid view or layout')

        $storex.views.setCurrentView(view)
        $storex.views.setLastView(view)

        const desktopApi = state._desktopApi
        if (desktopApi) {
          desktopApi.fromJSON(view.layout)
          await $storex.views.syncAppsFromLayout(view.layout)
        }
      } catch (error) {
        console.error('Failed to load view:', error)
        throw error
      }
    },

    async deleteView({ state }, viewName) {
      try {
        $storex.views.removeView(viewName)
        await $storex.views.persistViews()

        if (state.currentView?.name === viewName) {
          $storex.views.setCurrentView(null)
        }
        if (state.lastView?.name === viewName) {
          $storex.views.setLastView(null)
        }
      } catch (error) {
        console.error('Failed to delete view:', error)
        throw error
      }
    },

    async renameView({ state }, { oldName, newName }) {
      try {
        const existing = state.views.find(v => v.name === oldName)
        if (existing) {
          const renamedView = { ...existing, name: newName }
          $storex.views.removeView(oldName)
          $storex.views.upsertView(renamedView)

          if (state.currentView?.name === oldName) {
            $storex.views.setCurrentView(renamedView)
          }
          if (state.lastView?.name === oldName) {
            $storex.views.setLastView(renamedView)
          }

          await $storex.views.persistViews()
        }
      } catch (error) {
        console.error('Failed to rename view:', error)
        throw error
      }
    },

    async persistViews({ state }) {
      try {
        const key = getProjectStorageKey()
        if (!key) return

        const gridData = {
          views: state.views,
          currentView: state.currentView?.name || null,
          lastView: state.lastView?.name || null,
          lastUpdated: Date.now()
        }

        localStorage.setItem(key, JSON.stringify(gridData))
      } catch (error) {
        console.error('Failed to persist views to localStorage:', error)
        throw error
      }
    },

    async saveCurrentView({ state }) {
      try {
        const view = state.lastView || state.currentView
        if (!view?.name) return
        await $storex.views.saveView(view.name)
      } catch (error) {
        console.error('Error saving current view:', error)
      }
    },

    async syncAppsFromLayout(_, layout) {
      try {
        const apps = extractAppsFromLayout(layout)
        for (const app of apps) {
          $storex.ui.showApp(app)
        }
      } catch (error) {
        console.error('Failed to sync apps from layout:', error)
      }
    },

    async restoreProjectLayout({ state }, desktopApi) {
      if (!desktopApi || !$storex.projects?.activeProject) {
        throw new Error('Desktop API or active project not available')
      }

      try {
        const key = getProjectStorageKey()
        if (!key) throw new Error('No active project storage key')

        const stored = localStorage.getItem(key)
        if (!stored) return false

        let gridData
        try {
          gridData = JSON.parse(stored)
        } catch (parseError) {
          console.error('Failed to parse stored layout:', parseError)
          return false
        }

        if (!gridData.views?.length) return false

        const lastViewName = gridData.lastView
        let layoutToRestore = null

        if (lastViewName) {
          const view = gridData.views.find(v => v.name === lastViewName)
          if (view?.layout) {
            layoutToRestore = view.layout
            $storex.views.setLastView(view)
          }
        }

        if (layoutToRestore) {
          desktopApi.fromJSON(layoutToRestore)
          await $storex.views.syncAppsFromLayout(layoutToRestore)
          return true
        }

        return false
      } catch (error) {
        console.error('Failed to restore project layout:', error)
        return false
      }
    },

    togglePanelFullscreen({ state }, panelId) {
      if (!state._desktopApi) return
      try {
        const panel = state._desktopApi.getPanel(panelId)
        if (panel) {
          state._desktopApi.maximizePanel(panel)
        }
      } catch(e) {
        console.error(`Error toggling fullscreen for panel ${panelId}:`, e)
      }
    },

    async onLayoutChanged({ state }) {
      try {
        const desktopApi = state._desktopApi
        if (!desktopApi) return

        const layout = desktopApi.toJSON()
        const key = getProjectStorageKey()
        if (!key) return

        if ($storex.views.lastView) {
          $storex.views.lastView.layout = layout
          $storex.views.lastView.last_update = Date.now()
          $storex.views.upsertView($storex.views.lastView)
        } else {
          const defaultView = {
            name: 'Default',
            layout,
            last_update: Date.now()
          }
          $storex.views.upsertView(defaultView)
          $storex.views.setLastView(defaultView)
        }

        await $storex.views.persistViews()
      } catch (error) {
        console.error('Error saving layout:', error)
      }
    },

    async onPanelActive(_, panel) {
      if (!panel) {
        return
      }
      try {
        const params = panel.params?.params || panel.params
        const chat = params?.chat
        if (!chat?.id) return

        await $storex.chats.loadUninitialized(chat)
      } catch (error) {
        console.error('Error handling active panel change:', error)
      }
    },

    async onPanelRemoved(_, panel) {
      try {
        const app = panel.params?.app
        if (app) {
          $storex.ui.closeApp(app)
        }
      } catch (error) {
        console.error('Error handling panel remove:', error)
      }
    },

    async activatePanel(_, panelId) {
      try {
        const desktopApi = $storex.views._desktopApi
        if (!desktopApi) return
        
        const panel = desktopApi.getPanel(panelId)
        if (panel) {
          desktopApi.setActivePanel(panel)
        }
      } catch (error) {
        console.error(`Error activating panel ${panelId}:`, error)
      }
    },

    addPanelToDesktop(_, { id, title, component, position, params, renderer }) {
      const desktopApi = $storex.views._desktopApi
      if (!desktopApi) return
      
      try {
        if (!desktopApi.panels.find(p => p.id === id)) {
          desktopApi.addPanel({
            id,
            title,
            component,
            position,
            renderer,
            params: {
              ...params,
              tabName: title,
            },
            tabComponent: 'tabComponent'
          })
        }
      } catch (error) {
        console.error(`Error adding panel ${id}:`, error)
        throw error
      }
    },

    removePanelFromDesktop(_, panelId) {
      const desktopApi = $storex.views._desktopApi
      if (!desktopApi) return
      
      try {
        const panel = desktopApi.getPanel(panelId)
        if (panel) {
          desktopApi.removePanel(panel)
        }
      } catch (error) {
        console.error(`Error removing panel ${panelId}:`, error)
      }
    },

    syncPanelsWithApps({ state }) {
      const desktopApi = state._desktopApi
      if (!desktopApi) return

      const { openApps } = $storex.ui
      const apps = Object.values(openApps)
      const panelTabIds = desktopApi.panels.map(p => p.id)
      const openAppTabIds = apps.map(app => app.tabId)

      // Add missing app panels
      apps
        .filter(({ tabId }) => !panelTabIds.includes(tabId))
        .forEach(app => {
          if (!app?.tabId) return
          const component = app.component || 'app-window'
          const renderer = 'always'
          try {
            $storex.views.addPanelToDesktop({
              id: app.tabId,
              title: app.name,
              component,
              renderer,
              params: {
                ...app.params || {},
                app
              }
            })
          } catch (error) {
            console.error('Error adding app panel:', error)
          }
        })

      // Remove closed app panels
      panelTabIds
        .filter(tabId => !openAppTabIds.includes(tabId))
        .forEach(tabId => $storex.views.removePanelFromDesktop(tabId))
    }
  }
)