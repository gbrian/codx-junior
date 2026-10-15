<script setup>
import { computed } from 'vue'
</script>

<template>
  <div class="flex items-center gap-0.5">
    <!-- Add to chat (for conversation files) -->
    <button
      v-if="fileType === 'conversation'"
      class="p-1 rounded hover:bg-base-content/10 transition-colors flex-shrink-0"
      @click.stop="$emit('add-file')"
      title="Add to chat"
      aria-label="Add to chat"
    >
      <i class="fa-solid fa-plus text-success text-xs"></i>
    </button>

    <!-- Remove from chat (for chat files) -->
    <button
      v-if="fileType === 'chat'"
      class="p-1 rounded hover:bg-base-content/10 transition-colors flex-shrink-0"
      @click.stop="$emit('remove-file')"
      title="Remove from chat"
      aria-label="Remove from chat"
    >
      <i class="fa-solid fa-minus text-error text-xs"></i>
    </button>

    <!-- Copy path -->
    <button
      class="p-1 rounded hover:bg-base-content/10 transition-colors flex-shrink-0"
      @click.stop="$emit('copy-path')"
      title="Copy path"
      aria-label="Copy path"
    >
      <i class="fa-solid fa-copy text-accent text-xs"></i>
    </button>

    <!-- Add as message -->
    <button
      class="p-1 rounded hover:bg-base-content/10 transition-colors flex-shrink-0"
      @click.stop="$emit('add-as-message')"
      title="Add as message"
      aria-label="Add as message"
    >
      <i class="fa-regular fa-comment-dots text-info text-xs"></i>
    </button>

    <!-- Sync notebook (conditional) -->
    <button
      v-if="isNotebook"
      class="p-1 rounded hover:bg-base-content/10 transition-colors flex-shrink-0"
      @click.stop="$emit('sync-notebook')"
      title="Sync notebook"
      aria-label="Sync notebook"
    >
      <i class="fa-solid fa-book-open text-warning text-xs"></i>
    </button>

    <!-- Export notebook (conditional) -->
    <button
      v-if="isNotebook"
      class="p-1 rounded hover:bg-base-content/10 transition-colors flex-shrink-0"
      @click.stop="$emit('export-notebook')"
      title="Export notebook"
      aria-label="Export notebook"
    >
      <i class="fa-solid fa-file-export text-success text-xs"></i>
    </button>

    <!-- Preview file (conditional) -->
    <button
      v-if="fileType === 'conversation'"
      class="p-1 rounded hover:bg-base-content/10 transition-colors flex-shrink-0"
      @click.stop="$emit('preview-file')"
      title="Preview"
      aria-label="Preview"
    >
      <i class="fa-regular fa-eye text-primary text-xs"></i>
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
  emits: ['copy-path', 'add-as-message', 'sync-notebook', 'export-notebook', 'preview-file', 'add-file', 'remove-file']
}
</script>