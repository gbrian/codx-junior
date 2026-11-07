<script setup>
import BrowserSessionList from './BrowserSessionList.vue'
import BrowserSessionPanel from './BrowserSessionPanel.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col bg-base-100">
    <!-- Mobile: Toggle Header -->
    <div v-if="isMobile" class="flex items-center gap-2 p-3 border-b border-base-content/10 bg-base-200">
      <button
        v-if="selectedSessionId"
        @click="clearSelection"
        class="btn btn-sm btn-ghost btn-circle"
        title="Back to list"
        aria-label="Back to session list"
      >
        <i class="fa-solid fa-arrow-left"></i>
      </button>
      <h1 class="text-lg font-bold flex-1">Browser Sessions</h1>
    </div>

    <!-- Desktop: fixed-width sidebar (collapsed rail or expanded list) + panel -->
    <div v-if="!isMobile" class="flex flex-1 min-h-0 gap-3 p-3 overflow-hidden">
      <aside
        class="flex-shrink-0 flex flex-col rounded-2xl border border-base-content/10 bg-base-100 shadow-sm overflow-hidden transition-[width] duration-200 ease-out"
        :class="sidebarCollapsed ? 'w-[68px]' : 'w-80'"
      >
        <BrowserSessionList :collapsed="sidebarCollapsed" @toggle-collapse="toggleSidebar" />
      </aside>
      <section class="flex-1 min-w-0 rounded-2xl border border-base-content/10 bg-base-100 shadow-sm overflow-hidden flex flex-col">
        <BrowserSessionPanel />
      </section>
    </div>

    <!-- Mobile: Single column -->
    <div v-else class="flex-1 overflow-hidden flex flex-col">
      <Transition
        mode="out-in"
        enter-active-class="transition-all duration-300 ease-out"
        enter-from-class="opacity-0 translate-x-6"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="transition-all duration-300 ease-out"
        leave-from-class="opacity-100 translate-x-0"
        leave-to-class="opacity-0 -translate-x-6"
      >
        <div v-if="showList" key="list" class="flex-1 overflow-hidden">
          <BrowserSessionList :collapsed="false" />
        </div>
        <div v-else key="panel" class="flex-1 overflow-hidden">
          <BrowserSessionPanel />
        </div>
      </Transition>
    </div>
  </div>
</template>
<script>
const SIDEBAR_STATE_KEY = 'codx.browsers.sidebarCollapsed'

export default {
  name: 'BrowsersSessionManager',
  components: {
    BrowserSessionList,
    BrowserSessionPanel
  },
  data() {
    return {
      sidebarCollapsed: false
    }
  },
  computed: {
    isMobile() {
      return this.$storex.ui.isMobile
    },
    selectedSessionId() {
      return this.$storex.browsers.selectedSessionId
    },
    showList() {
      if (this.isMobile) {
        return !this.selectedSessionId
      }
      return true
    },
    showPanel() {
      if (this.isMobile) {
        return !!this.selectedSessionId
      }
      return true
    }
  },
  watch: {
    sidebarCollapsed(value) {
      this.saveSidebarState(value)
    }
  },
  methods: {
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
    },
    clearSelection() {
      this.$storex.browsers.clearSelection()
    },
    loadSidebarState() {
      try {
        return window.localStorage.getItem(SIDEBAR_STATE_KEY) === 'true'
      } catch (error) {
        return false
      }
    },
    saveSidebarState(value) {
      try {
        window.localStorage.setItem(SIDEBAR_STATE_KEY, value ? 'true' : 'false')
      } catch (error) {
        // localStorage not available
      }
    }
  },
  mounted() {
    this.sidebarCollapsed = this.loadSidebarState()
  },
  inject: ['$storex']
}
</script>