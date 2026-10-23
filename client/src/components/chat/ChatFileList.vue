<script setup>
import FileActionMenu from './FileActionMenu.vue'
</script>

<template>
  <div class="my-1 space-y-1 px-1 text-xs md:space-y-1.5 md:px-0 md:text-sm">
    <!-- Header -->
    <div
      v-if="mergedFileStatuses.length > 0"
      class="flex items-center gap-1.5 px-1 text-[11px] font-semibold uppercase tracking-wider text-base-content/60"
    >
      <i class="fa-solid fa-paperclip flex-shrink-0"></i>
      <span class="truncate">Files</span>
      <span class="badge badge-xs badge-ghost shrink-0">{{ mergedFileStatuses.length }}</span>
    </div>

    <!-- File chips — actions are ALWAYS visible (no hover reveal) so they
         remain reachable on touch devices and keyboards. -->
    <div v-if="mergedFileStatuses.length > 0" class="flex flex-wrap gap-1 md:gap-1.5">
      <div
        v-for="file in mergedFileStatuses"
        :key="file.path"
        class="flex items-center gap-0.5 rounded-md px-1.5 py-0.5 text-xs transition-colors"
        :class="[
          file.exists === false
            ? 'bg-error/10'
            : (file.type === 'chat' ? 'bg-primary/10 hover:bg-primary/15' : 'bg-base-200 hover:bg-base-300')
        ]"
      >
        <!-- Label → preview/open (real button for keyboard + touch) -->
        <button
          type="button"
          class="flex min-w-0 items-center gap-1 rounded px-0.5 py-1 text-left"
          :title="file.exists === false ? 'File not found: ' + file.path : file.path"
          @click.stop="$emit('preview-file', file.path)"
        >
          <i
            class="fa-solid flex-shrink-0 text-[10px]"
            :class="file.exists === false
              ? 'fa-circle-xmark text-error'
              : (file.type === 'chat' ? 'fa-file text-primary' : 'fa-file text-info')"
          ></i>
          <span
            class="max-w-[120px] truncate font-medium md:max-w-[220px]"
            :class="file.exists === false ? 'text-error/70 line-through' : ''"
          >{{ file.label }}</span>
        </button>

        <!-- Missing-file indicator (color alone is never the only signal) -->
        <i
          v-if="file.exists === false"
          class="fa-solid fa-circle-xmark pr-1 text-xs text-error"
          title="File not found"
        ></i>

        <!-- Actions — inline & always visible -->
        <FileActionMenu
          v-if="file.exists !== false"
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
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="py-1 text-center text-base-content/40 md:py-2">
      <i class="fa-solid fa-paperclip mb-0.5 block"></i>
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