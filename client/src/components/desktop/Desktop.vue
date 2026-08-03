<script setup>
import { DockviewVue } from 'dockview-vue'
import { ALL_COMPONENTS } from '../../config/appComponentsMap.js'
import ViewProperties from '../main-menu/ViewProperties.vue'
</script>

<template>
  <div class="w-full h-full relative">
    <dockview-vue
      class="dockview-theme-abyss w-full h-full"
      @ready="onReady"
      @panel-error="onPanelError"
    />

    <!-- ViewProperties modal triggered by store viewEditor flag -->
    <modal close="true" @close="closeViewEditor" v-if="viewEditor">
      <ViewProperties
        :view="viewEditor.view"
        @close="closeViewEditor"
        @confirm="closeViewEditor"
      />
    </modal>

    <!-- Error notification for failed panels -->
    <div v-if="failedPanels.length" class="alert alert-error shadow-lg fixed bottom-4 right-4 max-w-md z-50">
      <div>
        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l-2-2m0 0l-2-2m2 2l2-2m-2 2l-2 2m2-2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>{{ failedPanelsMessage }}</span>
      </div>
      <button class="btn btn-sm" @click="clearFailedPanels">Dismiss</button>
    </div>
  </div>
</template>

<script>
const STORAGE_KEY = 'dockview-layout'

export default {
  name: 'Desktop',
  components: ALL_COMPONENTS,
  props: {
    storageKey: {
      type: String,
      default: STORAGE_KEY
    }
  },
  data() {
    return {
      dockviewApi: null,
      registeredComponents: {},
      layoutRestored: false,
      failedPanels: [],
      panelErrorTimeout: null
    }
  },
  computed: {
    apps() {
      const { openApps } = this.$ui
      return Object.values(openApps)
    },
    panelTabIds() {
      return this.dockviewApi?.panels.map(p => p.id) || []
    },
    uiReady() {
      return this.$ui.uiReady
    },
    viewEditor() {
      return this.$storex.ui.viewEditor
    },
    failedPanelsMessage() {
      const count = this.failedPanels.length
      return count === 1
        ? `Failed to load panel: ${this.failedPanels[0]}`
        : `Failed to load ${count} panels`
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
      try {
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
      } catch(ex) {
        console.error('Error adding app panel:', ex)
        this.handlePanelError(app.tabId, app.name)
      }
    },
    onReady(event) {
      this.dockviewApi = event.api
      this.$ui.setDesktopApi(this.dockviewApi)
      this.setupPanelErrorHandlers()
      this.restoreLayout()
      this.dockviewApi.onDidAddPanel(this.onAddPanel.bind(this))
      this.dockviewApi.onDidRemovePanel(this.onRemovePanel.bind(this))
      this.dockviewApi.onDidLayoutChange(this.onLayoutChange.bind(this))
    },
    setupPanelErrorHandlers() {
      if (!this.dockviewApi) return
      try {
        this.dockviewApi.onDidPanelError?.((event) => {
          this.onPanelError(event)
        })
      } catch(e) {
        console.warn('Panel error handler not available:', e)
      }
    },
    onPanelError(event) {
      const panelId = event?.panelId || event?.id
      const panelTitle = this.getPanelTitle(panelId)
      console.error(`Panel error (${panelId}):`, event)
      this.handlePanelError(panelId, panelTitle)
      this.safelyRemovePanel(panelId)
    },
    onAddPanel() {
      this.saveLayoutImmediately()
    },
    onRemovePanel(panel) {
      try {
        this.$ui.closeApp(panel.params?.app)
      } catch(e) {
        console.warn('Error closing app on panel remove:', e)
      }
      this.saveLayoutImmediately()
    },
    onLayoutChange() {
      this.saveLayoutImmediately()
    },
    saveLayoutImmediately() {
      if (!this.dockviewApi) return
      try {
        const layout = this.dockviewApi.toJSON()
        localStorage.setItem(this.storageKey, JSON.stringify(layout))
      } catch(e) {
        console.error('Error saving layout:', e)
      }
    },
    addPanel({ id, title, component = 'window', position, params, renderer }) {
      if (!this.dockviewApi) return
      try {
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
      } catch(e) {
        console.error(`Error adding panel ${id}:`, e)
        this.handlePanelError(id, title)
        throw e
      }
    },
    removePanel(id) {
      if (!this.dockviewApi) return
      this.safelyRemovePanel(id)
    },
    safelyRemovePanel(id) {
      try {
        const panel = this.dockviewApi?.getPanel(id)
        if (panel) {
          this.dockviewApi.removePanel(panel)
        }
      } catch(e) {
        console.error(`Error removing panel ${id}:`, e)
      }
    },
    handlePanelError(panelId, panelTitle) {
      const displayName = panelTitle || panelId
      if (!this.failedPanels.includes(displayName)) {
        this.failedPanels.push(displayName)
      }
      this.resetErrorTimeout()
    },
    resetErrorTimeout() {
      if (this.panelErrorTimeout) {
        clearTimeout(this.panelErrorTimeout)
      }
      this.panelErrorTimeout = setTimeout(() => {
        this.clearFailedPanels()
      }, 5000)
    },
    clearFailedPanels() {
      this.failedPanels = []
      if (this.panelErrorTimeout) {
        clearTimeout(this.panelErrorTimeout)
        this.panelErrorTimeout = null
      }
    },
    getPanelTitle(panelId) {
      try {
        const panel = this.dockviewApi?.getPanel(panelId)
        return panel?.title || panelId
      } catch(e) {
        return panelId
      }
    },
    registerComponent(name, component) {
      this.registeredComponents = {
        ...this.registeredComponents,
        [name]: component
      }
    },
    restoreLayout(layout = null) {
      if (this.layoutRestored) return true
      if (!this.dockviewApi || !this.uiReady) return false
      try {
        const data = layout || JSON.parse(localStorage.getItem(this.storageKey))
        if (!data) return false
        this.dockviewApi.fromJSON(data)
        this.dockviewApi.panels.forEach(panel => {
          try {
            if (panel.params?.chat) {
              this.$chats.reloadChat(panel.params.chat)
            }
            if (panel.params?.app) {
              this.$ui.showApp(panel.params.app)
            }
          } catch(e) {
            console.warn(`Error restoring panel ${panel.id}:`, e)
            this.handlePanelError(panel.id, panel.title)
          }
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
    'addPanel',
    'removePanel',
    'registerComponent',
    'restoreLayout',
    'clearSavedLayout',
    'getLayout'
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