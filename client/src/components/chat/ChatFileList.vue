<script setup>
</script>

<template>
  <div class="my-2 text-xs">
    <span><i class="fa-solid fa-paperclip"></i></span>

    <!-- Chat Files Section -->
    <template v-if="fileStatuses.length > 0">
      <a
        v-for="file in fileStatuses"
        :key="file.path"
        :data-tip="file.path"
        class="group text-nowrap ml-2 hover:underline hover:bg-base-300 cursor-pointer"
        :class="[
          file.exists === false ? 'text-error' : 'text-accent',
          file.isMessageFile ? 'opacity-75' : 'font-semibold'
        ]"
        :title="file.exists === false ? 'File not found: ' + file.path : file.path"
      >
        <span class="click mr-1" @click.stop="$ui.copyTextToClipboard(file.path)">
          <i class="fa-solid fa-copy"></i>
        </span>
        <!-- Clicking the label opens the preview panel -->
        <span @click.stop="$emit('preview-file', file.path)">{{ file.label }}</span>
        <span
          v-if="file.exists !== false"
          class="ml-2 cursor-pointer"
          @click.stop="$emit('add-as-message', file.path)"
        >
          <i class="fa-regular fa-comment-dots"></i>
        </span>
        <!-- Notebook sync icon: only shown for .ipynb files -->
        <span
          v-if="isNotebook(file)"
          class="ml-2 cursor-pointer text-warning"
          :title="'Sync notebook: ' + file.path"
          @click.stop="$emit('sync-notebook', file.path)"
        >
          <i class="fa-solid fa-book-open"></i>
        </span>
        <!-- Export chat to notebook icon: only shown for .ipynb files -->
        <span
          v-if="isNotebook(file)"
          class="ml-2 cursor-pointer text-success"
          :title="'Export chat to notebook: ' + file.path"
          @click.stop="$emit('export-notebook', file.path)"
        >
          <i class="fa-solid fa-file-export"></i>
        </span>

        <!-- Plus icon for message files (add to chat) -->
        <span
          v-if="file.isMessageFile"
          class="ml-2 cursor-pointer text-info"
          :title="'Add to chat files: ' + file.path"
          @click.stop="$emit('add-to-chat', file.path)"
        >
          <i class="fa-solid fa-plus"></i>
        </span>

        <!-- Minus icon for chat files (remove from chat) -->
        <span
          v-else
          class="ml-2 cursor-pointer"
          @click.stop="$emit('remove', file.path)"
        >
          <i class="fa-regular fa-circle-xmark"></i>
        </span>
      </a>
    </template>
  </div>
</template>

<script>
export default {
  props: {
    files: { type: Array, default: () => [] },
    messageFiles: { type: Array, default: () => [] },
    chatProject: { type: Object, default: null }
  },
  emits: ['remove', 'add-as-message', 'sync-notebook', 'export-notebook', 'preview-file', 'add-to-chat'],
  data() {
    return {
      fileStatuses: []
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
    // Sync both chat files and message files, filtering duplicates
    syncFiles() {
      const chatFiles = this.files || []
      const msgFiles = this.messageFiles || []
      
      // Create a set of normalized chat file paths for fast lookup
      const chatFilePaths = new Set(chatFiles.map(f => this.normalizeFilePath(f)))
      
      // Filter message files to exclude those already in chat files
      const uniqueMsgFiles = msgFiles.filter(
        f => !chatFilePaths.has(this.normalizeFilePath(f))
      )
      
      // Combine: chat files first, then unique message files
      const allFiles = [...chatFiles, ...uniqueMsgFiles]
      
      const existing = new Map(this.fileStatuses.map(f => [f.path, f]))
      
      this.fileStatuses = allFiles.map(path => {
        if (existing.has(path)) return existing.get(path)
        const entry = {
          path,
          label: path?.split('/').reverse()[0] || '---error---',
          exists: null,
          isMessageFile: !chatFilePaths.has(this.normalizeFilePath(path))
        }
        this.checkFileExists(entry)
        return entry
      })
    },

    normalizeFilePath(path) {
      return path?.toLowerCase().trim() || ''
    },

    // Check file existence via API and update entry reactively
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