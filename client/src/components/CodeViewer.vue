<script setup>
import { VueCodeHighlighter } from 'vue-code-highlighter'
import 'vue-code-highlighter/dist/style.css'
import DiffViewer from './DiffViewer.vue'
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="underline click text-link flex gap-2" v-if="fileName">
      <div @click="$ui.openFile(file)">{{ fileName }}</div>
      <div @click="onShowDiff">
        <i class="fa-solid fa-code-compare"></i>
      </div>
      <div @click="saveFile">
        <i class="fa-solid fa-floppy-disk"></i>
      </div>
    </div>
    <div @click="runCommand" v-if="isCommand">
      <i class="fa-solid fa-terminal"></i>
    </div>
    <div class="view-code">
      <VueCodeHighlighter :code="diff" :lang="'diff'" :title="fileName" v-if="showDiff" />
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
      diff: null
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
      this.$storex.api.files.write(this.file, this.code)
    },
    runCommand() {
      this.$storex.api.apps.runScript(this.code)
    }
  }
}
</script>
