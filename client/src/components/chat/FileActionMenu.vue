<script setup>
import { computed } from 'vue'
</script>

<template>
  <div
    class="flex gap-2"
  >
    <!-- Copy path -->
    <button
      class="click rounded hover:bg-base-200 transition-colors flex-shrink-0"
      @click.stop="$emit('copy-path')"
      title="Copy path"
    >
      <i class="fa-solid fa-copy text-accent text-xs"></i>
    </button>

    <!-- Add as message -->
    <button
      class="click rounded hover:bg-base-200 transition-colors flex-shrink-0"
      @click.stop="$emit('add-as-message')"
      title="Add as message"
    >
      <i class="fa-regular fa-comment-dots text-info text-xs"></i>
    </button>

    <!-- Sync notebook (conditional) -->
    <button
      v-if="isNotebook"
      class="click rounded hover:bg-base-200 transition-colors flex-shrink-0"
      @click.stop="$emit('sync-notebook')"
      title="Sync notebook"
    >
      <i class="fa-solid fa-book-open text-warning text-xs"></i>
    </button>

    <!-- Export notebook (conditional) -->
    <button
      v-if="isNotebook"
      class="click rounded hover:bg-base-200 transition-colors flex-shrink-0"
      @click.stop="$emit('export-notebook')"
      title="Export notebook"
    >
      <i class="fa-solid fa-file-export text-success text-xs"></i>
    </button>

    <!-- Preview file (conditional) -->
    <button
      v-if="showPreview"
      class="click rounded hover:bg-base-200 transition-colors flex-shrink-0"
      @click.stop="$emit('preview-file')"
      title="Preview"
    >
      <i class="fa-regular fa-eye text-primary text-xs"></i>
    </button>

    <!-- Add/Remove toggle (conditional) -->
    <button
      v-if="showAddToChat"
      class="click rounded hover:bg-base-200 transition-colors flex-shrink-0"
      @click.stop="$emit('add-file')"
      title="Add to chat files"
    >
      <i class="fa-solid fa-plus text-success text-xs"></i>
    </button>

    <button
      v-if="showRemoveFromChat"
      class="click rounded hover:bg-base-200 transition-colors flex-shrink-0"
      @click.stop="$emit('remove-file')"
      title="Remove"
    >
      <i class="fa-solid fa-trash text-error text-xs"></i>
    </button>
  </div>
</template>

<script>
export default {
  props: {
    filePath: { type: String, required: true },
    fileType: { type: String, enum: ['chat', 'conversation'], required: true },
    isNotebook: { type: Boolean, default: false }
  },
  emits: ['copy-path', 'add-as-message', 'sync-notebook', 'export-notebook', 'preview-file', 'add-file', 'remove-file'],
  computed: {
    showPreview() {
      return this.fileType === 'conversation'
    },
    showAddToChat() {
      return this.fileType === 'conversation'
    },
    showRemoveFromChat() {
      return this.fileType === 'chat'
    }
  }
}
</script>