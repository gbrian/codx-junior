<script setup>
import { DockviewVue } from 'dockview-vue'
import { ALL_COMPONENTS } from '../../config/appComponentsMap.js'
import ViewProperties from '../main-menu/ViewProperties.vue'
import GroupHeaderActions from './GroupHeaderActions.vue'
</script>

<template>
  <div class="w-full h-full relative">
    <dockview-vue
      class="dockview-theme-abyss w-full h-full"
      @ready="onReady"
      @panel-error="onPanelError"
      rightHeaderActionsComponent="groupHeaderActions"
    />

    <!-- ViewProperties modal triggered by store viewEditor flag -->
    <modal close="true" @close="closeViewEditor" v-if="viewEditor">
      <ViewProperties
        :view="viewEditor.view"
        @close="closeViewEditor"
        @confirm="onViewConfirm"
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
export default {
  name: 'Desktop',
  components: {
    ...ALL_COMPONENTS,
    groupHeaderActions: GroupHeaderActions
  },
  data() {
    return {
      failedPanels: [],
      panelErrorTimeout: null
    }
  },
  computed: {
    apps() {
      const { openApps } = this.$ui
      return Object.values(openApps)
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
    apps() {
      this.syncPanelsWithApps()
    },
    uiReady() {
      this.restoreLayout()
    }
  },
  methods: {
    closeViewEditor() {
      this.$storex.ui.closeViewEditor()
    },
    async onViewConfirm(viewName) {
      if (!viewName) return
      try {
        await this.$storex.views.saveView(viewName)
      } catch (e) {
        console.error('Failed to save view:', e)
      }
      this.closeViewEditor()
    },
    syncPanelsWithApps() {
      this.$storex.views.syncPanelsWithApps()
    },
    onReady(event) {
      this.$storex.views.setDesktopApi(event.api)
      this.restoreLayout()
    },
    onPanelError(event) {
      const panelId = event?.panelId || event?.id
      const panelTitle = this.getPanelTitle(panelId)
      console.error(`Panel error (${panelId}):`, event)
      this.handlePanelError(panelTitle || panelId)
      this.$storex.views.removePanelFromDesktop(panelId)
    },
    handlePanelError(displayName) {
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
        const desktopApi = this.$storex.views._desktopApi
        const panel = desktopApi?.getPanel(panelId)
        return panel?.title || panelId
      } catch (e) {
        return panelId
      }
    },
    async restoreLayout() {
      if (!this.$storex.views._desktopApi || !this.uiReady) return
      try {
        await this.$storex.views.restoreProjectLayout(this.$storex.views._desktopApi)
      } catch (e) {
        console.warn('Failed to restore layout:', e)
      }
    },
    getLayout() {
      return this.$storex.views._desktopApi?.toJSON() || null
    }
  },
  expose: [
    'restoreLayout',
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