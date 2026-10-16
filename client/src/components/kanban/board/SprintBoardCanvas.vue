<script setup>
import SprintBoardColumn from './SprintBoardColumn.vue'
</script>

<template>
  <!--
    Shared board canvas. Serves both:
      • Sprint board  (allowReorderColumns=false, allowNewColumn=false)
      • Kanban board  (allowReorderColumns=true,  allowNewColumn=true, background)
    The sprint implementation (latest behaviour) is the base; kanban-only
    affordances are opt-in through props.
  -->
  <div class="kanban-board-canvas flex flex-col flex-1 min-w-0 min-h-0 overflow-x-auto overflow-y-hidden relative">

    <!-- Board background image (Trello-style) -->
    <div
      v-if="background"
      class="absolute inset-0 z-0 bg-cover bg-center"
      :style="{ backgroundImage: `url(${background})` }"
    >
      <!-- Dark overlay so columns remain readable -->
      <div class="absolute inset-0 bg-base-100/60 backdrop-blur-[1px]"></div>
    </div>

    <!-- Canvas: horizontal scroll columns -->
    <div class="relative z-10 flex gap-3 h-full p-4 w-max min-w-full">
      <!-- Column components with optional drag-to-reorder -->
      <div
        v-for="(col, colIndex) in localColumns"
        :key="col.id || col.title || col.value"
        class="relative shrink-0 h-full"
        :class="draggingColIndex === colIndex ? 'opacity-40' : ''"
        @dragover.prevent="onColumnDragOver($event, colIndex)"
        @drop.prevent="onColumnDrop($event, colIndex)"
      >
        <SprintBoardColumn
          :column="col"
          :selectedTaskId="selectedTaskId"
          :allowCreate="allowCreate"
          :allowEdit="allowEditColumn"
          :allowActions="allowActions"
          :reorderable="reorderable"
          :draggable="allowReorderColumns"
          :hasBackground="!!background"
          @open-task="$emit('open-task', $event)"
          @open-task-window="$emit('open-task-window', $event)"
          @move-task="$emit('move-task', $event)"
          @new-task="$emit('new-task', { column: col.title, status: col.value || null })"
          @edit-column="$emit('edit-column', col.title)"
          @reorder-tasks="onReorderTasks(col, $event)"
          @add-subtask="$emit('add-subtask', $event)"
          @remove-task="$emit('remove-task', $event)"
          @column-drag-start="onColumnDragStart(colIndex)"
          @column-drag-end="onColumnDragEnd"
        />

        <!-- Drop zone indicator between columns -->
        <div
          v-if="dropTargetColIndex === colIndex && draggingColIndex !== colIndex && draggingColIndex !== colIndex - 1"
          class="absolute left-0 top-0 bottom-0 w-1 bg-primary/60 rounded-full -translate-x-2 z-30"
        ></div>
      </div>

      <!-- Empty board state -->
      <div
        v-if="!localColumns.length"
        class="flex flex-col items-center justify-center w-64 h-full text-base-content/20 gap-3"
      >
        <i class="fa-brands fa-trello text-5xl"></i>
        <span class="text-sm">No columns yet</span>
        <button
          v-if="allowNewColumn"
          @click="$emit('new-column')"
          class="btn btn-sm btn-ghost border border-dashed border-base-100 gap-1.5"
        >
          <i class="fa-solid fa-plus text-xs"></i> Add Column
        </button>
      </div>

      <!-- New column CTA -->
      <div
        v-if="localColumns.length && allowNewColumn"
        @click="$emit('new-column')"
        class="flex flex-col items-center justify-center w-52 shrink-0 rounded-xl border border-dashed cursor-pointer gap-2 hover:text-primary transition-all duration-150 self-start min-h-24"
        :class="background
          ? 'border-white/20 text-white/40 bg-black/20 hover:bg-black/30 hover:border-primary/50 backdrop-blur-sm'
          : 'border-base-100 text-base-content/30 hover:border-primary/40'"
      >
        <i class="fa-solid fa-plus text-lg"></i>
        <span class="text-xs font-medium">New Column</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SprintBoardCanvas',
  props: {
    columns: { type: Array, default: () => [] },
    selectedTaskId: { type: String, default: null },
    // When false (virtual board) the columns hide their creation affordances
    allowCreate: { type: Boolean, default: true },
    // Kanban: enable column drag-to-reorder
    allowReorderColumns: { type: Boolean, default: false },
    // Kanban: show the "New Column" CTA / empty state button
    allowNewColumn: { type: Boolean, default: false },
    // Kanban: show the per-column edit button
    allowEditColumn: { type: Boolean, default: false },
    // Show card hover actions (add subtask / remove from sprint)
    allowActions: { type: Boolean, default: true },
    // Kanban: allow within-column task reordering
    reorderable: { type: Boolean, default: false },
    // Kanban: board background image URL
    background: { type: String, default: null }
  },
  emits: [
    'open-task', 'open-task-window', 'move-task', 'new-task', 'new-column',
    'edit-column', 'reorder-columns', 'reorder-tasks', 'add-subtask', 'remove-task'
  ],
  data() {
    return {
      localColumns: [],
      draggingColIndex: null,
      dropTargetColIndex: null
    }
  },
  watch: {
    columns: {
      immediate: true,
      handler(newCols) {
        // Sync local copy when store columns change (but not while dragging)
        if (this.draggingColIndex === null) {
          this.localColumns = [...newCols]
        }
      }
    }
  },
  methods: {
    onColumnDragStart(colIndex) {
      this.draggingColIndex = colIndex
    },
    onColumnDragEnd() {
      this.draggingColIndex = null
      this.dropTargetColIndex = null
    },
    onColumnDragOver(event, colIndex) {
      if (this.draggingColIndex === null) return
      event.dataTransfer.dropEffect = 'move'
      this.dropTargetColIndex = colIndex
    },
    onColumnDrop(event, targetIndex) {
      const fromIndex = this.draggingColIndex
      if (fromIndex === null || fromIndex === targetIndex) {
        this.onColumnDragEnd()
        return
      }

      // Reorder localColumns array
      const reordered = [...this.localColumns]
      const [moved] = reordered.splice(fromIndex, 1)
      reordered.splice(targetIndex, 0, moved)
      this.localColumns = reordered

      this.$emit('reorder-columns', reordered)
      this.onColumnDragEnd()
    },
    onReorderTasks(col, { taskIds }) {
      this.$emit('reorder-tasks', { columnTitle: col.title, taskIds })
    }
  }
}
</script>