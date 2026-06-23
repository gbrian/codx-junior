<script setup>
import AppWindow from '@/components/windowManager/AppWindow.vue'
</script>

<template>
  <div class="flex flex-col h-full w-full">
    <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 border-b border-base-content/10 shrink-0">
      <i class="fa-solid fa-display text-success text-sm"></i>
      <span class="text-sm font-bold grow">Preview</span>
      <select
        class="select select-xs select-bordered max-w-[180px]"
        :value="selectedAppKey"
        @change="onAppChange">
        <option value="">-- Select workspace app --</option>
        <option v-for="app in projectApps" :key="app.key" :value="app.key">
          {{ app.workspaceName }} / {{ app.name }}
        </option>
      </select>
      <button class="btn btn-xs btn-ghost" @click="$emit('reload')" title="Reload preview">
        <i class="fa-solid fa-rotate-right"></i>
      </button>
      <button v-if="selectedApp" class="btn btn-xs btn-ghost" @click="$emit('open-fullscreen')" title="Fullscreen">
        <i class="fa-solid fa-expand"></i>
      </button>
    </div>

    <div v-if="selectedApp?.app" :key="selectedAppKey" class="grow min-h-0 relative overflow-hidden bg-base-100">
      <AppWindow :app="selectedApp.app" class="w-full h-full" />
    </div>

    <div v-else class="grow flex flex-col items-center justify-center gap-3 text-base-content/30">
      <i class="fa-solid fa-display text-5xl"></i>
      <span class="text-sm">Select a workspace app to preview</span>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    selectedApp: { type: Object, default: null },
    projectApps: { type: Array, default: () => [] },
    fullHeight: { type: Boolean, default: false }
  },
  emits: ['app-selected', 'reload', 'open-fullscreen'],
  data() {
    return {
      selectedAppKey: ''
    }
  },
  watch: {
    selectedApp(newVal) {
      if (newVal?.key) {
        this.selectedAppKey = newVal.key
      }
    }
  },
  methods: {
    onAppChange(e) {
      this.selectedAppKey = e.target.value
      this.$emit('app-selected', this.selectedAppKey)
    }
  }
}
</script>