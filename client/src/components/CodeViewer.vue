<script setup>
import { VueCodeHighlighter } from 'vue-code-highlighter'
import 'vue-code-highlighter/dist/style.css'
import hljs from 'highlight.js';
import DiffViewer from './DiffViewer.vue';
import CodeEditor from 'simple-code-editor'
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex gap-1 click">
      <div class="underline click text-link flex gap-2" v-if="fileName">
        <div class="hover:text-info" @click="$emit('add-file', file)">
          <i class="fa-solid fa-file-arrow-up"></i>  
        </div>
        <div class="hover:text-info" @click="$emit('open-file', file)" :title="file">
          {{ fileName }}
        </div>
        <div class="hover:text-info" @click="$emit('reload-file', file)">
          <i class="fa-solid fa-arrows-rotate"></i>
        </div>
        <div class="hover:text-info" @click="onShowDiff"
          v-if="diffOption !== false"
        >
          <i class="fa-solid fa-code-compare"></i>
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
      <div class="hover:text-info" :class="edit && 'text-warning'" @click="onEdit">
        <i class="fa-solid fa-edit"></i>
      </div>      
      <div class="hover:text-info" @click="saveFile" v-if="canSave">
        <i class="fa-solid fa-floppy-disk"></i>
      </div>
    </div>
    <div @click="runCommand" v-if="isCommand">
      <i class="fa-solid fa-terminal"></i>
    </div>
    <div class="view-code" :style="{ zoom }">
      <DiffViewer :file="file" :orgContent="orgContent" 
        :newContent="code" 
        :diff="diff" 
        v-if="showDiff"></DiffViewer>
      <CodeEditor v-model="edit"
            width="100%"
            :header="false"
            :languages="[[fileLanguage, fileLanguage]]"
            v-if="edit"
          />
      <VueCodeHighlighter :code="code" :lang="fileLanguage" :title="fileName" 
        v-if="!edit && !diff" />
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
  props: ['code', 'language', 'file', 'diff-option', 'file-diff'],
  data() {
    return {
      showDiff: false,
      orgContent: null,
      diff: this.fileDiff,
      zoom: 1,
      edit: false,
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
    },
    fileLanguage() {
      if (!hljs.getLanguage(this.language)) {
        return "markdown"
      }
      return this.language
    },
    canSave() {
      return this.edit || this.file
    }
  },
  methods: {
    applyPatch() {
      this.$projects.applyPatch({ patch: this.code })
    },
    async onShowDiff() {
      if (!this.diff) {
        const { diff, stats } = await this.$storex.api.files.diff({ path: this.file, content: this.code }) 
        this.diff = diff
        this.stats = stats
      }
      this.orgContent = await this.$storex.api.files.read(this.file)
      this.showDiff = !this.showDiff
    },
    saveFile() {
      if (this.edit) {
        this.$emit('edit-message', { orgContent: this.code, newContent: this.edit })
        this.edit = null
      } else { 
        this.$emit('save-file', { file: this.file, content: this.code })
      }
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
    },
    onEdit() {
      if (!this.edit) {
        this.edit = this.code
      } else {
        this.edit = null
      }
    }
  }
}
</script>
<style>
.header-code-highlight {
  display: none !important;
}
</style>
