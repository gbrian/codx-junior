<script setup>
</script>

<template>
<div class="w-full flex flex-col gap-2 overflow-auto">
  <div class="relative" v-for="file in parsedDiff" :key="file.path">
    <div clas="flex gap-2 relative">
      <div class="click sticky top-0 hover:underline" @click="openFile(file)">
        <button class="btn btn-sm" @click.stop="toggleExpanded(file)">
          <i class="fa-solid fa-caret-up" v-if="!collapsedFiles[file.path]"></i>
          <i class="fa-solid fa-caret-down" v-else></i>
        </button>
        {{ file.path }}
      </div>
    </div>
    <div>
      <markdown :text="file.diff" v-if="!collapsedFiles[file.path]"></markdown>
    </div>
  </div>
</div>
</template>

<script>
export default {
  props:['diff'],
  data () {
    return {
      collapsedFiles: {}
    }
  },
  computed: {
    parsedDiff() {
      return this.parseDiff(this.diff)
    }
  },
  methods: {
    toggleExpanded(file) {
      if (this.collapsedFiles[file.path]) {
        this.collapsedFiles[file.path] = false
      } else {
        this.collapsedFiles[file.path] = true
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
    openFile(file) {
      const filePath = `${this.$project.project_path}/${file.path}`
      this.$ui.openFile(filePath)
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