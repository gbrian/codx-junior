<script setup>
</script>

<template>
<div class="w-full h-full flex flex-col gap-2">
  <div v-for="file in parsedDiff" :key="file.path">
    <div clas="flex gap-2">
      <div class="cursor-pointer" @click.stop="toggleExpanded(file)">
        {{ file.path }}
        <button class="btn btn-sm">
          <i class="fa-solid fa-caret-up" v-if="expandedFiles[file.path]"></i>
          <i class="fa-solid fa-caret-down" v-else></i>
        </button>
      </div>
    </div>
    <div>
      <markdown :text="file.diff" v-if="expandedFiles[file.path]"></markdown>
    </div>
  </div>
</div>
</template>

<script>
export default {
  props:['diff'],
  data () {
    return {
      expandedFiles: {}
    }
  },
  computed: {
    parsedDiff() {
      return this.parseDiff(this.diff)
    }
  },
  methods: {
    toggleExpanded(file) {
      if (this.expandedFiles[file.path]) {
        this.expandedFiles[file.path] = false
      } else {
        this.expandedFiles[file.path] = true
      }
    },
    parseDiff(diffData) {
      const files = {}
      let lastFile = null
      const lines = diffData.split('\n')
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const match = line.match(/^diff --git a\/([^ ]+)/)
        if (match) {
          lastFile = match[1]
          files[lastFile] = { path: lastFile, diff: '' }
        }
        if (lastFile) {
          files[lastFile].diff += line + '\n'
        }
      }
      Object.values(files).forEach(v => {
        v.diff = "```diff\n" + v.diff + "```" 
      })
      return files
    },
    openFile(filePath) {
      this.$ui.ui.coderOpenPath(filePath)
    },
    toggleCollapse(filePath) {
      if (this.collapsedFiles.has(filePath)) {
        this.collapsedFiles.delete(filePath)
      } else {
        this.collapsedFiles.add(filePath)
      }
    },
    isCollapsed(filePath) {
      return this.collapsedFiles.has(filePath)
    }
  }
}
</script>