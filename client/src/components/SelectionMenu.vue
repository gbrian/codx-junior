<script setup>
import { API } from '@/api/api'
</script>

<template>
  <div 
    class="selection-menu fixed bg-base-100 rounded-lg shadow-lg border border-base-300 z-50 py-2 min-w-48"
    :style="{ top: menuPosition.y + 'px', left: menuPosition.x + 'px' }"
    @mousedown.stop
  >
    <button 
      class="w-full px-4 py-2 text-left hover:bg-base-200 flex items-center gap-2 text-sm"
      @click="onCopy"
    >
      <i class="fa-solid fa-copy"></i>
      Copy
    </button>
    <button 
      class="w-full px-4 py-2 text-left hover:bg-base-200 flex items-center gap-2 text-sm"
      @click="onCreateSubtask"
    >
      <i class="fa-solid fa-list-check"></i>
      Create sub-task
    </button>
    <div class="divider my-1" v-if="isSingleWord"></div>
    <button 
      v-if="isSingleWord"
      class="w-full px-4 py-2 text-left hover:bg-base-200 flex items-center gap-2 text-sm"
      @click="onSearchFiles"
      :disabled="isSearching"
    >
      <i class="fa-solid fa-magnifying-glass"></i>
      Search files
      <i v-if="isSearching" class="fa-solid fa-spinner animate-spin ml-auto"></i>
    </button>
    <div class="divider my-1"></div>
    <button 
      class="w-full px-4 py-2 text-left hover:bg-base-200 flex items-center gap-2 text-sm"
      @click="onClose"
    >
      <i class="fa-solid fa-times"></i>
      Close
    </button>
  </div>
</template>

<script>
export default {
  props: {
    selectedText: { type: String, default: '' },
    position: { type: Object, default: () => ({ x: 0, y: 0 }) }
  },
  emits: ['copy', 'create-subtask', 'search-files', 'close'],
  data() {
    return {
      menuPosition: { x: 0, y: 0 },
      isSearching: false
    }
  },
  computed: {
    isSingleWord() {
      return this.selectedText && !this.selectedText.includes(' ') && this.selectedText.length > 0
    }
  },
  watch: {
    position(newPos) {
      this.menuPosition = { ...newPos }
    }
  },
  beforeUnmount() {
    document.removeEventListener('click', this.closeMenu)
    document.removeEventListener('contextmenu', this.closeMenu)
  },
  methods: {
    onCopy() {
      this.$emit('copy', this.selectedText)
      this.onClose()
    },
    onCreateSubtask() {
      this.$emit('create-subtask', this.selectedText)
      this.onClose()
    },
    async onSearchFiles() {
      if (!this.isSingleWord) return
      
      this.isSearching = true
      try {
        const results = await API.files.search({
          search: this.selectedText,
          page: 0,
          pageSize: 50
        })
        this.$emit('search-files', {
          query: this.selectedText,
          results
        })
        this.onClose()
      } catch (error) {
        console.error('File search failed:', error)
      } finally {
        this.isSearching = false
      }
    },
    onClose() {
      this.$emit('close')
    },
    closeMenu() {
      this.onClose()
    }
  }
}
</script>