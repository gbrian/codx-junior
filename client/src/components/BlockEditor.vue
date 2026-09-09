<script setup>
import CodeViewer from './CodeViewer.vue'
</script>

<template>
  <!-- Edit mode -->
  <div v-if="isEditing" class="bg-base-200 rounded-lg p-3 border border-base-300">
    <!-- Editor toolbar -->
    <div class="flex items-center justify-between gap-2 mb-2 pb-2 border-b border-base-300">
      <span class="text-xs font-semibold text-base-content/60">Editing block</span>
      <div class="flex gap-1">
        <button
          class="btn btn-xs btn-ghost gap-1"
          @click="cancelEdit"
        >
          <i class="fa-solid fa-ban"></i> Cancel
        </button>
        <button
          class="btn btn-xs btn-primary gap-1"
          :disabled="!hasChanges"
          @click="saveEdit"
        >
          <i class="fa-solid fa-check"></i> Save
        </button>
      </div>
    </div>

    <!-- Editor content -->
    <div class="space-y-2">
      <!-- Code editor for code blocks -->
      <div v-if="isCodeBlock" class="bg-base-300 rounded min-h-[200px] overflow-hidden">
        <textarea
          v-model="editedContent"
          class="w-full h-[300px] p-3 bg-base-300 text-xs font-mono text-base-content border-0 resize-none focus:outline-none"
          :placeholder="'Edit ' + language + ' code...'"
        ></textarea>
      </div>

      <!-- Markdown editor for markdown blocks -->
      <div v-else class="bg-base-300 rounded min-h-[200px] overflow-hidden">
        <textarea
          v-model="editedContent"
          class="w-full h-[300px] p-3 bg-base-300 text-sm text-base-content border-0 resize-none focus:outline-none"
          placeholder="Edit markdown content..."
        ></textarea>
      </div>

      <!-- Quick info -->
      <div class="flex items-center justify-between text-[10px] text-base-content/40">
        <span v-if="hasChanges" class="text-warning flex items-center gap-1">
          <i class="fa-solid fa-circle-info"></i> You have unsaved changes
        </span>
        <span v-else>No changes</span>
        <span>{{ editedContent.length }} characters</span>
      </div>
    </div>
  </div>

  <!-- View mode -->
  <div v-else>
    <slot></slot>
  </div>
</template>

<script>
export default {
  props: {
    originalContent: { type: String, required: true },
    isCodeBlock: { type: Boolean, default: false },
    language: { type: String, default: 'text' }
  },
  emits: ['edit-start', 'edit-cancel', 'edit-save'],
  data() {
    return {
      isEditing: false,
      editedContent: ''
    }
  },
  computed: {
    hasChanges() {
      return this.editedContent !== this.originalContent
    }
  },
  methods: {
    startEdit() {
      this.isEditing = true
      this.editedContent = this.originalContent
      this.$emit('edit-start')
    },
    cancelEdit() {
      this.isEditing = false
      this.editedContent = ''
      this.$emit('edit-cancel')
    },
    saveEdit() {
      if (!this.hasChanges) return
      this.$emit('edit-save', {
        originalContent: this.originalContent,
        newContent: this.editedContent
      })
      this.isEditing = false
      this.editedContent = ''
    }
  }
}
</script>