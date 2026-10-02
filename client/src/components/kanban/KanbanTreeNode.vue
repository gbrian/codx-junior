<script setup>
</script>

<template>
  <div class="flex flex-col">
    <!-- Folder node -->
    <div v-if="displayNode.isFolder">
      <div
        class="flex items-center gap-1 px-2 py-1 rounded hover:bg-base-300 cursor-pointer select-none"
        :style="{ paddingLeft: `${depth * 12 + 8}px` }"
        @click="$emit('toggle-expand', displayNode.path)"
      >
        <i
          class="fa-solid text-xs w-3 text-base-content-ERROR-40"
          :class="isExpanded ? 'fa-chevron-down' : 'fa-chevron-right'"
        ></i>

        <!-- Folder selection checkbox BEFORE folder icon -->
        <input
          v-if="selectionMode"
          type="checkbox"
          class="checkbox checkbox-xs checkbox-primary mr-1"
          :checked="folderAllSelected"
          :indeterminate.prop="folderSomeSelected"
          @change.stop="toggleFolderSelection"
          @click.stop
        />

        <i
          class="fa-solid text-warning text-xs"
          :class="isExpanded ? 'fa-folder-open' : 'fa-folder'"
        ></i>
        <span class="text-xs font-medium flex-1 truncate" :title="displayNode.path">
          {{ displayNode.name }}
        </span>

        <span class="badge badge-xs badge-ghost">{{ displayNode.fileCount }}</span>
      </div>

      <!-- Children -->
      <div v-if="isExpanded">
        <kanban-tree-node
          v-for="child in displayNode.children"
          :key="child.path"
          :node="child"
          :depth="depth + (node.isFolder ? 1 : 0)"
          :selection-mode="selectionMode"
          :selected-files="selectedFiles"
          :expanded-nodes="expandedNodes"
          @toggle-expand="$emit('toggle-expand', $event)"
          @toggle-select="$emit('toggle-select', $event)"
          @toggle-select-many="$emit('toggle-select-many', $event)"
          @open-task="$emit('open-task', $event)"
        />
      </div>
    </div>

    <!-- File node -->
    <div
      v-else
      class="group flex items-center gap-2 px-2 py-1 rounded hover:bg-base-300 transition-colors"
      :style="{ paddingLeft: `${depth * 12 + 8}px` }"
    >
      <i class="fa-solid fa-minus text-xs w-3 text-base-content/20"></i>

      <!-- File selection checkbox -->
      <input
        v-if="selectionMode"
        type="checkbox"
        class="checkbox checkbox-xs checkbox-primary"
        :checked="selectedFiles.includes(displayNode.path)"
        @change="$emit('toggle-select', displayNode.path)"
        @click.stop
      />

      <i class="fa-solid fa-file-code text-info text-xs"></i>

      <span
        class="font-mono text-xs flex-1 truncate cursor-pointer hover:text-primary"
        :title="displayNode.path"
        @click="displayNode.tasks?.length && $emit('open-task', displayNode.tasks[0].chat)"
      >
        {{ displayNode.name }}
      </span>

      <!-- Action icons (visible on hover) -->
      <div class="flex gap-1 items-center opacity-0 group-hover:opacity-100 transition-opacity">
        <!-- Copy file content -->
        <button
          class="btn btn-ghost btn-xs px-1"
          :class="{ 'text-success': copiedPath === displayNode.path }"
          title="Copy file content"
          @click.stop="copyFilePath(displayNode.path)"
        >
          <i class="fa-regular fa-copy text-xs"></i>
        </button>
      </div>

      <!-- Task badges -->
      <div class="flex gap-1 items-center">
        <span
          v-for="task in displayNode.tasks"
          :key="task.chat.id"
          class="badge badge-xs badge-ghost cursor-pointer hover:badge-primary truncate max-w-[80px]"
          :title="task.chat.name"
          @click.stop="$emit('open-task', task.chat)"
        >
          {{ task.chat.name || 'Untitled' }}
        </span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'KanbanTreeNode',
  props: {
    node: { type: Object, required: true },
    depth: { type: Number, default: 0 },
    selectionMode: { type: Boolean, default: false },
    selectedFiles: { type: Array, default: () => [] },
    expandedNodes: { type: Object, default: () => ({}) }
  },
  emits: ['toggle-expand', 'toggle-select', 'toggle-select-many', 'open-task'],
  data() {
    return {
      // Track which file was last copied for visual feedback
      copiedPath: null
    }
  },
  computed: {
    displayNode() {
      if (!this.node.isFolder) return this.node
      return this.collapseNode(this.node)
    },
    isExpanded() {
      return this.expandedNodes[this.displayNode.path] !== false
    },
    folderFilePaths() {
      return this.collectFilePaths(this.displayNode)
    },
    folderAllSelected() {
      return this.folderFilePaths.length > 0 &&
        this.folderFilePaths.every(p => this.selectedFiles.includes(p))
    },
    folderSomeSelected() {
      return !this.folderAllSelected &&
        this.folderFilePaths.some(p => this.selectedFiles.includes(p))
    }
  },
  methods: {
    collapseNode(node) {
      if (!node.isFolder) return node
      const onlyFolderChildren = node.children?.filter(c => c.isFolder) || []
      const fileChildren = node.children?.filter(c => !c.isFolder) || []
      if (onlyFolderChildren.length === 1 && fileChildren.length === 0) {
        const collapsed = this.collapseNode(onlyFolderChildren[0])
        return {
          ...collapsed,
          name: `${node.name}/${collapsed.name}`,
          path: collapsed.path
        }
      }
      return node
    },

    collectFilePaths(node) {
      if (!node.isFolder) return [node.path]
      return (node.children || []).flatMap(child => this.collectFilePaths(child))
    },

    toggleFolderSelection() {
      const paths = this.folderFilePaths
      this.$emit('toggle-select-many', { paths, select: !this.folderAllSelected })
    },

    // Read full file content and copy it to clipboard with brief visual feedback
    async copyFilePath(filePath) {
      this.$ui.copyTextToClipboard(filePath)
    }
  }
}
</script>