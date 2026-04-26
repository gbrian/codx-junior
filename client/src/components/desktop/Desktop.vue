<script setup>
import { DockviewVue } from 'dockview-vue'
import Window from './Window.vue'
import AppWindow from '../windowManager/AppWindow.vue'
import LogViewer from '../LogViewer.vue'

import KnowledgeViewVue from "../../views/KnowledgeView.vue"
import KnowledgeSettingsVue from "../../views/KnowledgeSettings.vue"
import ProfileViewVue from "../../views/ProfileView.vue"
import CodxWelcomeView from "../../views/CodxWelcomeView.vue"
import ProjectSettingsVue from "../../views/ProjectSettings.vue"
import WikiViewVue from "../../views/WikiView.vue"
import DocsViewVue from "../../views/DocsView.vue"
import GlobalSettingsVue from "../../views/GlobalSettings.vue"
import KanbanContainerVue from "../kanban/KanbanContainer.vue"
import Files from "../apps/Files.vue"
import MetricsViewer from "../metrics/MetricsViewer.vue"
import AccountSettings from '../security/AccountSettings.vue'
import FileFinderVue from '../filebrowser/FileFinder.vue'
import ProjectOverview from "../project/ProjectOverview.vue"
import Wall from "../wall/Wall.vue"
import ChatView from '@/views/ChatView.vue'
import Tab from './Tab.vue'
</script>

<template>
  <dockview-vue
    class="dockview-theme-abyss w-full h-full"
    @ready="onReady"
  />
</template>

<script>
const STORAGE_KEY = 'dockview-layout'

export default {
  name: 'Desktop',
  components: {
    'dockview-vue': DockviewVue,
    'window': Window,
    'app-window': AppWindow,
    'log-viewer': LogViewer,
    'knowledge': KnowledgeViewVue,
    'knowledge_settings': KnowledgeSettingsVue,
    'profiles': ProfileViewVue,
    'home': CodxWelcomeView,
    'settings': ProjectSettingsVue,
    'wiki': WikiViewVue,
    'docs': DocsViewVue,
    'global-settings': GlobalSettingsVue,
    'tasks': KanbanContainerVue,
    'files': Files,
    'metrics': MetricsViewer,
    'account': AccountSettings,
    'file-finder': FileFinderVue,
    'projects': ProjectOverview,
    'activity': Wall,
    'chat': ChatView,
    tabComponent: Tab
  },
  props: {
    // localStorage key to persist layout
    storageKey: {
      type: String,
      default: STORAGE_KEY
    }
  },
  data() {
    return {
      dockviewApi: null,
      registeredComponents: {
        'window': Window,
        'app-window': AppWindow,
      },
      layoutRestored: false
    }
  },
  computed: {
    apps() {
      const { openApps } = this.$ui
      return Object.values(openApps)
    },
    panelTabIds() {
      return this.dockviewApi?.panels.map(p => p.id)
    },
    uiReady() {
      return this.$ui.uiReady
    }
  },
  watch: {
    apps(newVal) {
      const { panelTabIds } = this
      newVal
        .filter(({ tabId }) => !panelTabIds.includes(tabId))
        .forEach(app => this.addAppPanel(app))
      if (!newVal.length) {
        this.init()
      }
    },
    uiReady() {
      this.restoreLayout()
    }
  },
  methods: {
    init() {
      if (!this.panelTabIds.length) {
        this.$ui.showTab('home')
      }
    },
    addAppPanel(app) {
      if (!app?.tabId) return
      const component = app.component || 'app-window' 
      const renderer = 'always' 
      this.addPanel({
        id: app.tabId,
        title: app.name,
        component,
        renderer,
        params: {
          ...app.params || {},
          app
        }
      })
    },
    // Store dockview API, restore saved layout or add initial panels
    onReady(event) {
      this.dockviewApi = event.api
      this.restoreLayout()
      // Auto-save layout when panels are added or removed
      this.dockviewApi.onDidAddPanel(this.onAddPanel.bind(this))
      this.dockviewApi.onDidRemovePanel(this.onRemovePanel.bind(this))
      this.dockviewApi.onDidLayoutChange(this.saveLayout.bind(this))
    },
    onAddPanel() {
      this.saveLayout()
    },
    onRemovePanel(panel) {
      this.$ui.closeApp(panel.params.app)
      this.saveLayout()
    },
    // Add a new panel to the desktop
    addPanel({ id, title, component = 'window', position, params, renderer }) {
      if (!this.dockviewApi) return
      if (!this.dockviewApi.panels.find(p => p.id === id)) {
        this.dockviewApi.addPanel({ 
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
    },

    // Remove a panel by id
    removePanel(id) {
      if (!this.dockviewApi) return
      const panel = this.dockviewApi.getPanel(id)
      panel && this.dockviewApi.removePanel(panel)
    },

    // Register a new component so it can be used as a panel
    registerComponent(name, component) {
      this.registeredComponents = {
        ...this.registeredComponents,
        [name]: component
      }
    },

    // Serialize current layout to JSON and save to localStorage
    saveLayout() {
      if (!this.dockviewApi) return null
      const layout = this.dockviewApi.toJSON()
      localStorage.setItem(this.storageKey, JSON.stringify(layout))
      return layout
    },

    // Load layout JSON from localStorage and restore it
    restoreLayout(layout = null) {
      if (this.layoutRestored) return true
      if (!this.dockviewApi || !this.uiReady) return false
      try {
        const data = layout || JSON.parse(localStorage.getItem(this.storageKey))
        if (!data) return false
        this.dockviewApi.fromJSON(data)
        this.dockviewApi.panels.forEach(panel => {
          this.$ui.showApp(panel.params.app)
        })
        this.init()
        this.layoutRestored = true        
      } catch (e) {
        console.warn('Failed to restore dockview layout:', e)
        return false
      }
    },

    // Clear saved layout from localStorage
    clearSavedLayout() {
      localStorage.removeItem(this.storageKey)
      this.$emit('layout-cleared')
    },

    // Get current layout as plain JSON object (without saving)
    getLayout() {
      return this.dockviewApi ? this.dockviewApi.toJSON() : null
    }
  },
  expose: [
    "addPanel",
    "removePanel",
    "registerComponent",
    "saveLayout",
    "restoreLayout",
    "clearSavedLayout",
    "getLayout"
  ]
}
</script>