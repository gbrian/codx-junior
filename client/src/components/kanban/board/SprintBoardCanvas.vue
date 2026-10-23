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
        :key="col.id || col.title || col.status"
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
          @new-task="$emit('new-task', { column: col.title, status: col.status || null })"
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
        // Never resync while dragging (the local order wins until the drop)
        if (this.draggingColIndex !== null) return
        // The store rebuilds the whole column list on every chats change (a
        // chat being opened, a socket event, a status write…). When the columns
        // would render exactly what is already mounted, keep the current list:
        // that stops pushing a new `column` prop down every column (and, through
        // it, re-rendering every card of the board).
        if (this.sameColumns(newCols)) return
        this.localColumns = [...newCols]
      }
    }
  },
  methods: {
    // True when `next` would render exactly what is already mounted.
    //
    // Comparing object identity is not enough: the store derives fresh column
    // objects (and fresh task arrays) on every chats change, so an
    // identity-only check always failed and every column re-rendered on each
    // chat write. The comparison therefore ignores the wrapper identity and
    // looks at what the column actually renders:
    //   • its identity/position (id + title) and status,
    //   • the header metadata (icon, colour, project, profiles),
    //   • the tasks, which must be literally the same chat objects in the same
    //     order (the cards are keyed and compared by identity downstream).
    sameColumns(next) {
      if (next.length !== this.localColumns.length) return false
      return next.every((column, index) => {
        const current = this.localColumns[index]
        if (column === current) return true
        if (!current) return false
        if (column.id !== current.id || column.title !== current.title) return false
        if ((column.status || null) !== (current.status || null)) return false
        if ((column.icon || null) !== (current.icon || null)) return false
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