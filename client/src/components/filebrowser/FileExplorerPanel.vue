<script setup>
import FileExplorer from './FileExplorer.vue'
import TabManager from './TabManager.vue'
import VerticalSplitter from '../layout/VerticalSplitter.vue'
</script>

<template>
  <VerticalSplitter :panels="splitterConfig">
    <template #left>
      <FileExplorer
        ref="fileExplorer"
        :root-path="rootPath"
        @open="handleFileOpen"
        @createFile="handleCreateFile"
      />
    </template>

    <template #right>
      <TabManager class="pr-1" ref="tabManager" />
    </template>
  </VerticalSplitter>
</template>

<script>
export default {
  name: 'FileExplorerPanel',
  props: ['root-path'],
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
    },
    handleCreateFile(fileData) {
      this.$refs.tabManager.addTab({
        path: fileData.path,
        name: fileData.name,
        isNew: true,
        content: ''
      })
    }
  }
}
</script>