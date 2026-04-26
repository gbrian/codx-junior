<script setup>
import MenubarSub from './MenubarSub.vue'
import MenubarItem from './MenubarItem.vue';
</script>
<template>
  <MenubarSub title="Settings">
    <div class="font-bold px-2 hover:bg-base-300">
      Settings
    </div>
    <MenubarItem class="flex gap-2 hover:bg-base-300"
      
    >
      Project settings
    </MenubarItem>
    <MenubarItem class="flex gap-2 hover:bg-base-300">
      Global settings
    </MenubarItem>
    <MenubarItem class="flex gap-2 hover:bg-base-300" v-if="$ui.isMobile" @click="showEruda">
      Mobile console
    </MenubarItem>
  </MenubarSub>
</template>
<script>
export default {
  computed: {
    workspaces() {
      return this.$storex.projects.projectApps.reduce((acc, app) => {
        const apps = acc[app.workspaceName] || []
        apps.push(app)
        return {
          ...acc,
          [app.workspaceName]: apps
        }        
      }, {})
    }
  },
  methods: {
    toggleAppPanel(app) {
      app = this.$ui.openApps[app.key] || app
      this.$ui.showApp({
          ...app,
          left: !app?.left,
          ts: new Date().getTime()
      })
    },
    showEruda() {
      window.eruda.init()
    }
  }
}
</script>