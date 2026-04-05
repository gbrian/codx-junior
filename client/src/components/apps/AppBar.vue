<script setup>
import AppIcon from './AppIcon.vue';
</script>
<template>
    <div class="flex gap-2">
      <div class="tooltip tooltip-top bg-base-100 click" 
        :data-tip="`${app.workspaceName} / ${app.name}`" 
        :class="['hover:bg-base-100 click relative p-1 shadow rounded-lg border-2 border-b-4 border-slate-500 ',
          `group`,
          $ui.openApps[app.key] ? 'border-b-codx-primary' : 'opacity-80 hover:opacity-100 border-slate-700']"
          v-for="app in $ui.activeApps" :key="app.name + app.path" 
          @click.stop="activeAppPanel(app)"
          @click.ctrl="openNewWindowAppPanel(app)" 
          >
          <a class="px-2 flex justify-center items-center w-full focus:text-orange-500">
            <AppIcon :app="app" />
          </a>
      </div>
    </div>
</template>
<script>
export default {
    methods: {
        toggleAppPanel({ key }) {
            const app = this.$ui.openApps[key]
            this.$ui.showApp({
                ...app,
                left: !app.left,
                ts: new Date().getTime()
            })
        },
        openNewWindowAppPanel(app) {
          const { origin } = window.location
          const url = `${origin}${app.path}`
          window.open(url, app.name)
        },
        activeAppPanel(app) {
          app = app || this.$ui.openApps[app.key]
          this.$ui.showApp({
              ...app,
              ts: new Date().getTime()
          })
        }
    }
}
</script>