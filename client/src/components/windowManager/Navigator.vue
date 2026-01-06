<script setup>
import AppWindowVue from './AppWindow.vue'
</script>
<template>
  <div class="w-full h-full relative">
    <AppWindowVue v-for="app in $ui.openApps" :key="app.path"
      :app="app"
      class="absolute top-0 left-0 right-0 bottom-0"
      :class="app === $ui.activeApp ? 'z-10': 'z-0'"
    >
    </AppWindowVue>
  </div>
</template>
<script>
    export default {
    }
</script>