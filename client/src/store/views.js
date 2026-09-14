import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

const STORAGE_KEY_PREFIX = 'projectLayout'

export const state = () => ({
  _desktopApi: null,
  _layoutChangeDisposable: null,
  _activePanelDisposable: null,
  _panelAddDisposable: null,
  _panelRemoveDisposable: null,
  loadedView: false,
  fullscreenPanelId: null
})

export const getters = getterTree(state, {
  isPanelFullscreen: state => panelId => state.fullscreenPanelId === panelId,
})

export const mutations = mutationTree(state, {
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

    $storex.views.autoLoadLastLayout()
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

    async unloadCurrentLayout({ state }) {
      state.loadedView = null
      try {
        const desktopApi = $storex.views._desktopApi
        if (desktopApi) {
          desktopApi.clear()
        }
        $storex.ui.resetOpenApps()
      } catch (error) {
        console.error('Failed to unload current layout:', error)
      }
    },

    async onActiveProjectChanged() {
      await $storex.views.unloadCurrentLayout()
      await $storex.views.autoLoadLastLayout()
    },

    async autoLoadLastLayout({ state }) {
      const desktopApi = state._desktopApi

      if (!desktopApi) {
        console.warn('Desktop API not yet available for auto-loading layout')
        return
      }

      try {
        const key = getProjectStorageKey()
        if (!key) {
          await $storex.views.createEmptyLayout()
          return
        }

        const savedData = localStorage.getItem(key)
        if (savedData) {
          const layout = JSON.parse(savedData)
          desktopApi.fromJSON(layout)
          state.loadedView = key
          await $storex.views.syncAppsFromLayout(layout)
        } else {
          await $storex.views.createEmptyLayout()
        }
      } catch (error) {
        console.error('Failed to auto-load last layout:', error)
        await $storex.views.createEmptyLayout()
      }
    },

    async createEmptyLayout() {
      try {
        const desktopApi = $storex.views._desktopApi
        if (!desktopApi) return

        desktopApi.clear()
        $storex.ui.openTasks()
      } catch (error) {
        console.error('Failed to create empty layout:', error)
      }
    },

    async syncAppsFromLayout(_, layout) {
      try {
        const apps = extractAppsFromLayout(layout)
        for (const app of apps) {
          $storex.ui.showApp(app)
        }
        const panels = $storex.views._desktopApi.panels
        panels.map(panel => panel.isActive && $storex.views.onPanelActive(panel) )
        if (!panels.length) {
          $storex.ui.openTasks()
        }
      } catch (error) {
        console.error('Failed to sync apps from layout:', error)
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
      if (!state.loadedView) {
        // If "uloading view" ignore this events
        return
      }
      try {
        const desktopApi = state._desktopApi
        if (!desktopApi) return

        const layout = desktopApi.toJSON()
        const key = getProjectStorageKey()
        if (!key) return

        localStorage.setItem(key, JSON.stringify(layout))
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
          const app = params?.app
          const initialParams = app?.initialParams || params

          desktopApi.addPanel({
            id,
            title,
            component,
            position,
            renderer,
            key: app?.key,
            params: {
              ...params,
              tabName: title,
              initialParams
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

    syncPanelsWithApps({ state }, desktopApi) {
      const api = desktopApi || state._desktopApi
      if (!api) return

      const { openApps } = $storex.ui
      const apps = Object.values(openApps)
      const panelTabIds = api.panels.map(p => p.id)
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