<script setup>
import { VueCodeHighlighter } from 'vue-code-highlighter'
import 'vue-code-highlighter/dist/style.css'
import DiffViewer from './DiffViewer.vue'
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex gap-1 click">
      <div class="underline click text-link flex gap-2" v-if="fileName">
        <div class="hover:text-info" @click="$emit('open-file', file)" :title="file">{{ fileName }}</div>
        <div class="hover:text-info" @click="$emit('reload-file', file)">
          <i class="fa-solid fa-file-arrow-up"></i>
        </div>
        <div class="hover:text-info" @click="onShowDiff">
          <i class="fa-solid fa-code-compare"></i>
        </div>
        <div class="hover:text-info" @click="saveFile" v-if="$user.role === 'admin'">
          <i class="fa-solid fa-floppy-disk"></i>
        </div>
      </div>
      <div class="hover:text-info" @click="zoomOut">
        <i class="fa-solid fa-magnifying-glass-minus"></i>
      </div>
      <div class="hover:text-info" @click="zoomIn">
        <i class="fa-solid fa-magnifying-glass-plus"></i>
      </div>
      <div class="hover:text-info" @click="onCopy">
        <i class="fa-solid fa-copy"></i>
      </div>      
    </div>
    <div @click="runCommand" v-if="isCommand">
      <i class="fa-solid fa-terminal"></i>
    </div>
    <div class="view-code" :style="{ zoom }">
      <VueCodeHighlighter :code="diff" :lang="'diff'" :header="false" :title="fileName" v-if="showDiff" />
      <VueCodeHighlighter :code="code" :lang="language" :title="fileName" v-else />
    </div>
    <div class="flex justify-end gap-2">
      <button class="btn btn-sm btn-warning" @click="applyPatch" v-if="isPatch">
        Apply
      </button>
    </div>
  </div>
</template>
<script>
export default {
  props: ['code', 'language', 'file'],
  data() {
    return {
      showDiff: false,
      diff: null,
      zoom: 0.6
    }
  },
  computed: {
    isPatch() {
      return this.language === 'diff'
    },
    fileName() {
      return this.file?.split("/").reverse()[0]
    },  
    isCommand() {
      return this.language === "bash"
    }
  },
  methods: {
    applyPatch() {
      this.$projects.applyPatch({ patch: this.code })
    },
    async onShowDiff() {
      if (!this.diff) {
        this.diff = await this.$storex.api.files.diff({ path: this.file, content: this.code })
      }
      this.showDiff = !this.showDiff
    },
    saveFile() {
      this.$emit('save-file', { file: this.file, content: this.code })
    },
    runCommand() {
      this.$storex.api.apps.runScript(this.code)
    },
    zoomOut() {
      this.zoom -= .1
    },
    zoomIn() {
      this.zoom += .1
    },
    onCopy() {
      this.$ui.copyTextToClipboard(this.code)
    }
  }
}
</script>
<style>
.header-code-highlight {
  display: none !important;
}
</style>
