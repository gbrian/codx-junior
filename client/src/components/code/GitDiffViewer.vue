<script setup>
import Code from '../Code.vue'
import MarkdownViewer from '../MarkdownViewer.vue';
</script>

<template>
<div class="w-full flex flex-col gap-2 overflow-auto">
  <div class="relative" v-for="file in parsedDiff" :key="file.path">
    <div clas="flex gap-2 relative">
      <div class="click sticky top-0 hover:underline" @click="openFile(file)">
        <button class="btn btn-sm" @click.stop="toggleExpanded(file)">
          <i class="fa-solid fa-caret-up" v-if="!expandedFiles[file.path]"></i>
          <i class="fa-solid fa-caret-down" v-else></i>
        </button>
        {{ file.path }}
      </div>
    </div>
    <div>
      <Code :text="diffText(file.diff)" :text-language="'diff'" v-if="false && expandedFiles[file.path]"></Code>
      <MarkdownViewer :text="file.diff" v-if="expandedFiles[file.path]"/>
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
  created () {
    const parsedDiff = this.parsedDiff
    Object.keys(parsedDiff)
      .slice(0, 5).forEach(k => this.toggleExpanded(parsedDiff[k]))
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
    diffText(diff) {
      const lines = diff.split("\n")
      return lines.slice(1, lines.length - 2).join("\n")
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
      if (this.expandedFiles.has(filePath)) {
        this.expandedFiles.delete(filePath)
      } else {
        this.expandedFiles.add(filePath)
      }
    },
    isCollapsed(filePath) {
      return this.expandedFiles.has(filePath)
    }
  }
}
</script>