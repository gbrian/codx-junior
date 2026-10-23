<script setup>
import BrowserSessionList from './BrowserSessionList.vue'
import BrowserSessionPanel from './BrowserSessionPanel.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col">
    <!-- Mobile: Toggle Header -->
    <div v-if="isMobile" class="flex items-center gap-2 p-3 border-b border-base-content/10 bg-base-200">
      <button
        v-if="selectedSessionId"
        @click="clearSelection"
        class="btn btn-sm btn-ghost btn-circle"
        title="Back to list"
      >
        <i class="fa-solid fa-arrow-left"></i>
      </button>
      <h1 class="text-lg font-bold flex-1">Browser Sessions</h1>
    </div>

    <!-- Main Content -->
    <div v-if="!isMobile" class="flex flex-1 gap-4 p-4 overflow-hidden bg-base-100">
      <!-- Desktop: Side-by-side layout -->
      <div class="w-80 border border-base-content/10 rounded-lg overflow-hidden flex flex-col bg-base-100">
        <BrowserSessionList />
      </div>
      <div class="flex-1 border border-base-content/10 rounded-lg overflow-hidden flex flex-col bg-base-100">
        <BrowserSessionPanel />
      </div>
    </div>

    <!-- Mobile: Single column -->
    <div v-else class="flex-1 overflow-hidden flex flex-col">
      <Transition
        name="fade-slide"
        mode="out-in"
      >
        <div v-if="showList" key="list" class="flex-1 overflow-hidden">
          <BrowserSessionList />
        </div>
        <div v-else-if="showPanel" key="panel" class="flex-1 overflow-hidden">
          <BrowserSessionPanel />
        </div>
      </Transition>
    </div>
  </div>
</template>
<script>
export default {
  name: 'BrowsersSessionManager',
  components: {
    BrowserSessionList,
    BrowserSessionPanel
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
  methods: {
    clearSelection() {
      this.$storex.browsers.clearSelection()
    }
  },
  inject: ['$storex']
}
</script>
<style scoped>
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(30px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}
</style>
