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
        <div class="flex gap-2 items-center flex-1">
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
            <span @click.stop="toggleView" class="cursor-pointer hover:underline" v-if="stats && !editMode && !isNoChange">
              <i class="fa-solid fa-file-lines" v-if="showDiff"></i>
              <i class="fa-solid fa-code-compare" v-else></i>
              {{ stats }}
            </span>

            <span v-if="last_modification" class="text-xs opacity-75">
              {{ moment(last_modification).fromNow() }}
            </span>
            <span v-if="size">
              {{ size > 1024 ? `${Math.round(size/1024)} KB` : `${size} B` }}
            </span>
          </span>
        </div>

        <!-- Diff percentage bar with danger indicator -->
        <div v-if="stats && !editMode && !isNoChange" class="flex items-center gap-2 ml-2">
          <div 
            class="flex h-2 rounded-full overflow-hidden bg-base-200 w-24 relative transition-all duration-300"
            :class="isDangerousChange && 'ring-2 ring-error ring-opacity-70'"
          >
            <div
              class="bg-error transition-all duration-500"
              :style="{ width: deletionPercentage + '%' }"
              :title="`Deletions: ${deletionCount} lines`"
            ></div>
            <div
              class="bg-success transition-all duration-500"
              :style="{ width: additionPercentage + '%' }"
              :title="`Additions: ${additionCount} lines`"
            ></div>
          </div>
          <span class="text-xs font-medium text-base-content/60 w-20 text-right">
            {{ deletionCount }} / {{ additionCount }}
          </span>
          <div v-if="isDangerousChange" class="tooltip tooltip-left" data-tip="Heavy modification detected! Review carefully.">
            <i class="fa-solid fa-triangle-exclamation text-error animate-pulse"></i>
          </div>
        </div>
      </div>
    </template>

    <template #actions>
      <button class="btn btn-sm btn-success btn-outline"
        @click.stop="saveToFile"
        v-if="file && finished && (showCode || showDiff)"
        :class="{ 'blink-save': isSaving }"
        title="Save to file">
        <i class="fa-solid fa-floppy-disk"></i> Save
      </button>
      <button class="btn btn-sm btn-error btn-outline"
        @click.stop="discardChanges"
        v-if="showDiff && hasChanges"
        title="Discard changes">
        <i class="fa-solid fa-xmark"></i> Discard
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

      <!-- Danger alert for heavy modifications -->
      <div v-if="isDangerousChange && !editMode && !showDiff" class="alert alert-warning">
        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4v2m0 0a9 9 0 1 1 0-18 9 9 0 0 1 0 18z" /></svg>
        <span class="text-sm">
          <strong>Heavy modification detected:</strong> {{ changeRiskMessage }}
        </span>
      </div>

      <!-- view-code grows to fill all available vertical space -->
      <div class="view-code grow overflow-auto">
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

          <!-- Monaco editor: plain edit mode -->
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

      <!-- Edit mode actions -->
      <div class="flex justify-end gap-2" v-if="editMode">
        <button class="btn btn-sm btn-outline" @click="cancelEdit">
          <i class="fa-solid fa-xmark"></i> Cancel
        </button>
        <button class="btn btn-sm btn-warning" @click="applyMessageChange">
          <i class="fa-solid fa-pen-to-square"></i> Apply
        </button>
      </div>

      <!-- Read-only view actions -->
      <div class="flex justify-end gap-2" v-else>
        <button class="btn btn-sm btn-outline" @click.stop="onCopy" title="Copy">
          <i class="fa-solid fa-copy"></i> Copy
        </button>
        <button class="btn btn-sm btn-success btn-outline"
          @click.stop="applyPatch"
          v-if="isPatch"
          title="Apply patch">
          Apply patch
        </button>
      </div>
    </div>
  </Collapsible>
</template>

<script>
export default {
  props: ['close', 'chat', 'code', 'language', 'file', 'diff-option', 'file-diff', 'files', 'project', 'finished', 'showCodeOpened'],
  emits: ['message-change', 'save-file', 'add-file', 'open-file', 'close', 'sub-task'],
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
      showCode: this.$props.showCodeOpened,
      prevScrollTop: 0,
      isAtBottom: true,
      isSaving: false,
      deletionPercentage: 0,
      additionPercentage: 0,
      deletionCount: 0,
      additionCount: 0,
      isDangerousChange: false,
      changeRiskMessage: '',
      isNewFile: true
    }
  },
  computed: {
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
    hasChanges() {
      return this.diffEditContent !== this.code
    },
    $api() {
      return (this.project?.$api || this.$storex.api)
    }
  },
  watch: {
    async finished() {
      if (this.finished) {
        await this.loadDiffInfo()
        // Show diff by default for existing files when generation is done
        if (!this.isNewFile && this.stats && !this.isNoChange) {
          this.showDiff = true
        }
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
    parseStatsString() {
      if (!this.stats) return { deletions: 0, insertions: 0 }
      
      const deleteMatch = this.stats.match(/(\d+) deletion/)
      const insertMatch = this.stats.match(/(\d+) insertion/)
      
      return {
        deletions: deleteMatch ? parseInt(deleteMatch[1]) : 0,
        insertions: insertMatch ? parseInt(insertMatch[1]) : 0
      }
    },

    calculateDiffPercentages() {
      if (!this.stats || !this.orgContent) return
      
      const { deletions, insertions } = this.parseStatsString()
      const total = deletions + insertions
      
      this.deletionCount = deletions
      this.additionCount = insertions
      
      if (total === 0) {
        this.deletionPercentage = 0
        this.additionPercentage = 0
        return
      }
      
      this.deletionPercentage = (deletions / total) * 100
      this.additionPercentage = (insertions / total) * 100
      
      this.evaluateChangeRisk()
    },

    evaluateChangeRisk() {
      const { deletions, insertions } = this.parseStatsString()
      const originalLines = this.orgContent?.split('\n').length || 1
      const newLines = this.code?.split('\n').length || 1
      
      const deletionRatio = deletions / originalLines
      const lineChangeRatio = Math.abs(newLines - originalLines) / originalLines
      const totalChanges = deletions + insertions
      const changeIntensity = totalChanges / originalLines
      
      const DANGEROUS_DELETION_RATIO = 0.4
      const DANGEROUS_INTENSITY = 0.5
      const DANGEROUS_LINE_LOSS = 0.3
      
      const isDeletion = deletionRatio > DANGEROUS_DELETION_RATIO
      const isHighIntensity = changeIntensity > DANGEROUS_INTENSITY
      const isLineLoss = lineChangeRatio > DANGEROUS_LINE_LOSS && deletions > insertions
      
      this.isDangerousChange = isDeletion || isHighIntensity || isLineLoss
      this.changeRiskMessage = this.generateRiskMessage(deletionRatio, changeIntensity, lineChangeRatio, deletions, insertions)
    },

    generateRiskMessage(delRatio, intensity, lineRatio, deletions, insertions) {
      if (delRatio > 0.4) {
        return `${(delRatio * 100).toFixed(0)}% of original content deleted. Critical review recommended.`
      }
      if (lineRatio > 0.3 && deletions > insertions) {
        return `File lost ~${Math.round(lineRatio * 100)}% of its content. Check if changes are intentional.`
      }
      if (intensity > 0.5) {
        return `Over 50% of file modified. This may indicate significant structural changes.`
      }
      return 'High modification level detected.'
    },

    applyPatch() {
      this.$projects.applyPatch({ patch: this.code })
    },

    toggleView() {
      if (this.isNoChange) return
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
          
          // Determine if file is new
          const { content } = await this.$api.files.read(this.file)
          this.isNewFile = !content
          
          if (!this.orgContent) {
            this.orgContent = content
          }
          this.diffEditContent = this.code
          this.calculateDiffPercentages()
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

    discardChanges() {
      this.diffEditContent = this.code
      this.showDiff = false
    },

    async saveToFile() {
      this.triggerSaveAnimation()
      const content = this.isNewFile ? this.code : 
        (this.editMode ? this.editContent : this.diffEditContent)
      this.$emit('save-file', { file: this.file, content })
      this.hasUnsavedFileChanges = false
      if (this.editMode) {
        this.cancelEdit()
      }
      this.showDiff = false
      await this.loadDiffInfo()
    },

    triggerSaveAnimation() {
      this.isSaving = true
      setTimeout(() => {
        this.isSaving = false
      }, 800)
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

@keyframes blink-animation {
  0%, 49% {
    opacity: 1;
  }
  50%, 100% {
    opacity: 0.4;
  }
}

.blink-save {
  animation: blink-animation 0.8s ease-in-out;
}
</style>