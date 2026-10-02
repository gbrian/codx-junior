<script setup>
import FileExplorerPanel from '../filebrowser/FileExplorerPanel.vue'
</script>

<template>
  <FileExplorerPanel :root-path="rootPath" />
</template>

<script>
export default {
  props: {
    workspace: Object,
  },
  computed: {
    rootPath() {
      return this.workspace.folder_path
    }
  }
}
</script>