<script setup>
</script>

<template>
  <div 
    class="sticky top-0 z-20 bg-base-100/95 border border-info backdrop-blur border-b border-base-300 rounded-t-md px-3 py-1 flex items-center gap-2 shadow-sm"
    @mousedown.stop
  >
    <span class="truncate max-w-xs italic">
      "{{ selectedText.slice(0, 60) }}{{ selectedText.length > 60 ? '...' : '' }}"
    </span>
    <div class="flex-1"></div>
    <button 
      class="btn btn-ghost gap-1"
      @click="onCopy"
    >
      <i class="fa-solid fa-copy"></i>
      Copy
    </button>
    <button 
      class="btn btn-ghost gap-1"
      @click="onCreateSubtask"
    >
      <i class="fa-solid fa-list-check"></i>
      Create task
    </button>
    <button 
      class="btn btn-ghost text-base-content/50"
      @click="onClose"
    >
      <i class="fa-solid fa-times"></i>
    </button>
  </div>
</template>

<script>
export default {
  props: {
    selectedText: { type: String, default: '' }
  },
  emits: ['copy', 'create-subtask', 'close'],
  mounted() {
    document.addEventListener('mousedown', this.onDocumentMouseDown)
  },
  beforeUnmount() {
    document.removeEventListener('mousedown', this.onDocumentMouseDown)
  },
  methods: {
    onCopy() {
      this.$emit('copy', this.selectedText)
      this.onClose()
    },
    onCreateSubtask() {
      this.$emit('create-subtask', this.selectedText.trim())
      this.onClose()
    },
    onClose() {
      this.$emit('close')
    },
    // Close when clicking outside the content area
    onDocumentMouseDown(e) {
      if (!this.$el.contains(e.target)) {
        this.onClose()
      }
    }
  }
}
</script>