<script setup>
import MenubarSub from './MenubarSub.vue'
import MenubarItem from './MenubarItem.vue';
import ProjectLabel from './ProjectLabel.vue';
import ProjectDetailt from '../ProjectDetailt.vue';
</script>
<template>
  <MenubarSub>
    <template v-slot:menubaritem>
      <ProjectLabel :project="$project" />
    </template>
    <div class="font-bold px-2 hover:bg-base-300">
      {{ $project.project_name }}
    </div>
    
    <div class="divider"></div>
    <MenubarItem class="flex gap-2 hover:bg-base-300"
      @click="$ui.setActiveTab('settings')"
    >
      Project settings
    </MenubarItem>
  </MenubarSub>
</template>
<script>
export default {
  computed: {
    topLevelProjects() {
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