<script setup>
import FileActionMenu from './FileActionMenu.vue'
</script>

<template>
  <div class="my-1 text-xs space-y-1">
    <!-- Chat Files Section -->
    <div v-if="chatFileStatuses.length > 0" class="space-y-1">
      <div class="flex items-center gap-1.5 px-2 py-0.5 text-xs font-semibold text-base-content/70 uppercase tracking-wider">
        <i class="fa-solid fa-paperclip text-primary flex-shrink-0"></i>
        <span>Chat Files</span>
        <span class="badge badge-xs badge-primary">{{ chatFileStatuses.length }}</span>
      </div>
      <div class="flex flex-wrap gap-1">
        <div
          v-for="file in chatFileStatuses"
          :key="file.path"
          class="group flex items-center gap-1"
        >
          <!-- File Chip (Label + Icon) -->
          <div
            class="flex items-center gap-0.5 px-2 py-1 rounded-full bg-primary/10 text-primary/80 cursor-pointer transition-all duration-200 hover:bg-primary/20 flex-shrink-0"
            @click="$emit('preview-file', file.path)"
            :class="[
              file.exists === false 
                ? 'bg-error/10 text-error/60 hover:bg-error/20' 
                : ''
            ]"
          >
            <i class="fa-solid fa-file text-xs flex-shrink-0"></i>
            <span class="font-medium max-w-[80px] truncate">
              {{ file.label }}
            </span>
          </div>

          <!-- Action Menu (always visible on hover, no overlap) -->
          <FileActionMenu
            v-if="file.exists !== false"
            class="hidden group-hover:flex transition-opacity duration-200"
            :file-path="file.path"
            file-type="chat"
            :is-notebook="isNotebook(file)"
            @copy-path="$ui.copyTextToClipboard(file.path)"
            @add-as-message="$emit('add-as-message', file.path)"
            @sync-notebook="$emit('sync-notebook', file.path)"
            @export-notebook="$emit('export-notebook', file.path)"
            @remove-file="$emit('remove-file', file.path)"
          />

          <!-- Missing file indicator icon -->
          <i v-if="file.exists === false" class="fa-solid fa-circle-xmark text-error text-xs flex-shrink-0" title="File not found"></i>
        </div>
      </div>
    </div>

    <!-- Conversation Files Section -->
    <div v-if="conversationFileStatuses.length > 0" class="space-y-1">
      <div class="flex items-center gap-1.5 px-2 py-0.5 text-xs font-semibold text-base-content/70 uppercase tracking-wider">
        <i class="fa-solid fa-comments text-info flex-shrink-0"></i>
        <span>Conversation Files</span>
        <span class="badge badge-xs badge-info">{{ conversationFileStatuses.length }}</span>
      </div>
      <div class="flex flex-wrap gap-1 opacity-75">
        <div
          v-for="file in conversationFileStatuses"
          :key="file.path"
          class="group flex items-center gap-1"
        >
          <!-- File Chip (Label + Icon) -->
          <div
            class="flex items-center gap-0.5 px-2 py-1 rounded-full bg-info/10 text-info/70 cursor-pointer transition-all duration-200 hover:bg-info/20 hover:opacity-100 flex-shrink-0"
            @click="$emit('preview-file', file.path)"
            :class="[
              file.exists === false 
                ? 'bg-error/10 text-error/50 hover:bg-error/20' 
                : ''
            ]"
          >
            <i class="fa-solid fa-file text-xs flex-shrink-0"></i>
            <span class="font-medium">
              {{ file.label }}
            </span>
          </div>

          <!-- Action Menu (always visible on hover, no overlap) -->
          <FileActionMenu
            v-if="file.exists !== false"
            class="hidden group-hover:flex transition-opacity duration-200"
            :file-path="file.path"
            file-type="conversation"
            :is-notebook="isNotebook(file)"
            @copy-path="$ui.copyTextToClipboard(file.path)"
            @add-as-message="$emit('add-as-message', file.path)"
            @preview-file="$emit('preview-file', file.path)"
            @add-file="$emit('add-file', file.path)"
          />

          <!-- Missing file indicator icon -->
          <i v-if="file.exists === false" class="fa-solid fa-circle-xmark text-error text-xs flex-shrink-0" title="File not found"></i>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="chatFileStatuses.length === 0 && conversationFileStatuses.length === 0" class="text-center py-1 text-base-content/40 text-xs">
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
      chatFileStatuses: [],
      conversationFileStatuses: []
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

      const existingChat = new Map(this.chatFileStatuses.map(f => [f.path, f]))
      this.chatFileStatuses = chatFiles.map(path => {
        if (existingChat.has(path)) return existingChat.get(path)
        const entry = {
          path,
          label: path?.split('/').reverse()[0] || '---error---',
          exists: null
        }
        this.checkFileExists(entry)
        return entry
      })

      const uniqueConvFiles = conversationFiles.filter(
        f => !chatFilePaths.has(this.normalizeFilePath(f))
      )
      const existingConv = new Map(this.conversationFileStatuses.map(f => [f.path, f]))
      this.conversationFileStatuses = uniqueConvFiles.map(path => {
        if (existingConv.has(path)) return existingConv.get(path)
        const entry = {
          path,
          label: path?.split('/').reverse()[0] || '---error---',
          exists: null
        }
        this.checkFileExists(entry)
        return entry
      })
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