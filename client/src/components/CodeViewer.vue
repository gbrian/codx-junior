<script setup>
import { VueCodeHighlighter } from 'vue-code-highlighter'
import 'vue-code-highlighter/dist/style.css'
import hljs from 'highlight.js'
import DiffViewer from './DiffViewer.vue'
import Editor from './monaco/Editor.vue'
import Collapsible from './Collapsible.vue'
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
          <div class="hover:text-info tooltip" :data-tip="file" @click.stop="$emit('open-file', file)">
            {{ fileName }}
          </div>
        </div>
        <span class="text-sm font-medium opacity-60" v-else>Code</span>

        <!-- Zoom controls -->
        <div class="hover:text-info cursor-pointer" @click.stop="zoomOut">
          <i class="fa-solid fa-magnifying-glass-minus"></i>
        </div>
        <div class="hover:text-info cursor-pointer" @click.stop="zoomIn">
          <i class="fa-solid fa-magnifying-glass-plus"></i>
        </div>

        <!-- Edit toggle: highlighted when active -->
        <div
          class="hover:text-info cursor-pointer"
          :class="editMode && 'text-warning'"
          @click.stop="onEdit"
        >
          <i class="fa-solid fa-edit"></i>
        </div>

        <!-- Diff preview toggle (only while editing) -->
        <div
          class="hover:text-info cursor-pointer"
          :class="showMonacoDiff && 'text-info'"
          @click.stop="toggleMonacoDiff"
          v-if="editMode"
          title="Preview diff"
        >
          <i class="fa-solid fa-code-compare"></i>
        </div>
        
        <!-- Sub-task -->
        <div class="hover:text-info cursor-pointer" @click.stop="createSubTask">
          <i class="fa-brands fa-trello"></i>
        </div>

        <!-- File diff stats -->
        <span class="text-xs text-info">
          <span v-if="loadingStats">Loading...</span>
          <span @click.stop="onShowDiff" class="cursor-pointer" v-if="stats && !editMode">
            <i class="fa-solid fa-file-lines" v-if="showDiff"></i>
            <i class="fa-solid fa-code-compare" v-else></i>
            {{ stats }}
          </span>
        </span>
      </div>
    </template>

    <template #actions>

    </template>

    <!-- Default slot: collapsible code area -->
    <div class="flex flex-col gap-2 p-2">
      <!-- Run command button -->
      <div @click="runCommand" class="cursor-pointer" v-if="isCommand">
        <i class="fa-solid fa-terminal"></i>
      </div>

      <!-- Code display area -->
      <div class="view-code" :style="{ zoom }">

        <!-- Monaco Diff viewer: file diff from server -->
        <DiffViewer
          :file="file"
          :orgContent="orgContent"
          :newContent="code"
          :language="language"
          :diff="diff"
          v-if="showDiff && !editMode"
        />

        <!-- Monaco Diff viewer: editing preview (original vs edited) -->
        <Editor
          :diff="true"
          :originalCode="code"
          v-model="editContent"
          :language="fileLanguage"
          @update:modelValue="onEditorChange"
          v-if="editMode && showMonacoDiff"
        />

        <!-- Monaco editor: edit mode -->
        <Editor
          v-model="editContent"
          :language="fileLanguage"
          @update:modelValue="onEditorChange"
          v-if="editMode && !showMonacoDiff"
        />

        <!-- Syntax highlighted read-only view -->
        <VueCodeHighlighter
          :code="code"
          :lang="fileLanguage"
          :title="fileName"
          v-if="code && !editMode && !showDiff"
        />
      </div>

      <!-- Footer actions -->
      <div class="flex justify-end gap-2" v-if="editMode">
        <button class="btn btn-sm btn-outline" @click="cancelEdit">
          <i class="fa-solid fa-xmark"></i> Cancel
        </button>
        <!-- Apply to message: updates the chat message document -->
        <button class="btn btn-sm btn-warning" @click="applyMessageChange">
          <i class="fa-solid fa-pen-to-square"></i> Apply
        </button>
      </div>
      <div class="flex justify-end gap-2" v-else>
        <button class="btn btn-sm btn-outline"
          @click.stop="onCopy"
          title="Copy">
          <i class="fa-solid fa-copy"></i> Copy
        </button>
        <!-- Save to file: only writes to disk, always visible when file is known -->
        <button class="btn btn-sm btn-success btn-outline"
          @click.stop="saveToFile"
          v-if="file"
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
  props: ['chat', 'code', 'language', 'file', 'diff-option', 'file-diff', 'files', 'project', 'finished'],
  emits: ['message-change', 'save-file', 'add-file', 'open-file', 'sub-task'],
  data() {
    return {
      showDiff: false,
      orgContent: null,
      diff: this.fileDiff,
      zoom: 1,
      // editMode: user is editing the code block as a document
      editMode: false,
      // editContent: mutable copy while editing; code prop stays untouched
      editContent: null,
      // showMonacoDiff: toggle diff preview vs plain editor while in edit mode
      showMonacoDiff: false,
      // tracks whether editContent diverges from the last saved-to-file version
      hasUnsavedFileChanges: false,
      loadingStats: false,
      stats: null,
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
        // In vibe mode auto-save to file when generation completes
        this.saveToFile()
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

    toggleMonacoDiff() {
      this.showMonacoDiff = !this.showMonacoDiff
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
      this.showMonacoDiff = false
    },

    // Called on every editor keystroke; marks file as having unsaved changes
    onEditorChange(value) {
      this.editContent = value
      this.hasUnsavedFileChanges = true
    },

    // Applies the edited content back to the chat message (document update)
    // Does NOT touch the file on disk
    applyMessageChange() {
      this.$emit('message-change', { orgContent: this.code, newContent: this.editContent })
      this.hasUnsavedFileChanges = true
      this.cancelEdit()
    },

    // Writes the current code to disk; uses editContent if editing, otherwise code prop
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