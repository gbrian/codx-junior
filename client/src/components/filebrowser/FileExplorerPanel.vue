<script setup>
import FileExplorer from './FileExplorer.vue'
import TabManager from './TabManager.vue'
import VerticalSplitter from '../layout/VerticalSplitter.vue'
</script>

<template>
  <VerticalSplitter :panels="splitterConfig">
    <template #left>
      <FileExplorer @open="handleFileOpen" />
    </template>

    <template #right>
      <TabManager class="pr-1" ref="tabManager" />
    </template>
  </VerticalSplitter>
</template>

<script>
export default {
  name: 'FileExplorerPanel',
  data() {
    return {
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
  methods: {
    handleFileOpen(fileData) {
      this.$refs.tabManager.addTab({
        path: fileData.path,
        name: fileData.name
      })
    }
  }
}
</script>