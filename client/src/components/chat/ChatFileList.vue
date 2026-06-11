<script setup>
</script>

<template>
  <div class="my-2 text-xs" v-if="fileStatuses.length">
    <span><i class="fa-solid fa-paperclip"></i></span>
    <a
      v-for="file in fileStatuses"
      :key="file.path"
      :data-tip="file.path"
      class="group text-nowrap ml-2 hover:underline hover:bg-base-300 cursor-pointer"
      :class="file.exists === false ? 'text-error' : 'text-accent'"
      :title="file.exists === false ? 'File not found: ' + file.path : file.path"
      @click="$ui.openFile(file.path)"
    >
      <span class="click mr-1" @click.stop="$ui.copyTextToClipboard(file.path)">
        <i class="fa-solid fa-copy"></i>
      </span>
      <span>{{ file.label }}</span>
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
      <span class="ml-2 cursor-pointer" @click.stop="$emit('remove', file.path)">
        <i class="fa-regular fa-circle-xmark"></i>
      </span>
    </a>
  </div>
</template>

<script>
export default {
  props: {
    files: { type: Array, default: () => [] },
    chatProject: { type: Object, default: null }
  },
  emits: ['remove', 'add-as-message', 'sync-notebook', 'export-notebook'],
  data() {
    return {
      // Each entry: { path, label, exists: null|true|false }
      fileStatuses: []
    }
  },
  watch: {
    files: {
      immediate: true,
      handler(files) {
        this.syncFiles(files)
      }
    }
  },
  methods: {
    // Sync file list and trigger existence checks for new entries
    syncFiles(files) {
      if (!files) { this.fileStatuses = []; return }
      const existing = new Map(this.fileStatuses.map(f => [f.path, f]))
      this.fileStatuses = files.map(path => {
        if (existing.has(path)) return existing.get(path)
        const entry = { path, label: path?.split('/').reverse()[0] || '---error---', exists: null }
        this.checkFileExists(entry)
        return entry
      })
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