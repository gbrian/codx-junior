<script setup>
</script>

<template>
  <div v-if="hasWorkspaceApps" class="flex flex-col gap-1.5">
    <!-- Dropdown (when collapsed) -->
    <div class="dropdown dropdown-bottom dropdown-right w-full">
      <button
        tabindex="0"
        role="button"
        class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-white/80 hover:bg-white/8 hover:text-white transition-colors text-left w-full"
        :class="isCollapsed ? 'justify-center' : ''"
        :title="isCollapsed ? 'Workspaces' : ''"
      >
        <i class="fa-solid fa-play w-5 text-center shrink-0"></i>
        <span v-if="!isCollapsed">Workspaces</span>
      </button>
      <ul tabindex="-1" class="dropdown-content z-10 menu p-2 shadow bg-base-100 rounded-box w-52">
        <li v-for="app in workspaceApps" :key="app.name">
          <a @click="selectApp(app)" :class="isSelected(app) ? 'active' : ''">
            <i v-if="app.icon" :class="app.icon" class="mr-2"></i>
            {{ app.name }}
          </a>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    isCollapsed: { type: Boolean, default: false },
    selectedApp: { type: Object, default: null },
    workspaceApps: { type: Array, default: () => [] }
  },
  emits: ['select-app'],
  computed: {
    hasWorkspaceApps() {
      return this.workspaceApps && this.workspaceApps.length > 0
    }
  },
  methods: {
    selectApp(app) {
      this.$emit('select-app', app)
    },
    isSelected(app) {
      return this.selectedApp?.name === app.name
    }
  }
}
</script>