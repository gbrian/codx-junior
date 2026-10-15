<script setup>
</script>

<template>
  <div v-if="hasWorkspaceApps" class="px-2 py-3 shrink-0 border-b border-base-content/5">
    <!-- Section Header (Desktop Only) -->
    <button
      v-if="!isCollapsed"
      class="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-base-content/60 hover:text-base-content/80 transition-colors"
      @click="workspacesExpanded = !workspacesExpanded"
      title="Toggle Workspaces"
    >
      <span>WORKSPACES</span>
      <i :class="workspacesExpanded ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'" class="text-xs"></i>
    </button>

    <!-- Workspace Apps List -->
    <div 
      v-if="workspacesExpanded || isCollapsed" 
      class="flex flex-col gap-1"
      :class="isCollapsed ? 'justify-center items-center' : ''"
    >
      <!-- Empty State on Mobile -->
      <div 
        v-if="isCollapsed && workspaceApps.length === 0" 
        class="text-center text-xs text-base-content/40 py-2"
      >
        <i class="fa-solid fa-cube text-sm block mb-1"></i>
        <span class="text-[10px]">No workspaces</span>
      </div>

      <!-- Workspace Apps -->
      <button
        v-for="app in workspaceApps"
        :key="app.id"
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-base-content/80 hover:bg-white/8 hover:text-base-content transition-colors text-left"
        :class="[
          isWorkspaceAppSelected(app.id) ? 'bg-white/10 text-base-content' : '',
          isCollapsed ? 'justify-center px-2' : 'w-full'
        ]"
        :title="isCollapsed ? app.name : ''"
        @click="handleSelectWorkspaceApp(app)"
      >
        <i v-if="app.icon" :class="app.icon" class="w-5 text-center shrink-0"></i>
        <i v-else class="fa-solid fa-cube w-5 text-center shrink-0"></i>
        <span v-if="!isCollapsed" class="truncate min-w-0">{{ app.name }}</span>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    workspaceApps: { type: Array, default: () => [] },
    isCollapsed: { type: Boolean, default: false },
    currentWorkspaceId: { type: String, default: null }
  },
  data() {
    return {
      workspacesExpanded: false
    }
  },
  computed: {
    hasWorkspaceApps() {
      return this.workspaceApps && this.workspaceApps.length > 0
    }
  },
  watch: {
    isCollapsed(newVal) {
      // On mobile (collapsed), always show the list
      if (newVal) {
        this.workspacesExpanded = true
      }
    }
  },
  methods: {
    handleSelectWorkspaceApp(app) {
      this.$ui.openWorkspace(app)
    },
    isWorkspaceAppSelected(workspaceId) {
      return this.$router.$navigation.getWorkspaceId() === workspaceId
    }
  }
}
</script>