<script setup>
import { VueCodeHighlighter } from 'vue-code-highlighter'
import 'vue-code-highlighter/dist/style.css'
import hljs from 'highlight.js';
import DiffViewer from './DiffViewer.vue';
import Editor from './monaco/Editor.vue';
import Collapsible from './Collapsible.vue';
</script>

<template>
  <Collapsible :default-open="showCode">
    <!-- Icon slot: streaming/done indicator -->
    <template #icon>
      <i class="fa-solid fa-check-double text-success" v-if="finished"></i>
      <span class="loading loading-spinner loading-xs" v-else-if="isStreaming"></span>
      <i class="fa-solid fa-code text-xs opacity-60" v-else></i>
    </template>

    <!-- Title slot: file name always visible -->
    <template #title>
      <div class="flex gap-2 items-center">
        <div class="underline text-link flex gap-2 items-center cursor-pointer" v-if="fileName">
          <div class="hover:text-info" @click.stop="$emit('add-file', file)">
            <i class="fa-solid fa-file-arrow-up"></i>
          </div>
          <div class="hover:text-info tooltip" :data-tip="file"
            @click.stop="$emit('open-file', file)">
            {{ fileName }}
          </div>
        </div>
        <span class="text-sm font-medium opacity-60" v-else>Code</span>
        <div class="hover:text-info cursor-pointer" @click.stop="zoomOut">
          <i class="fa-solid fa-magnifying-glass-minus"></i>
        </div>
        <div class="hover:text-info cursor-pointer" @click.stop="zoomIn">
          <i class="fa-solid fa-magnifying-glass-plus"></i>
        </div>
        <div class="hover:text-info cursor-pointer" @click.stop="onCopy">
          <i class="fa-solid fa-copy"></i>
        </div>
        <div class="hover:text-info cursor-pointer" :class="edit && 'text-warning'" @click.stop="onEdit">
          <i class="fa-solid fa-edit"></i>
        </div>
        <div class="hover:text-info cursor-pointer" @click.stop="saveFile" v-if="canSave">
          <i class="fa-solid fa-floppy-disk"></i>
        </div>
        <div class="hover:text-info cursor-pointer" @click.stop="createSubTask">
          <i class="fa-brands fa-trello"></i>
        </div>
        <span class="text-xs text-info">
          <span v-if="loadingStats">Loading...</span>
          <span @click.stop="onShowDiff" class="cursor-pointer" v-if="stats">
            <i class="fa-solid fa-file-lines" v-if="showDiff"></i>
            <i class="fa-solid fa-code-compare" v-else></i>
            {{ stats }}
          </span>
        </span>
      </div>
    </template>

    <!-- Default slot: only the code area collapses -->
    <div class="flex flex-col gap-2 p-2">
      <!-- Run command button -->
      <div @click="runCommand" class="cursor-pointer" v-if="isCommand">
        <i class="fa-solid fa-terminal"></i>
      </div>

      <!-- Code display area -->
      <div class="view-code" :style="{ zoom }">
        <DiffViewer :file="file" :orgContent="orgContent" :newContent="code" :language="language"
          :diff="diff" v-if="showDiff" />
        <VueCodeHighlighter :code="code" :lang="fileLanguage" :title="fileName"
          v-if="code && !edit && !showDiff" />
        <Editor v-model="edit" :language="fileLanguage" v-if="edit" />
      </div>

      <!-- Footer actions -->
      <div class="flex justify-end gap-2">
        <button class="btn btn-sm btn-warning" @click="applyPatch" v-if="isPatch">
          Apply
        </button>
      </div>
    </div>
  </Collapsible>
</template>

<script>
export default {
  props: ['chat', 'code', 'language', 'file', 'diff-option', 'file-diff', 'files', 'project', 'finished'],
  data() {
    return {
      showDiff: false,
      orgContent: null,
      diff: this.fileDiff,
      zoom: 1,
      edit: null,
      loadingStats: false,
      stats: null,
      // open by default, collapsed in vibe mode
      showCode: true,
      prevScrollTop: 0
    }
  },
  computed: {
    isStreaming() {
      return !this.finished && this.code
    },
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
    },
    $api() {
      return (this.project?.$api || this.$storex.api)
    }
  },
  watch: {
    async finished() {
      if (this.finished) {
        await this.loadDiffInfo()
      }
      if (this.chat?.mode === 'vibe') {
        this.saveFile()
      }
    },
    code() {
      this.$nextTick(() => {
        const viewCode = this.$el?.querySelector('.view-code')
        if (viewCode) viewCode.scrollTop = this.prevScrollTop
      })
    }
  },
  mounted() {
    // collapse code by default in vibe mode
    if (this.chat?.mode === 'vibe') {
      this.showCode = false
    }
    if (this.finished) {
      this.loadDiffInfo()
    }
    const viewCode = this.$el?.querySelector('.view-code')
    if (viewCode) viewCode.addEventListener('scroll', this.saveScrollPosition)
  },
  methods: {
    applyPatch() {
      this.$projects.applyPatch({ patch: this.code })
    },
    async onShowDiff() {
      if (!this.diff) {
        await this.loadDiffInfo()
      }
      this.orgContent = await this.$api.files.read(this.file)
      this.showDiff = !this.showDiff
    },
    async loadDiffInfo() {
      try {
        this.loadingStats = true
        if (this.file) {
          const { diff, stats } = await this.$api.files.diff({ path: this.file, content: this.code })
          this.diff = diff
          this.stats = stats
          if (!stats && diff) {
            this.stats = 'File changes'
          }
        }
      } finally {
        this.loadingStats = false
      }
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
      this.edit = !this.edit ? this.code : null
    },
    createSubTask() {
      const content = [
        "```" + this.fileLanguage + " " + this.file,
        this.code,
        "```"
      ].join("\n")
      this.$emit('sub-task', { file: this.file, content })
    },
    saveScrollPosition() {
      const viewCode = this.$el?.querySelector('.view-code')
      if (viewCode) this.prevScrollTop = viewCode.scrollTop
    }
  }
}
</script>

<style>
.header-code-highlight {
  display: none !important;
}
</style>