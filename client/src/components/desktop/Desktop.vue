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
import ViewProperties from '../main-menu/ViewProperties.vue'
import AnalyticsDashboard from '../analytics/index.vue'
import LogsAnalyzerDashboard from '../logs/LogsAnalyzerDashboard.vue'
</script>

<template>
  <div class="w-full h-full relative">
    <dockview-vue
      class="dockview-theme-abyss w-full h-full"
      @ready="onReady"
    />

    <!-- ViewProperties modal triggered by store viewEditor flag -->
    <modal close="true" @close="closeViewEditor" v-if="viewEditor">
      <ViewProperties
        :view="viewEditor.view"
        @close="closeViewEditor"
        @confirm="closeViewEditor"
      />
    </modal>
  </div>
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
    'analytics': AnalyticsDashboard,
    'chat-logs': LogsAnalyzerDashboard,
    tabComponent: Tab,
    ViewProperties
  },
  props: {
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
    },
    viewEditor() {
      return this.$storex.ui.viewEditor
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
    closeViewEditor() {
      this.$storex.ui.closeViewEditor()
    },
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
    onReady(event) {
      this.dockviewApi = event.api
      this.$ui.setDesktopApi(this.dockviewApi)
      this.restoreLayout()
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
    removePanel(id) {
      if (!this.dockviewApi) return
      const panel = this.dockviewApi.getPanel(id)
      panel && this.dockviewApi.removePanel(panel)
    },
    registerComponent(name, component) {
      this.registeredComponents = {
        ...this.registeredComponents,
        [name]: component
      }
    },
    saveLayout() {
      if (!this.dockviewApi) return null
      const layout = this.dockviewApi.toJSON()
      localStorage.setItem(this.storageKey, JSON.stringify(layout))
      return layout
    },
    restoreLayout(layout = null) {
      if (this.layoutRestored) return true
      if (!this.dockviewApi || !this.uiReady) return false
      try {
        const data = layout || JSON.parse(localStorage.getItem(this.storageKey))
        if (!data) return false
        this.dockviewApi.fromJSON(data)
        this.dockviewApi.panels.forEach(panel => {
          if (panel.params.chat) {
            this.$chats.reloadChat(panel.params.chat)
          }
          this.$ui.showApp(panel.params.app)
        })
        this.init()
        this.layoutRestored = true
      } catch (e) {
        console.warn('Failed to restore dockview layout:', e)
        return false
      }
    },
    clearSavedLayout() {
      localStorage.removeItem(this.storageKey)
      this.$emit('layout-cleared')
    },
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

<style>
.dv-tabs-and-actions-container {
    background-color: inherit;
    box-sizing: unset;
    height: inherit;
    font-size: inherit;
}

.dv-tabs-and-actions-container {
  height: fit-content;
  background-color: inherit !important;
}

.dv-tabs-and-actions-container .dv-tabs-container > .dv-tab.dv-inactive-tab,
.dv-tab {
  background-color: inherit;
}

.dv-groupview.dv-active-group > .dv-tabs-and-actions-container .dv-tabs-container > .dv-tab.dv-inactive-tab,
.dv-groupview.dv-active-group > .dv-tabs-and-actions-container .dv-tabs-container > .dv-tab.dv-active-tab {
    background-color: inherit;
    color: inherit;
}
</style>