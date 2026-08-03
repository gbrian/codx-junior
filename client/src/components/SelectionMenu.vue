<script setup>
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
    position: { type: Object, default: () => ({ x: 0, y: 0 }) },
  },
  emits: ['copy', 'create-subtask', 'close'],
  data() {
    return {
      menuPosition: { x: 0, y: 0 }
    }
  },
  watch: {
    position(newPos) {
      this.menuPosition = { ...newPos }
    },
    isVisible(visible) {
      if (visible) {
        document.addEventListener('click', this.closeMenu)
        document.addEventListener('contextmenu', this.closeMenu)
      } else {
        document.removeEventListener('click', this.closeMenu)
        document.removeEventListener('contextmenu', this.closeMenu)
      }
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
    onClose() {
      this.$emit('close')
    },
    closeMenu() {
      this.onClose()
    }
  }
}
</script>