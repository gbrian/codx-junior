<script setup>
import AppIcon from './AppIcon.vue';
</script>
<template>
    <div class="flex gap-2">
      <div class="tooltip tooltip-top bg-base-100" :data-tip="app.name" 
        :class="['hover:bg-base-100 click relative p-1 shadow rounded-lg border-2 border-b-4 border-slate-500 ',
          `group`,
          $ui.openApps[app.name] ? 'border-b-codx-primary' : 'opacity-80 hover:opacity-100 border-slate-700']"
          v-for="app in projectApps" :key="app.name + app.path" @click.stop="activeAppPanel(app)">
          <a class="px-2 flex justify-center items-center w-full focus:text-orange-500">
              <div class="flex gap-2 items-center">
                  <span class="click" @click.stop="toggleAppPanel(app)" v-if="$ui.openApps[app.name]">
                      <i class="fa-solid fa-caret-right" v-if="$ui.openApps[app.name].left"></i>
                      <i class="fa-solid fa-caret-left" v-else></i>
                  </span>
                  <AppIcon :app="app" />
                  <div class="max-w-10 text-nowrap text-ellipsis overflow-hidden">{{ app.name }}</div>
                  <div class="text-codx-primary" title="close" v-if="$ui.openApps[app.name]"
                      @click.stop="$ui.closeApp(app)">
                      <i class="fa-solid fa-xmark"></i>
                  </div>
              </div>
          </a>
      </div>
    </div>
</template>
<script>
export default {
    computed: {
        projectApps() {
        return this.$storex.api.workspaces?.filter(w => w.project_ids.includes("*") || 
                                w.project_ids.includes(this.$project?.project_id))
                            .reduce((a, w) => a.concat(w.apps.map(a => ({ ...a, workspaceId: w.id }))), [])
                            .sort(a => this.$ui.openApps[a.name] && this.$ui.openApps[a.name].left ? -1: 1)

        }
    },
    methods: {
        toggleAppPanel({ name }) {
            const app = this.$ui.openApps[name]
            this.$ui.showApp({
                ...app,
                left: !app.left,
                ts: new Date().getTime()
            })
        },
        activeAppPanel(app) {
            app = app || this.$ui.openApps[app.name]
            this.$ui.showApp({
                ...app,
                ts: new Date().getTime()
            })
        }
    }
}
</script>