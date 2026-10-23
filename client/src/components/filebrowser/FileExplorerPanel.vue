<script setup>
import FileExplorer from './FileExplorer.vue'
import TabManager from './TabManager.vue'
import VerticalSplitter from '../layout/VerticalSplitter.vue'
</script>

<template>
  <!-- Desktop / landscape: resizable split (tree + open files).
       The right (file) panel is only provided while a file is open, so the
       tree uses the full width when there is nothing to show. -->
  <VerticalSplitter :panels="splitterConfig" v-if="!isSinglePanel">
    <template #left>
      <FileExplorer
        ref="fileExplorer"
        :root-path="rootPath"
        @open="handleFileOpen"
        @createFile="handleCreateFile"
      />
    </template>

    <template #right v-if="hasOpenFiles">
      <TabManager
        class="pr-1"
        ref="tabManager"
        @tab-open="onTabOpen"
        @tabs-empty="onTabsEmpty"
      />
    </template>
  </VerticalSplitter>

  <!-- Mobile / portrait tablet: a single full-width panel (tree OR file).
       Both children stay mounted and are toggled with v-show so the tree
       state and the open tabs are preserved while switching. -->
  <div class="w-full h-full overflow-hidden" v-else>
    <FileExplorer
      v-show="mobileView === 'tree'"
      ref="fileExplorer"
      :root-path="rootPath"
      @open="handleFileOpen"
      @createFile="handleCreateFile"
    />
    <TabManager
      v-show="mobileView === 'file'"
      class="pr-1"
      ref="tabManager"
      @tab-open="onTabOpen"
      @tabs-empty="onTabsEmpty"
    />
  </div>
</template>

<script>
export default {
  name: 'FileExplorerPanel',
  props: ['root-path'],
  data() {
    return {
      // Which panel is visible in single-panel mode: 'tree' | 'file'
      mobileView: 'tree',
      // Whether any file is currently open. When false the file tree takes the
      // full width on every viewport (desktop hides the file panel too).
      hasOpenFiles: false,
      splitterConfig: {
        left: {
          minSize: 15,
          defaultSize: 25,
          collapsible: true
        },
        right: {
          minSize: 15,
          defaultSize: 75,
          collapsible: true
        }
      }
    }
  },
  computed: {
    // Mobile phones and portrait tablets (viewport <= 1024px) use a single,
    // full-width panel; larger / landscape viewports keep the resizable split.
    isSinglePanel() {
      return this.$ui.isMobile
    }
  },
  methods: {
    // Open a new file tab. On desktop the file panel is mounted on demand
    // (see hasOpenFiles), so we wait a tick for the TabManager ref to exist.
    async openTab(tab) {
      this.hasOpenFiles = true
      await this.$nextTick()
      if (this.$refs.tabManager) {
        this.$refs.tabManager.addTab(tab)
      } else {
        // Panel could not mount — keep the tree full width instead of
        // leaving an empty file area on screen.
        this.hasOpenFiles = false
      }
    },
    handleFileOpen(fileData) {
      this.openTab({
        path: fileData.path,
        name: fileData.name
      })
    },
    handleCreateFile(fileData) {
      this.openTab({
        path: fileData.path,
        name: fileData.name,
        isNew: true,
        content: ''
      })
    },
    // A file was opened: on mobile hide the tree and show the file full width
    onTabOpen() {
      this.hasOpenFiles = true
      if (this.isSinglePanel) {
        this.mobileView = 'file'
      }
    },
    // Every tab was closed: back to the full-width file tree
    onTabsEmpty() {
      this.hasOpenFiles = false
      if (this.isSinglePanel) {
        this.mobileView = 'tree'
      }
    }
  }
}
</script>