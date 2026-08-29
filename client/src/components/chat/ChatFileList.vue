<script setup>
import FileActionMenu from './FileActionMenu.vue'
</script>

<template>
  <div class="my-1 text-xs space-y-1">
    <!-- Unified Files List (Chat first, then Conversation - sorted by filename length) -->
    <div v-if="mergedFileStatuses.length > 0" class="space-y-1">
      <div class="flex items-center gap-1.5 px-2 py-0.5 text-xs font-semibold text-base-content/70 uppercase tracking-wider">
        <i class="fa-solid fa-file text-base-content/60 flex-shrink-0"></i>
        <span>Files</span>
        <span class="badge badge-xs badge-base-300">{{ mergedFileStatuses.length }}</span>
      </div>
      
      <div class="flex flex-wrap gap-1">
        <div
          v-for="file in mergedFileStatuses"
          :key="file.path"
          class="group flex items-center gap-1"
        >
          <!-- File Chip (Label + Icon) - Color coded by type -->
          <div
            class="flex items-center gap-0.5 px-2 py-1 rounded-full cursor-pointer transition-all duration-200 flex-shrink-0"
            @click="$emit('preview-file', file.path)"
            :title="file.path"
            :class="[
              file.type === 'chat'
                ? 'bg-primary/10 text-primary/80 hover:bg-primary/20'
                : 'bg-info/10 text-info/70 hover:bg-info/20',
              file.exists === false 
                ? 'bg-error/10 text-error/60 hover:bg-error/20 opacity-60' 
                : ''
            ]"
          >
            <i class="fa-solid fa-file text-xs flex-shrink-0"></i>
            <span class="font-medium max-w-[80px] group-hover:max-w-full truncate">
              {{ file.label }}
            </span>
          </div>

          <!-- Action Menu -->
          <FileActionMenu
            v-if="file.exists !== false"
            class="hidden group-hover:flex transition-opacity duration-200"
            :file-path="file.path"
            :file-type="file.type"
            :is-notebook="isNotebook(file)"
            @copy-path="$ui.copyTextToClipboard(file.path)"
            @add-as-message="$emit('add-as-message', file.path)"
            @sync-notebook="$emit('sync-notebook', file.path)"
            @export-notebook="$emit('export-notebook', file.path)"
            @preview-file="$emit('preview-file', file.path)"
            @add-file="$emit('add-file', file.path)"
            @remove-file="$emit('remove-file', file.path)"
          />

          <!-- Missing file indicator -->
          <i v-if="file.exists === false" class="fa-solid fa-circle-xmark text-error text-xs flex-shrink-0" title="File not found"></i>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="mergedFileStatuses.length === 0" class="text-center py-1 text-base-content/40 text-xs">
      <i class="fa-solid fa-paperclip block mb-0.5"></i>
      <span>No files</span>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    files: { type: Array, default: () => [] },
    messageFiles: { type: Array, default: () => [] },
    chatProject: { type: Object, default: null }
  },
  emits: ['remove-file', 'add-file', 'add-as-message', 'sync-notebook', 'export-notebook', 'preview-file'],
  data() {
    return {
      mergedFileStatuses: []
    }
  },
  watch: {
    files: {
      immediate: true,
      handler() {
        this.syncFiles()
      }
    },
    messageFiles: {
      immediate: true,
      handler() {
        this.syncFiles()
      }
    }
  },
  methods: {
    syncFiles() {
      const chatFiles = this.files || []
      const conversationFiles = this.messageFiles || []

      const chatFilePaths = new Set(chatFiles.map(f => this.normalizeFilePath(f)))

      // Build chat files with type
      const chatFileStatuses = chatFiles.map(path => ({
        path,
        type: 'chat',
        label: path?.split('/').reverse()[0] || '---error---',
        exists: null,
        nameLength: path?.split('/').reverse()[0]?.length || 0
      }))

      // Build conversation files with type (exclude duplicates)
      const uniqueConvFiles = conversationFiles.filter(
        f => !chatFilePaths.has(this.normalizeFilePath(f))
      )
      const conversationFileStatuses = uniqueConvFiles.map(path => ({
        path,
        type: 'conversation',
        label: path?.split('/').reverse()[0] || '---error---',
        exists: null,
        nameLength: path?.split('/').reverse()[0]?.length || 0
      }))

      // Merge: chat files first, then conversation files, both sorted by filename length
      this.mergedFileStatuses = [
        ...chatFileStatuses.sort((a, b) => a.nameLength - b.nameLength),
        ...conversationFileStatuses.sort((a, b) => a.nameLength - b.nameLength)
      ]

      // Check existence for each file
      this.mergedFileStatuses.forEach(entry => this.checkFileExists(entry))
    },

    normalizeFilePath(path) {
      return path?.toLowerCase().trim() || ''
    },

    async checkFileExists(entry) {
      try {
        await this.chatProject.$api.files.read(entry.path)
        entry.exists = true
      } catch {
        entry.exists = false
      }
    },

    isNotebook(file) {
      return file.path?.endsWith('.ipynb')
    }
  }
}
</script>