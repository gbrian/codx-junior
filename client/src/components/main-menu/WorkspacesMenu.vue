<script setup>
import MenubarSub from './MenubarSub.vue'
import MenubarItem from './MenubarItem.vue';
import AppIcon from '../apps/AppIcon.vue';
</script>
<template>
  <MenubarSub title="Workspaces">
    <template v-slot:menubaritem>
      <i class="fa-solid fa-server"></i>
      Workspaces
    </template>
    <div class="font-bold px-2 hover:bg-base-300">
      Workspaces
    </div>
    <MenubarSub :title="workspaceName" v-for="apps, workspaceName in workspaces" :key="workspaceName">
      <div class="font-bold px-2">Apps</div>
        
      <MenubarItem class="flex gap-2 hover:bg-base-300" v-for="app in apps" :key="app.name"
        @click.stop="toggleAppPanel(app)"
      >
        <AppIcon :app="app" />
        {{ app.name }}
        <button class="btn btn-sm" @click="$ui.openNewWindowAppPanel(app)">
          <i class="fa-solid fa-arrow-up-right-from-square"></i>
        </button>
      </MenubarItem>
    </MenubarSub>
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
    }
  }
}
</script>