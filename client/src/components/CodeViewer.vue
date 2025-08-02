<script setup>
import { VueCodeHighlighter } from 'vue-code-highlighter'
import 'vue-code-highlighter/dist/style.css'
import DiffViewer from './DiffViewer.vue'
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="underline click text-link flex gap-2" v-if="fileName">
      <div @click="$ui.openFile(file)">{{ fileName }}</div>
      <div @click="onShowDiff"><i class="fa-solid fa-code-compare"></i></div>
    </div>
    <VueCodeHighlighter :code="diff" :lang="'diff'" :title="fileName" v-if="showDiff" />
    <VueCodeHighlighter :code="code" :lang="language" :title="fileName" v-else />
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
    }
  }
}
</script>

<style scoped>
.pre .code {
  font-size: 8px !important;
}
</style>
