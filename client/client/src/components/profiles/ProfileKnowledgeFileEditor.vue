<script setup>
import { normalizeFileName } from '../../services/profileKnowledgeApi'
</script>

<template>
  <div class="flex flex-col min-h-0 bg-[#1f1f1f] border border-white/5 rounded-md overflow-hidden">
    <!-- Toolbar -->
    <div class="flex items-center gap-2 px-3 py-2 border-b border-white/5">
      <div class="flex-1 min-w-0">
        <label for="profile-knowledge-file-name" class="sr-only">Knowledge file name</label>
        <input
          id="profile-knowledge-file-name"
          v-model="fileName"
          type="text"
          :readonly="isExisting || !canWrite"
          class="input input-sm w-full bg-white/5 border-white/10 rounded text-xs font-mono text-white placeholder:text-white/25 outline-none focus:border-primary/50 focus:bg-white/[0.08] transition-colors duration-150"
          placeholder="guidelines/state-management.md"
          aria-describedby="profile-knowledge-file-hint"
        />
      </div>
      <button
        type="button"
        class="btn btn-xs btn-ghost text-white/60 hover:text-white transition-colors duration-150"
        :aria-pressed="preview"
        :title="preview ? 'Edit markdown' : 'Preview markdown'"
        @click="preview = !preview"
      >
        <i class="fas" :class="preview ? 'fa-pen' : 'fa-eye'" aria-hidden="true"></i>
        <span class="hidden sm:inline">{{ preview ? 'Edit' : 'Preview' }}</span>
      </button>
      <button
        v-if="isExisting && canWrite"
        type="button"
        class="btn btn-xs btn-ghost text-white/60 hover:text-error transition-colors duration-150"
        title="Delete this file"
        @click="$emit('delete')"
      >
        <i class="fas fa-trash" aria-hidden="true"></i>
        <span class="sr-only">Delete file</span>
      </button>
      <button
        v-if="isExisting && canWrite"
        type="button"
        class="btn btn-xs btn-ghost text-white/60 hover:text-primary transition-colors duration-150"
        title="Convert this file into a rule"
        @click="$emit('promote')"
      >
        <i class="fas fa-arrow-up-from-bracket" aria-hidden="true"></i>
        <span class="sr-only">Move to rule</span>
      </button>
      <button
        type="button"
        class="btn btn-xs btn-ghost text-white/50 hover:text-white transition-colors duration-150"
        title="Close editor"
        @click="$emit('cancel')"
      >
        <i class="fas fa-xmark" aria-hidden="true"></i>
        <span class="sr-only">Close</span>
      </button>
    </div>

    <!-- Body -->
    <textarea
      v-if="!preview"
      id="profile-knowledge-file-content"
      v-model="draft"
      :readonly="!canWrite"
      rows="16"
      spellcheck="false"
      class="textarea w-full flex-1 min-h-[16rem] bg-transparent border-0 rounded-none text-xs font-mono leading-relaxed text-white/90 placeholder:text-white/25 outline-none resize-y focus:outline-none"
      placeholder="# Conventions&#10;&#10;- Always use standalone components"
      aria-label="Knowledge file content"
    ></textarea>
    <pre
      v-else
      class="flex-1 min-h-[16rem] px-3 py-2 m-0 text-xs font-mono leading-relaxed text-white/80 whitespace-pre-wrap break-words overflow-auto"
    >{{ draft || '> Nothing to preview yet.' }}</pre>

    <!-- Footer -->
    <div class="flex flex-wrap items-center justify-between gap-2 px-3 py-2 border-t border-white/5">
      <p id="profile-knowledge-file-hint" class="text-[11px] text-white/40">
        {{ fileNameHint }}
      </p>
      <div class="flex items-center gap-2">
        <span v-if="dirty" class="text-[11px] text-warning">unsaved</span>
        <button
          type="button"
          class="btn btn-sm btn-primary"
          :disabled="saving || !canWrite || !normalizedFileName || !draft.trim()"
          @click="submit"
        >
          <span v-if="saving" class="loading loading-spinner loading-xs mr-1"></span>
          <i v-else class="fas fa-floppy-disk mr-1" aria-hidden="true"></i>
          {{ isExisting ? 'Update file' : 'Create file' }}
        </button>
      </div>
    </div>

    <!-- Error -->
    <p v-if="error" class="px-3 pb-2 text-[11px] text-error">{{ error }}</p>
  </div>
</template>

<script>
export default {
  props: {
    // Existing knowledge file entry (null when creating a new one).
    file: {
      type: Object,
      default: null
    },
    // File content loaded by the parent (empty when creating).
    content: {
      type: String,
      default: ''
    },
    // Whether the user may write (admin / knowledge admin).
    canWrite: {
      type: Boolean,
      default: false
    },
    saving: {
      type: Boolean,
      default: false
    },
    error: {
      type: String,
      default: ''
    }
  },
  emits: ['save', 'delete', 'promote', 'cancel'],
  data() {
    return {
      fileName: '',
      draft: '',
      initialContent: '',
      preview: false
    }
  },
  computed: {
    isExisting() {
      return !!(this.file && this.file.file)
    },
    normalizedFileName() {
      return normalizeFileName(this.fileName)
    },
    dirty() {
      return this.draft !== this.initialContent
    },
    fileNameHint() {
      if (!this.canWrite) {
        return 'Read-only: you need project admin or knowledge admin rights to edit'
      }
      if (!this.normalizedFileName) {
        return 'A .md extension is added when none is given'
      }
      return `Saved as ${this.normalizedFileName} · ${this.draft.length} chars`
    }
  },
  watch: {
    file: {
      immediate: true,
      handler() {
        this.resetFromProps()
      }
    },
    content() {
      this.draft = this.content || ''
      this.initialContent = this.draft
    }
  },
  methods: {
    resetFromProps() {
      this.fileName = this.file ? this.file.file : ''
      this.draft = this.content || ''
      this.initialContent = this.draft
      this.preview = false
    },
    submit() {
      this.$emit('save', {
        fileName: this.normalizedFileName,
        content: this.draft,
        overwrite: this.isExisting
      })
    }
  }
}
</script>