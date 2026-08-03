<script setup>
import FileViewer from './FileViewer.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col overflow-hidden">
    <!-- Tabs header -->
    <div class="flex items-center gap-1 px-2 py-1 bg-base-200 border-b border-base-300 flex-shrink-0 overflow-x-auto">
      <div
        v-for="tab in tabs"
        :key="tab.id"
        class="flex items-center gap-2 px-3 py-2 rounded-t-lg cursor-pointer transition-colors whitespace-nowrap"
        :class="activeTabId === tab.id
          ? 'bg-base-100 border-b-2 border-blue-500'
          : 'bg-base-300 hover:bg-base-300/80'"
        @click="setActiveTab(tab.id)"
      >
        <i class="fa-regular fa-file text-info text-xs"></i>
        <span class="text-sm font-mono truncate max-w-xs">
          {{ tab.name }}
        </span>
        <button
          class="btn btn-xs btn-ghost btn-circle ml-1"
          @click.stop="closeTab(tab.id)"
          title="Close tab"
        >
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
    </div>

    <!-- Tab content -->
    <div class="grow overflow-hidden">
      <div
        v-for="tab in tabs"
        :key="tab.id"
        class="w-full h-full"
        v-show="activeTabId === tab.id"
      >
        <FileViewer :params="{ filePath: tab.path }" />
      </div>

      <!-- Empty state -->
      <div
        v-if="!tabs.length"
        class="w-full h-full flex items-center justify-center opacity-50 flex-col gap-3"
      >
        <i class="fa-regular fa-folder-open text-3xl"></i>
        <span class="text-sm">Select a file to view</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TabManager',
  data() {
    return {
      tabs: [],
      activeTabId: null,
      nextTabId: 0
    }
  },
  computed: {
    activeTab() {
      return this.tabs.find(t => t.id === this.activeTabId)
    },
    tabCount() {
      return this.tabs.length
    }
  },
  methods: {
    addTab(file) {
      const tabId = `tab-${this.nextTabId++}`
      const tab = {
        id: tabId,
        name: file.name,
        path: file.path,
        openedAt: new Date()
      }
      this.tabs.push(tab)
      this.setActiveTab(tabId)
    },
    closeTab(tabId) {
      const index = this.tabs.findIndex(t => t.id === tabId)
      if (index === -1) return

      this.tabs.splice(index, 1)

      // Switch to adjacent tab or clear active tab
      if (this.activeTabId === tabId) {
        if (this.tabs.length > 0) {
          const nextIndex = index < this.tabs.length ? index : index - 1
          this.setActiveTab(this.tabs[nextIndex].id)
        } else {
          this.activeTabId = null
        }
      }
    },
    closeAllTabs() {
      this.tabs = []
      this.activeTabId = null
    },
    setActiveTab(tabId) {
      this.activeTabId = tabId
    },
    getTab(tabId) {
      return this.tabs.find(t => t.id === tabId)
    },
    getAllTabs() {
      return this.tabs
    },
    hasTab(path) {
      return this.tabs.some(t => t.path === path)
    }
  },
  expose: [
    'addTab',
    'closeTab',
    'closeAllTabs',
    'setActiveTab',
    'getTab',
    'getAllTabs',
    'hasTab'
  ]
}
</script>