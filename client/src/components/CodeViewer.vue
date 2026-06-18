<script setup>
import moment from 'moment'
import { VueCodeHighlighter } from 'vue-code-highlighter'
import 'vue-code-highlighter/dist/style.css'
import hljs from 'highlight.js'
import Editor from './monaco/Editor.vue'
import Collapsible from './Collapsible.vue'
import { EXTENSION_LANGUAGE_MAP } from '../store'
</script>

<template>
  <Collapsible v-model="showCode" class="h-full">
    <template #icon>
      <span class="loading loading-spinner loading-xs" v-if="isStreaming"></span>
      <div class="hover:text-info" @click.stop="$emit('add-file', file)" v-else>
        <i class="fa-solid fa-file-arrow-up"></i>
      </div>
    </template>

    <template #title>
      <div class="flex gap-2 items-center">
        <div class="underline text-link flex gap-2 items-center cursor-pointer" v-if="fileName">
          <div class="hover:text-info tooltip" :data-tip="file" @click.stop="$emit('open-file', file)">
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

        <div
          class="hover:text-info cursor-pointer"
          :class="editMode && 'text-warning'"
          @click.stop="onEdit"
        >
          <i class="fa-solid fa-edit"></i>
        </div>

        <div class="hover:text-info cursor-pointer" @click.stop="createSubTask">
          <i class="fa-brands fa-trello"></i>
        </div>

        <span class="text-xs text-info flex gap-2 items-center" @click.stop="">
          <span v-if="loadingStats">Loading...</span>
          <span @click.stop="onShowDiff" class="cursor-pointer hover:underline" v-if="stats && !editMode && !isNoChange">
            <i class="fa-solid fa-file-lines" v-if="showDiff"></i>
            <i class="fa-solid fa-code-compare" v-else></i>
            {{ stats }}
          </span>

          <span v-if="last_modification">
            {{ moment(last_modification).fromNow() }}
          </span>
          <span v-if="size">
            {{ size > 1024 ? `${Math.round(size/1024)} KB` : `${size} B` }}
          </span>
        </span>
      </div>
    </template>

    <template #actions>
      <button class="btn btn-sm btn-success btn-outline"
        @click.stop="saveToFile"
        v-if="file && finished && !showCode"
        title="Save to file">
        <i class="fa-solid fa-floppy-disk"></i> Save
      </button>
      <button class="btn btn-sm btn-error btn-outline"
        @click.stop="$emit('close')"
        v-if="close"
        title="Close">
        <i class="fa-solid fa-rectangle-xmark"></i>
      </button>
    </template>

    <div class="p-2 flex flex-col gap-2">

      <div @click="runCommand" class="cursor-pointer" v-if="isCommand">
        <i class="fa-solid fa-terminal"></i>
      </div>

      <!-- view-code grows to fill all available vertical space -->
      <div class="view-code grow overflow-auto">
        <!-- Fixed height container for Monaco editors so they render correctly -->
        <div :style="{ zoom, height: `${editorHeight}px` }">
          <!-- File diff view: original on disk vs generated code (editable) -->
          <Editor
            :diff="true"
            :originalCode="orgContent"
            v-model="diffEditContent"
            :fileName="file"
            class="h-full"
            v-if="showDiff && !editMode && orgContent"
          />

          <!-- Monaco editor: plain edit mode, needs explicit height to render -->
          <Editor
            v-model="editContent"
            :fileName="file"
            class="h-full"
            @update:modelValue="onEditorChange"
            v-if="editMode"
          />
        

          <!-- Syntax highlighted read-only view -->
          <VueCodeHighlighter
            class="h-full"
            :code="code"
            :lang="fileLanguage"
            :title="fileName"
            v-if="code && !editMode && !showDiff"
          />
        </div>
      </div>

      <div class="flex justify-end gap-2" v-if="editMode">
        <button class="btn btn-sm btn-outline" @click="cancelEdit">
          <i class="fa-solid fa-xmark"></i> Cancel
        </button>
        <button class="btn btn-sm btn-warning" @click="applyMessageChange">
          <i class="fa-solid fa-pen-to-square"></i> Apply
        </button>
      </div>
      <div class="flex justify-end gap-2" v-else-if="showDiff && !isNoChange">
        <button class="btn btn-sm btn-outline" @click="onShowDiff">
          <i class="fa-solid fa-xmark"></i> Close diff
        </button>
        <button class="btn btn-sm btn-success btn-outline" @click="saveDiffEdit" v-if="file">
          <i class="fa-solid fa-floppy-disk"></i> Save changes
        </button>
      </div>
      <div class="flex justify-end gap-2" v-else>
        <button class="btn btn-sm btn-outline" @click.stop="onCopy" title="Copy">
          <i class="fa-solid fa-copy"></i> Copy
        </button>
        <button class="btn btn-sm btn-success btn-outline"
          @click.stop="saveToFile"
          v-if="file && finished"
          title="Save to file">
          <i class="fa-solid fa-floppy-disk"></i> Save
        </button>
      </div>

      <div class="flex justify-end gap-2" v-if="!editMode">
        <button class="btn btn-sm btn-warning" @click="applyPatch" v-if="isPatch">
          Apply patch
        </button>
      </div>
    </div>
  </Collapsible>
</template>

<script>
export default {
  props: ['close', 'chat', 'code', 'language', 'file', 'diff-option', 'file-diff', 'files', 'project', 'finished'],
  emits: ['message-change', 'save-file', 'add-file', 'open-file', 'sub-task'],
  data() {
    return {
      showDiff: false,
      orgContent: null,
      diffEditContent: null,
      diff: this.fileDiff,
      zoom: 1,
      editMode: false,
      editContent: null,
      hasUnsavedFileChanges: false,
      loadingStats: false,
      stats: null,
      last_modification: null,
      size: null,
      showCode: true,
      prevScrollTop: 0,
      isAtBottom: true,
    }
  },
  computed: {
    // Estimate editor height from line count, capped at 600px, min 200px
    editorHeight() {
      const lineCount = this.code?.split("\n").length || 10
      const estimated = Math.max(lineCount * 20, 200)
      return Math.min(estimated, 600)
    },
    isStreaming() {
      return !this.finished && this.code
    },
    isPatch() {
      return this.language === 'diff'
    },
    fileName() {
      return this.file?.split('/').reverse()[0]
    },
    isCommand() {
      return this.language === 'bash'
    },
    // Parse stats string to check if insertions === deletions (no net change)
    isNoChange() {
      if (!this.stats) return false
      const insertMatch = this.stats.match(/(\d+) insertion/)
      const deleteMatch = this.stats.match(/(\d+) deletion/)
      if (!insertMatch || !deleteMatch) return false
      return parseInt(insertMatch[1]) === parseInt(deleteMatch[1])
    },
    fileLanguage() {
      if (this.language) {
        if (hljs.getLanguage(this.language)) {
          return this.language
        }
      }
      const ext = this.file?.split('.').reverse()[0]
      if (ext) {
        return EXTENSION_LANGUAGE_MAP[ext] || ext
      }
      return 'markdown'
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
        this.saveToFile()
      }
    },
    code() {
      this.$nextTick(() => {
        const viewCode = this.$el?.querySelector('.view-code')
        if (!viewCode) return
        if (this.isAtBottom) {
          viewCode.scrollTop = viewCode.scrollHeight
        } else {
          viewCode.scrollTop = this.prevScrollTop
        }
      })
    }
  },
  mounted() {
    if (this.chat?.mode === 'vibe') {
      this.showCode = false
    }
    if (this.finished) {
      this.loadDiffInfo()
    }
    const viewCode = this.$el?.querySelector('.view-code')
    if (viewCode) viewCode.addEventListener('scroll', this.saveScrollPosition)
  },
  beforeUnmount() {
    const viewCode = this.$el?.querySelector('.view-code')
    if (viewCode) viewCode.removeEventListener('scroll', this.saveScrollPosition)
  },
  methods: {
    applyPatch() {
      this.$projects.applyPatch({ patch: this.code })
    },

    async onShowDiff() {
      if (this.isNoChange) return
      if (!this.showDiff) {
        await this.loadDiffInfo()
        const { content } = await this.$api.files.read(this.file)
        this.orgContent = content
        this.diffEditContent = this.code
      }
      this.showDiff = !this.showDiff
    },

    async loadDiffInfo() {
      try {
        this.loadingStats = true
        if (this.file) {
          const { diff, stats, last_modification, size } = await this.$api.files.diff({ path: this.file, content: this.code })
          this.diff = diff
          this.stats = stats
          this.last_modification = last_modification
          this.size = size
          if (!stats && diff) {
            this.stats = 'File changes'
          }
        }
      } finally {
        this.loadingStats = false
      }
    },

    onEdit() {
      if (this.editMode) {
        this.cancelEdit()
        return
      }
      this.editContent = this.code
      this.editMode = true
      this.showDiff = false
      this.hasUnsavedFileChanges = false
    },

    cancelEdit() {
      this.editMode = false
      this.editContent = null
    },

    onEditorChange(value) {
      this.editContent = value
      this.hasUnsavedFileChanges = true
    },

    applyMessageChange() {
      this.$emit('message-change', { orgContent: this.code, newContent: this.editContent })
      this.hasUnsavedFileChanges = true
      this.cancelEdit()
    },

    saveDiffEdit() {
      this.$emit('save-file', { file: this.file, content: this.diffEditContent })
      this.hasUnsavedFileChanges = false
      this.showDiff = false
    },

    saveToFile() {
      const content = this.editMode ? this.editContent : this.code
      this.$emit('save-file', { file: this.file, content })
      this.hasUnsavedFileChanges = false
      if (this.editMode) {
        this.cancelEdit()
      }
    },

    runCommand() {
      this.$storex.api.apps.runScript(this.code)
    },

    zoomOut() {
      this.zoom -= 0.1
    },

    zoomIn() {
      this.zoom += 0.1
    },

    onCopy() {
      this.$ui.copyTextToClipboard(this.code)
    },

    createSubTask() {
      const content = [
        '```' + this.fileLanguage + ' ' + this.file,
        this.code,
        '```'
      ].join('\n')
      this.$emit('sub-task', { file: this.file, content })
    },

    saveScrollPosition() {
      const viewCode = this.$el?.querySelector('.view-code')
      if (!viewCode) return
      this.prevScrollTop = viewCode.scrollTop
      const distanceFromBottom = viewCode.scrollHeight - viewCode.scrollTop - viewCode.clientHeight
      this.isAtBottom = distanceFromBottom <= 40
    }
  }
}
</script>

<style>
.header-code-highlight {
  display: none !important;
}
.wrapper-code-highlight {
  height: 100%;
}
</style>