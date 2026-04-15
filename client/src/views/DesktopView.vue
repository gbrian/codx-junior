<script setup>
import Desktop from '@/components/desktop/Desktop.vue'
</script>
<template>
  <div class="w-full h-full @container group-codxjunior">
    <Desktop
      :panels="panels"
      @ready="onDesktopReady"
      ref="desktop"
    />
  </div>
</template>
<script>
export default {
  name: 'DesktopView',
  data() {
    return {
      panelsApi: null,
      panels: []
    }
  },
  computed: {
    apps() {
      return Object.values(this.$ui.openApps)
    },
    appKeys() {
      return this.apps.map(({ key }) => key)
    },
    panelKeys() {
      return this.panels.map(({ id }) => id)
    }
  },
  watch: {
    apps(newVal) {
      const { panelKeys } = this      
      newVal
        .filter(({ key }) => !panelKeys.includes(key))
        .forEach(app => this.addAppPanel(app));
    }
  },
  methods: {
    onDesktopReady({ api }) {
      this.panelsApi = api
      this.panelsApi.onDidAddPanel(this.onDidAddPanel.bind(this))
      this.panelsApi.onDidRemovePanel(this.onDidRemovePanel.bind(this))
      this.apps.forEach(app => this.addAppPanel(app))
    },
    addAppPanel(app) {
      this.panelsApi.addPanel({ 
                            id: app.key,
                            title: app.name,
                            component: app.component || 'app-window', 
                            params: {
                              ...app.params || {},
                              app
                            }
                          })
    },
    onDidAddPanel(panel) {
      this.panels.push(panel)
    },
    onDidRemovePanel(panel) {
      this.$ui.closeApp(panel.params.app)
      this.panels = this.panels.filter(p => p !== panel)
    }
  }
}
</script>