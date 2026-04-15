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
</script>
<template>
  <dockview-vue
    class="dockview-theme-abyss w-full h-full"
    @ready="onReady"
    :components="registeredComponents"
  />
</template>
<script>
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
    'chat': ChatView
  },
  props: {
    // Initial panels to render on mount
    panels: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      dockviewApi: null,
      // Map of registered component names to Vue components
      registeredComponents: {
        'window': Window,
        'app-window': AppWindow,
      }
    }
  },
  methods: {
    // Store dockview API and add initial panels
    onReady(event) {
      this.dockviewApi = event.api
      this.panels.forEach(panel => this.addPanel(panel))
    },

    // Add a new panel to the desktop
    addPanel({ id, title, component = 'window', position, params }) {
      if (!this.dockviewApi) return
      this.dockviewApi.addPanel({
        id,
        title,
        component,
        position,
        params
      })
    },

    // Remove a panel by id
    removePanel(id) {
      if (!this.dockviewApi) return
      const panel = this.dockviewApi.getPanel(id)
      panel && this.dockviewApi.removePanel(panel)
    },

    // Register a new component so it can be used as a panel
    registerComponent(name, component) {
      // this.registeredComponents = {
      //   ...this.registeredComponents,
      //   [name]: component
      // }
    }
  },
  expose: [ "addPanel", "removePanel", "registerComponent" ]
}
</script>