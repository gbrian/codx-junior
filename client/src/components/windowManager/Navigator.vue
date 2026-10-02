<script setup>
import VerticalSplitterVue from '../layout/VerticalSplitter.vue'
import AppWindowVue from './AppWindow.vue'
</script>
<template>
  <VerticalSplitterVue class="w-full h-full relative" 
      :panels="{ left: { defaultSize: 60 }, right: { defaultSize: 40 } }"
    >
      <template v-slot:left v-if="leftWindows.length">
        <AppWindowVue v-for="app, ix in leftWindows" :key="app.path"
          :app="app"
          class=""
          :class="[
            app === ix ? 'z-0': 'z-10',
            `app-${encodeURIComponent(app.name)}`
          ]"
        >
        </AppWindowVue>
      </template>
      <template v-slot:right v-if="rightWindows.length">
        <AppWindowVue v-for="app, ix in rightWindows" :key="app.path"
          :app="app"
          class=""
          :class="[
            app === ix ? 'z-0': 'z-10',
            `app-${encodeURIComponent(app.name)}`
          ]"
        >
        </AppWindowVue>
      </template>
  </VerticalSplitterVue> 
</template>
<script>
    export default {
      computed: {
        apps() {
          return Object.values(this.$ui.openApps || {})
                  .sort((a, b) => (a.ts||0) > (b.ts||0) ? -1 : 1)
        },
        leftWindows() {
          return this.apps.filter(a => a.left)
        },
        rightWindows() {
          return this.apps.filter(a => !a.left)
        }
      }
    }
</script>