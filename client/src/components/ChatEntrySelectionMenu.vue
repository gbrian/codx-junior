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
      class="btn btn-ghost btn-sm gap-1"
      @click.stop="onCopy"
    >
      <i class="fa-solid fa-copy"></i>
      Copy
    </button>
    <button 
      class="btn btn-ghost btn-sm gap-1"
      @click.stop="onCreateSubtask"
    >
      <i class="fa-solid fa-list-check"></i>
      Create task
    </button>
    <div v-if="isSingleWord" class="divider divider-horizontal mx-1"></div>
    <button 
      v-if="isSingleWord"
      class="btn btn-ghost btn-sm gap-1"
      @click.stop="onSearchFiles"
      :disabled="isSearching"
    >
      <i :class="['fa-solid', isSearching ? 'fa-spinner animate-spin' : 'fa-magnifying-glass']"></i>
      Search
    </button>
    <button 
      class="btn btn-ghost btn-sm text-base-content/50"
      @click="onClose"
    >
      <i class="fa-solid fa-times"></i>
    </button>
  </div>
</template>

<script>
export default {
  props: {
    selectedText: { type: String, default: '' },
    chatProject: { type: Object, default: null }
  },
  emits: ['copy', 'create-subtask', 'search-files', 'close'],
  data() {
    return {
      isSearching: false
    }
  },
  computed: {
    isSingleWord() {
      return this.selectedText && !this.selectedText.includes(' ') && this.selectedText.length > 0
    }
  },
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
    onSearchFiles() {
      if (!this.isSingleWord) return
      
      // Emit search event with the selected text to parent (ChatEntry)
      this.$emit('search-files', {
        query: this.selectedText,
        fromSelection: true
      })
      this.onClose()
    },
    onClose() {
      this.$emit('close')
    },
    onDocumentMouseDown(e) {
      if (!this.$el.contains(e.target)) {
        this.onClose()
      }
    }
  }
}
</script>