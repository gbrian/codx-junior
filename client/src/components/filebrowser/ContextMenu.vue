<script setup>
</script>

<template>
  <div
    v-if="isVisible"
    class="fixed z-50 bg-base-100 border border-base-300 rounded-lg shadow-lg py-1 min-w-48"
    :style="{ top: position.y + 'px', left: position.x + 'px' }"
    @click.stop
    @contextmenu.prevent.stop
  >
    <!-- Create new file -->
    <button
      class="w-full px-4 py-2 text-sm text-left hover:bg-base-200 flex items-center gap-2 transition-colors"
      @click="handleCreate(false)"
      title="Create a new file"
    >
      <i class="fa-solid fa-file-plus w-4"></i>
      <span>New File</span>
    </button>

    <!-- Create new folder -->
    <button
      class="w-full px-4 py-2 text-sm text-left hover:bg-base-200 flex items-center gap-2 transition-colors"
      @click="handleCreate(true)"
      title="Create a new folder"
    >
      <i class="fa-solid fa-folder-plus w-4"></i>
      <span>New Folder</span>
    </button>

    <div class="divider my-1" v-if="hasSelection"></div>

    <!-- Rename -->
    <button
      v-if="hasSelection && !isMultiSelect"
      class="w-full px-4 py-2 text-sm text-left hover:bg-base-200 flex items-center gap-2 transition-colors"
      @click="handleRename"
      title="Rename file or folder"
    >
      <i class="fa-solid fa-pen-to-square w-4"></i>
      <span>Rename</span>
    </button>

    <!-- Delete -->
    <button
      v-if="hasSelection"
      class="w-full px-4 py-2 text-sm text-left hover:bg-error/10 text-error flex items-center gap-2 transition-colors"
      @click="handleDelete"
      title="Delete selected items"
    >
      <i class="fa-solid fa-trash w-4"></i>
      <span>Delete {{ isMultiSelect ? `(${selectionCount})` : '' }}</span>
    </button>
  </div>
</template>

<script>
export default {
  name: 'ContextMenu',
  props: {
    isVisible: {
      type: Boolean,
      default: false
    },
    position: {
      type: Object,
      default: () => ({ x: 0, y: 0 })
    },
    hasSelection: {
      type: Boolean,
      default: false
    },
    isMultiSelect: {
      type: Boolean,
      default: false
    },
    selectionCount: {
      type: Number,
      default: 0
    }
  },
  methods: {
    handleCreate(isDir) {
      this.$emit('create', { isDir })
    },
    handleRename() {
      this.$emit('rename')
    },
    handleDelete() {
      this.$emit('delete')
    }
  }
}
</script>