<script setup>
import AppWindow from '@/components/windowManager/AppWindow.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col">
    <!-- No VNC app available -->
    <div
      v-if="!vncApp"
      class="flex-1 flex flex-col items-center justify-center gap-4 text-base-content/50"
    >
      <i class="fa-solid fa-display text-5xl"></i>
      <p class="text-lg font-semibold">No VNC app available</p>
      <p class="text-sm">Enable VNC on a project app to use the browser view</p>
    </div>

    <!-- VNC AppWindow -->
    <div v-else class="w-full h-full">
      <AppWindow :app="vncApp" class="w-full h-full" />
    </div>
  </div>
</template>

<script>
export default {
  props: ['chat'],
  computed: {
    // Find first app that has vnc enabled
    vncApp() {
      return this.$storex.projects.projectApps?.find(app => app.is_vnc) || null
    }
  }
}
</script>