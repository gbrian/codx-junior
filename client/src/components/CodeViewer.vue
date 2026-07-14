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

          <div
            class="hover:text-info cursor-pointer"
            :class="editMode && 'text-warning'"
            @click.stop="onEdit"
            title="Edit code"
          >
            <i class="fa-solid fa-edit"></i>
          </div>

          <div
            class="hover:text-info cursor-pointer"
            :class="associatedChat && 'text-success'"
            @click.stop="onTaskClick"
            :title="associatedChat ? 'Open associated chat' : 'Create sub-task'"
          >
            <i :class="associatedChat ? 'fa-solid fa-comments' : 'fa-brands fa-trello'"></i>
          </div>

          <div class="hover:text-info cursor-pointer" @click.stop="loadDiffInfo" title="Refresh diff stats">
            <i class="fa-solid fa-arrows-rotate" :class="{ 'animate-spin': loadingStats }"></i>
          </div>

          <span class="text-xs text-info flex gap-2 items-center" @click.stop="">
            <span v-if="loadingStats">Loading...</span>
            <span @click.stop="toggleView" class="cursor-pointer hover:underline" v-if="stats">
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

          <div class="font-mono text-xs truncate trl" v-if="!finished">
            {{ lastLine }}<span class="ml-1 animate-pulse text-info">_</span>
          </div>

          <span
            v-if="hasLocalChanges"
            class="badge badge-warning badge-xs gap-1"
            title="You have unsaved local edits"
          >
            <i class="fa-solid fa-pen-nib"></i> edited
          </span>
        </div>

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
        v-if="!isNoChange && file && finished && (showCode || showDiff)"
        :class="{ 'blink-save': isSaving }"
        title="Save to file">
        <i class="fa-solid fa-floppy-disk"></i> Save
      </button>

      <span class="text-success font-console text-xs" v-if="isNoChange">No changes</span>

      <button class="btn btn-sm btn-error btn-outline"
        @click.stop="discardDiffChanges"
        v-if="showDiff && hasDiffEdits"
        title="Discard changes">
        <i class="fa-solid fa-xmark"></i> Discard
      </button>

      <button class="btn btn-sm btn-ghost btn-outline"
        @click.stop="resetLocalChanges"
        v-if="hasLocalChanges"
        title="Reset to original AI-generated code">
        <i class="fa-solid fa-rotate-left"></i> Reset
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

      <div v-if="isDangerousChange && !editMode && !showDiff" class="alert alert-warning">
        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4v2m0 0a9 9 0 1 1 0-18 9 9 0 0 1 0 18z" />
        </svg>
        <span class="text-sm">
          <strong>Heavy modification detected:</strong> {{ changeRiskMessage }}
        </span>
      </div>

      <div v-if="isApplyingPatch" class="alert alert-info">
        <span class="loading loading-spinner loading-sm"></span>
        <span class="text-sm">Applying AI patch, please wait…</span>
      </div>

      <div v-if="changesetErrors.length" class="alert alert-error">
        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4v2m0 0a9 9 0 1 1 0-18 9 9 0 0 1 0 18z" />
        </svg>
        <div class="flex flex-col gap-1">
          <span class="font-bold">Changeset Errors:</span>
          <div class="text-sm space-y-1">
            <div v-for="(error, idx) in changesetErrors" :key="idx" class="text-xs">
              • {{ error }}
            </div>
          </div>
        </div>
      </div>

      <div class="view-code grow overflow-auto">
        <div :style="{ height: `${editorHeight}px` }">

          <Editor
            :diff="true"
            :originalCode="orgContent"
            v-model="diffEditContent"
            :fileName="file"
            class="h-full"
            v-if="showDiff && !editMode"
          />

          <Editor
            v-model="editContent"
            :fileName="file"
            class="h-full"
            @update:modelValue="onEditorChange"
            v-if="editMode"
          />

          <VueCodeHighlighter
            class="h-full"
            :code="effectiveCode"
            :lang="validatedLanguage"
            :title="fileName"
            v-if="effectiveCode && !editMode && !showDiff"
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

    <modal v-if="showConfirmModal">
        <h3 class="font-bold text-lg">Unsaved Changes</h3>
        <p>You have unsaved changes in the diff editor. What would you like to do?</p>
        <button class="btn btn-error" @click="confirmDiscardDiff">
          <i class="fa-solid fa-trash"></i> Discard
        </button>
        <button class="btn btn-success" @click="confirmApplyDiff">
          <i class="fa-solid fa-check"></i> Apply
        </button>
        <button class="btn" @click="cancelConfirm">
          <i class="fa-solid fa-xmark"></i> Cancel
        </button>
    </modal>
  </Collapsible>
</template>

<script>
export default {
  props: ['close', 'chat', 'code', 'language', 'file', 'diff-option', 'file-diff', 'files', 'project', 'finished', 'showCodeOpened', 'message', 'fromBranch', 'toBranch'],
  emits: ['message-change', 'save-file', 'add-file', 'open-file', 'close', 'sub-task'],
  data() {
    return {
      showDiff: this.diffOption,
      orgContent: null,
      diffEditContent: null,
      diffBaseContent: null,
      diff: this.fileDiff,
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
      isApplyingPatch: false,
      deletionPercentage: 0,
      additionPercentage: 0,
      deletionCount: 0,
      additionCount: 0,
      isDangerousChange: false,
      changeRiskMessage: '',
      isNewFile: true,
      localCode: null,
      showConfirmModal: false,
      pendingViewSwitch: null,
      changesetErrors: []
    }
  },
  computed: {
    effectiveCode() {
      return this.localCode !== null ? this.localCode : this.code
    },

    hasLocalChanges() {
      return this.localCode !== null && this.localCode !== this.code
    },

    hasDiffEdits() {
      return this.diffEditContent !== this.diffBaseContent
    },

    editorHeight() {
      const lineCount = this.effectiveCode?.split("\n").length || 10
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
      return this.orgContent === this.code
    },

    fileLanguage() {
      if (this.language) {
        if (hljs.getLanguage(this.language)) return this.language
      }
      const ext = this.file?.split('.').reverse()[0]
      if (ext) return EXTENSION_LANGUAGE_MAP[ext] || ext
      return 'markdown'
    },

    validatedLanguage() {
      const lang = this.fileLanguage
      try {
        if (lang && hljs.getLanguage(lang)) {
          return lang
        }
      } catch (error) {
        console.warn(`Invalid language detected: ${lang}`, error)
      }
      return 'markdown'
    },

    $api() {
      return (this.project?.$api || this.$storex.api)
    },

    lastLine() {
      return this.code?.split("\n").reverse()[0]
    },

    associatedChat() {
      return this.$service.chat.findChatByFileAndMessage({
        chat: this.chat,
        file: this.file,
        messageId: this.message?.doc_id
      })
    },
    isJSONChangeset() {
      return this.language === 'json-changeset'
    }
  },
  watch: {
    async finished() {
      if (this.finished && this.showCode) {
        await this.loadDiffInfo()
        if (!this.isNewFile && this.stats && !this.isNoChange) {
          this.showDiff = true
        }
      }
      if (this.chat?.mode === 'vibe') {
        this.saveToFile()
      }
    },
    code() {
      this.changesetErrors = []
      this.$nextTick(() => {
        const viewCode = this.$el?.querySelector('.view-code')
        if (!viewCode) return
        if (this.isAtBottom) {
          viewCode.scrollTop = viewCode.scrollHeight
        } else {
          viewCode.scrollTop = this.prevScrollTop
        }
      })
    },
    fromBranch() {
      if (this.showCode) {
        this.loadDiffInfo()
      }
    },
    toBranch() {
      if (this.showCode) {
        this.loadDiffInfo()
      }
    }
  },
  mounted() {
    if (this.chat?.mode === 'vibe') {
      this.showCode = false
    }
    if (this.finished && this.showCode) {
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
    applyChangeset() {
      try {
        const changeset = JSON.parse(this.code)
        if (!Array.isArray(changeset)) {
          this.changesetErrors.push('Changeset must be a JSON array')
          return
        }

        let processedCode = this.code
        changeset.forEach((change, idx) => {
          try {
            const { search_type, search, replace, replace_all } = change
            if (!search_type || !search || replace === undefined) {
              throw new Error('Missing required fields: search_type, search, or replace')
            }

            let result
            if (search_type === 'plain') {
              // Plain text search: exact match
              const searchIndex = processedCode.indexOf(search)
              if (searchIndex === -1) {
                throw new Error(`Pattern not found in code`)
              }

              if (replace_all) {
                // Replace all occurrences
                processedCode = processedCode.split(search).join(replace)
              } else {
                // Replace only first occurrence
                processedCode = processedCode.substring(0, searchIndex) +
                  replace +
                  processedCode.substring(searchIndex + search.length)
              }
            } else if (search_type === 'regex') {
              // Regex search: use replace_all to determine global flag
              try {
                const flags = replace_all ? 'g' : ''
                const regex = new RegExp(search, flags)
                processedCode = processedCode.replace(regex, replace)
              } catch (regexError) {
                throw new Error(`Invalid regex pattern: ${regexError.message}`)
              }
            } else {
              throw new Error(`Unknown search_type: ${search_type}. Must be 'plain' or 'regex'`)
            }
          } catch (error) {
            this.changesetErrors.push(`[Item ${idx}] ${error.message}`)
          }
        })

        this.localCode = processedCode
      } catch (parseError) {
        this.changesetErrors.push(`Failed to parse changeset JSON: ${parseError.message}`)
      }
    },

    applyUserChange(newContent) {
      if (!newContent) return
      this.localCode = newContent
      this.diffEditContent = newContent
      this.diffBaseContent = newContent
      this.editMode = false
      this.showDiff = !!this.orgContent
      this.hasUnsavedFileChanges = true
    },

    resetLocalChanges() {
      this.localCode = null
      this.diffEditContent = this.code
      this.diffBaseContent = this.code
      this.hasUnsavedFileChanges = false
      this.showDiff = !!this.orgContent && !this.isNoChange
    },

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
      const newLines = this.effectiveCode?.split('\n').length || 1
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
      if (delRatio > 0.4) return `${(delRatio * 100).toFixed(0)}% of original content deleted. Critical review recommended.`
      if (lineRatio > 0.3 && deletions > insertions) return `File lost ~${Math.round(lineRatio * 100)}% of its content. Check if changes are intentional.`
      if (intensity > 0.5) return `Over 50% of file modified. This may indicate significant structural changes.`
      return 'High modification level detected.'
    },

    applyPatch() {
      this.$projects.applyPatch({ patch: this.code })
    },

    async applyPatchFromAI() {
      if (!this.file || this.isApplyingPatch) return
      try {
        this.isApplyingPatch = true
        const response = await this.$api.run.patch({
          file_path: this.file,
          partial_content: this.effectiveCode
        })
        if (response?.content) {
          this.applyUserChange(response.content)
        } else {
          console.warn('Patch API returned no content', response)
        }
      } catch (error) {
        console.error('Error applying patch from AI:', error)
        this.$ui?.showNotification?.({
          type: 'error',
          message: 'Failed to apply patch: ' + (error?.message || 'Unknown error')
        })
      } finally {
        this.isApplyingPatch = false
      }
    },

    toggleView() {
      if (this.hasDiffEdits) {
        this.pendingViewSwitch = 'toggle'
        this.showConfirmModal = true
      } else {
        this.showDiff = !this.showDiff
      }
    },

    // In the methods section, update loadDiffInfo:
    async loadDiffInfo() {
      try {
        this.loadingStats = true
        if (this.file) {
          const diffRequest = {
            path: this.file,
            content: this.effectiveCode
          }
          if (this.fromBranch) diffRequest.from_branch = this.fromBranch
          if (this.toBranch) diffRequest.to_branch = this.toBranch

          const { diff, stats, last_modification, size } = await this.$api.files.diff(diffRequest)
          this.diff = diff
          this.stats = stats
          this.last_modification = last_modification
          this.size = size
          if (!stats && diff) this.stats = 'File changes'

          let content = ""
          try {
            // NEW: Load from branch if available
            if (this.fromBranch) {
              const { content: fileContent } = await this.$api.repo.readFromBranch(this.file, this.fromBranch)
              content = fileContent
              this.isNewFile = !fileContent
            } else {
              // Fallback to current file content
              const { content: fileContent } = await this.$api.files.read(this.file)
              content = fileContent
              this.isNewFile = !fileContent
            }
          } catch (ex) {
            console.error(ex)
            this.isNewFile = true
          }

          this.orgContent = content
          this.diffEditContent = this.effectiveCode
          this.diffBaseContent = this.effectiveCode
          this.calculateDiffPercentages()

          if (this.isJSONChangeset) {
            this.applyChangeset()
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
      this.editContent = this.effectiveCode
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
      this.$emit('message-change', { orgContent: this.effectiveCode, newContent: this.editContent })
      this.applyUserChange(this.editContent)
      this.cancelEdit()
    },

    discardDiffChanges() {
      this.diffEditContent = this.diffBaseContent
      this.showDiff = false
    },

    confirmApplyDiff() {
      this.localCode = this.diffEditContent
      this.diffBaseContent = this.diffEditContent
      this.showConfirmModal = false
      this.pendingViewSwitch = null
      if (this.pendingViewSwitch === 'toggle') {
        this.showDiff = !this.showDiff
      }
    },

    confirmDiscardDiff() {
      this.diffEditContent = this.diffBaseContent
      this.showConfirmModal = false
      const shouldToggle = this.pendingViewSwitch === 'toggle'
      this.pendingViewSwitch = null
      if (shouldToggle) {
        this.showDiff = !this.showDiff
      }
    },

    cancelConfirm() {
      this.showConfirmModal = false
      this.pendingViewSwitch = null
    },

    async saveToFile() {
      this.triggerSaveAnimation()
      let content
      if (this.editMode && this.editContent) {
        content = this.editContent
      } else if (this.showDiff && this.diffEditContent) {
        content = this.diffEditContent
      } else {
        content = this.effectiveCode
      }
      this.$emit('save-file', { file: this.file, content })
      this.hasUnsavedFileChanges = false
      if (this.editMode) this.cancelEdit()
      this.showDiff = false
      this.localCode = null
      this.diffEditContent = null
      this.diffBaseContent = null
      await this.loadDiffInfo()
    },

    triggerSaveAnimation() {
      this.isSaving = true
      setTimeout(() => { this.isSaving = false }, 800)
    },

    runCommand() {
      this.$storex.api.apps.runScript(this.code)
    },

    onCopy() {
      this.$ui.copyTextToClipboard(this.effectiveCode)
    },

    createSubTask() {
      const content = [
        '```' + this.fileLanguage + ' ' + this.file,
        this.effectiveCode,
        '```'
      ].join('\n')
      this.$emit('sub-task', { file: this.file, content })
    },

    onTaskClick() {
      if (this.associatedChat) {
        this.$chats.setActiveChat(this.associatedChat)
      } else {
        this.createSubTask()
      }
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
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0.4; }
}

.blink-save {
  animation: blink-animation 0.8s ease-in-out;
}
</style>