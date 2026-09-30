<script setup>
</script>

<template>
  <div v-if="hasWorkspaceApps" class="px-2 py-3 shrink-0 border-b border-base-content/5">
    <button
      v-if="!isCollapsed"
      class="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-base-content/60 hover:text-base-content/80 transition-colors"
      @click="workspacesExpanded = !workspacesExpanded"
      title="Toggle Workspaces"
    >
      <span>WORKSPACES</span>
      <i :class="workspacesExpanded ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'" class="text-xs"></i>
    </button>
    <div v-if="workspacesExpanded || isCollapsed" class="flex flex-col gap-1">
      <button
        v-for="app in workspaceApps"
        :key="app.id"
        class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-base-content/80 hover:bg-white/8 hover: transition-colors text-left w-full"
        :class="[
          isWorkspaceSelected(app.id) ? 'bg-white/10 ' : '',
          isCollapsed ? 'justify-center' : ''
        ]"
        :title="isCollapsed ? app.name : ''"
        @click="handleSelectWorkspaceApp(app)"
      >
        <i v-if="app.icon" :class="app.icon" class="w-5 text-center shrink-0"></i>
        <i v-else class="fa-solid fa-play w-5 text-center shrink-0"></i>
        <span v-if="!isCollapsed">{{ app.name }}</span>
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
    },
    navigation() {
      return this.$storex.$router.$navigation
    }
  },
  methods: {
    handleSelectWorkspaceApp(app) {
      app = this.$ui.openApps[app.key] || app
      this.$ui.showApp({
        ...app,
        left: !app?.left,
        ts: new Date().getTime(),
        params: {
          name: app.name,
          path: app.path
        }
      })
    },
    isWorkspaceSelected(workspaceId) {
      return this.navigation.getWorkspaceId() === workspaceId
    }
  }
}
</script>