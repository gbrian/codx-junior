<script setup>
import KanbanBoardColumn from './KanbanBoardColumn.vue'
</script>

<template>
  <div class="kanban-board-canvas flex flex-col flex-1 min-w-0 overflow-hidden relative">

    <!-- Board background image (Trello-style) -->
    <div
      v-if="boardBackground"
      class="absolute inset-0 z-0 bg-cover bg-center"
      :style="{ backgroundImage: `url(${boardBackground})` }"
    >
      <!-- Dark overlay so columns remain readable -->
      <div class="absolute inset-0 bg-base-100/60 backdrop-blur-[1px]"></div>
    </div>

    <!-- Top bar -->
    <div
      class="shrink-0 flex items-center gap-3 px-4 py-2.5 border-b border-base-100 relative z-10"
      :class="boardBackground ? 'bg-base-200/80 backdrop-blur-sm' : 'bg-base-200'"
    >
      <div class="flex flex-col min-w-0 flex-1">
        <span class="font-semibold text-sm text-base-content truncate">
          {{ activeBoardTitle || 'Select a board' }}
        </span>
        <span class="text-xs text-base-content/40">
          {{ columns.length }} columns · {{ totalTasks }} tasks
        </span>
      </div>

      <div class="flex items-center gap-2 shrink-0">
        <button
          class="btn btn-ghost btn-sm gap-1.5 text-base-content/50"
          title="Filter"
        >
          <i class="fa-solid fa-filter text-xs"></i>
          <span class="hidden sm:inline text-xs">Filter</span>
        </button>

        <button
          @click="$emit('new-task', {})"
          class="btn btn-primary btn-sm gap-1.5"
        >
          <i class="fa-solid fa-plus text-xs"></i>
          <span class="hidden sm:inline text-xs font-medium">New Task</span>
        </button>
      </div>
    </div>

    <!-- Canvas: horizontal scroll columns -->
    <div class="flex-1 min-h-0 overflow-x-auto overflow-y-hidden relative z-10">
      <div class="flex gap-3 h-full p-4 w-max min-w-full">

        <!-- Column components with drag-to-reorder -->
        <div
          v-for="(col, colIndex) in localColumns"
          :key="col.id || col.title"
          class="relative shrink-0 self-start"
          :class="draggingColIndex === colIndex ? 'opacity-40' : ''"
          @dragover.prevent="onColumnDragOver($event, colIndex)"
          @drop.prevent="onColumnDrop($event, colIndex)"
        >
          <!-- Column drag-handle indicator (shown on hover) -->
          <div
            class="absolute top-0 left-0 right-0 h-full z-20 cursor-grab active:cursor-grabbing opacity-0 hover:opacity-100 flex items-start justify-center pt-2 pointer-events-none"
          >
            <span class="bg-base-300/60 rounded px-1.5 py-0.5 text-xs text-base-content/30 select-none pointer-events-none">
              <i class="fa-solid fa-grip-vertical text-xs"></i>
            </span>
          </div>

          <KanbanBoardColumn
            :column="col"
            :selectedTaskId="selectedTaskId"
            :hasBackground="!!boardBackground"
            :isDraggingColumn="draggingColIndex === colIndex"
            @open-task="$emit('open-task', $event)"
            @new-task="$emit('new-task', { column: col.title })"
            @edit-column="$emit('edit-column', col.title)"
            @move-task="$emit('move-task', $event)"
            @reorder-tasks="onReorderTasks(col, $event)"
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
            @click="$emit('new-column')"
            class="btn btn-sm btn-ghost border border-dashed border-base-100 gap-1.5"
          >
            <i class="fa-solid fa-plus text-xs"></i> Add Column
          </button>
        </div>

        <!-- New column CTA -->
        <div
          v-if="localColumns.length"
          @click="$emit('new-column')"
          class="flex flex-col items-center justify-center w-52 shrink-0 rounded-xl border border-dashed cursor-pointer gap-2 hover:text-primary transition-all duration-150 self-start min-h-24"
          :class="boardBackground
            ? 'border-white/20 text-white/40 bg-black/20 hover:bg-black/30 hover:border-primary/50 backdrop-blur-sm'
            : 'border-base-100 text-base-content/30 hover:border-primary/40'"
        >
          <i class="fa-solid fa-plus text-lg"></i>
          <span class="text-xs font-medium">New Column</span>
        </div>

      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    columns: { type: Array, default: () => [] },
    selectedTaskId: { type: String, default: null },
    activeBoardTitle: { type: String, default: null },
    totalTasks: { type: Number, default: 0 },
    boardBackground: { type: String, default: null }
  },
  emits: ['open-task', 'new-task', 'new-column', 'edit-column', 'move-task', 'reorder-columns', 'reorder-tasks'],
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
        // Never resync while dragging (the local order wins until the drop)
        if (this.draggingColIndex !== null) return
        // The store rebuilds the whole column list on every chats change (a
        // chat being opened, a socket event, a status write…). When the columns
        // would render exactly what is already mounted, keep the current list:
        // that stops pushing a new `column` prop down every column (and, through
        // it, a new task array down every card of the board).
        if (this.sameColumns(newCols)) return
        this.localColumns = [...newCols]
      }
    }
  },
  methods: {
    // True when `next` would render exactly what is already mounted.
    //
    // Object identity alone is useless here: the store derives fresh column
    // objects (and fresh task arrays) on every chats change, so the check always
    // failed and every column re-rendered on each chat write. The comparison
    // looks at what the column renders instead: identity/position, header
    // metadata (colour, project, profiles) and the tasks themselves, which must
    // be literally the same chat objects in the same order.
    sameColumns(next) {
      if (next.length !== this.localColumns.length) return false
      return next.every((column, index) => {
        const current = this.localColumns[index]
        if (column === current) return true
        if (!current) return false
        if (column.id !== current.id || column.title !== current.title) return false
        if ((column.color || null) !== (current.color || null)) return false
        if ((column.project_id || null) !== (current.project_id || null)) return false
        if (this.profilesKey(column) !== this.profilesKey(current)) return false
        return this.sameTasks(column.tasks, current.tasks)
      })
    },
    // Stable signature of the profiles a column pre-selects on new tasks
    profilesKey(column) {
      return (column?.profiles || [])
        .map(entry => (entry && typeof entry === 'object' ? entry.name : entry))
        .join('|')
    },
    // Same tasks, same order (compared by object identity)
    sameTasks(next, current) {
      const nextTasks = next || []
      const currentTasks = current || []
      if (nextTasks.length !== currentTasks.length) return false
      return nextTasks.every((task, index) => task === currentTasks[index])
    },
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