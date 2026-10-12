<script setup>
import SprintTaskCard from './SprintTaskCard.vue'
</script>

<template>
  <!--
    Shared board column. Serves both:
      • Sprint status columns (column.value / icon / borderColor / textColor)
      • Kanban custom columns  (column.title / color, editable, reorderable)
    The sprint implementation (latest behaviour) is the base; kanban-only
    affordances are opt-in through props.
  -->
  <div
    class="kanban-board-column flex flex-col rounded-xl border-1 border-base-content/30 w-64 shrink-0 self-start max-h-full transition-colors duration-150"
    :class="columnClasses"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <!-- Column header (drag handle for column reordering when `draggable`) -->
    <div
      class="flex items-center gap-2 px-3 py-2.5 border-b border-base-100 shrink-0"
      :class="[
        column.borderColor ? `border-l-4 rounded-tl-xl ${column.borderColor}` : '',
        draggable ? 'cursor-grab active:cursor-grabbing select-none' : ''
      ]"
      :draggable="draggable"
      @dragstart="draggable ? onColumnDragStart($event) : null"
      @dragend="draggable ? $emit('column-drag-end') : null"
    >
      <i v-if="draggable" class="fa-solid fa-grip-vertical text-xs text-base-content/20 shrink-0"></i>

      <!-- Status icon (sprint) -->
      <i v-if="column.icon" :class="[column.icon, column.textColor, 'text-xs shrink-0']"></i>
      <!-- Color dot (kanban) -->
      <span
        v-else
        class="w-2 h-2 rounded-full shrink-0"
        :style="column.color ? `background: ${column.color}` : ''"
        :class="!column.color ? 'bg-base-content/20' : ''"
      ></span>

      <span class="text-xs text-base-content/30 bg-base-100 rounded-full px-1.5 shrink-0">
        {{ localTasks.length }}
      </span>
      <span class="text-xs font-semibold text-base-content/70 flex-1 truncate">
        {{ column.title }}
      </span>

      <!-- Accumulated cost of the tasks in this column (sprint) -->
      <span
        v-if="totalCost > 0"
        class="flex items-center gap-0.5 text-xs font-semibold text-amber-400 shrink-0 tabular-nums tooltip tooltip-bottom"
        :data-tip="costTooltip"
      >
        <i class="fa-solid fa-coins text-[10px]"></i>{{ formatCoins(totalCost) }}
      </span>

      <button
        v-if="allowCreate"
        @click.stop="$emit('new-task')"
        class="btn btn-ghost btn-xs rounded-md h-5 min-h-0 px-1 text-base-content/30 hover:text-primary"
        title="Add task"
        draggable="false"
      >
        <i class="fa-solid fa-plus text-xs"></i>
      </button>
      <button
        v-if="allowEdit"
        @click.stop="$emit('edit-column')"
        class="btn btn-ghost btn-xs rounded-md h-5 min-h-0 px-1 text-base-content/20 hover:text-base-content/60"
        title="Edit column"
        draggable="false"
      >
        <i class="fa-solid fa-ellipsis text-xs"></i>
      </button>
    </div>

    <!-- Tasks (sortable when `reorderable`) -->
    <div
      class="flex flex-col gap-2 p-2 overflow-y-auto flex-1 min-h-0"
      @dragover.prevent="onTaskListDragOver"
      @drop.prevent="onTaskListDrop"
    >
      <div
        v-for="(task, taskIndex) in localTasks"
        :key="task.id"
        class="group relative cursor-pointer"
        draggable="true"
        @dragstart="onTaskDragStart($event, task, taskIndex)"
        @dragend="onTaskDragEnd"
        @dragover.prevent.stop="onTaskDragOver($event, taskIndex)"
        @drop.prevent.stop="onTaskDrop($event, taskIndex)"
      >
        <!-- Drop indicator above this task (reorder) -->
        <div
          v-if="reorderable && taskDropIndex === taskIndex && draggingTaskIndex !== taskIndex && draggingTaskIndex !== taskIndex - 1"
          class="h-0.5 bg-primary/60 rounded-full mb-1 mx-1"
        ></div>

        <SprintTaskCard
          :task="task"
          :selected="selectedTaskId === task.id"
          :showActions="allowActions"
          class="transition-all duration-150"
          :class="draggingTaskId === task.id ? 'opacity-40' : ''"
          @open="$emit('open-task', task)"
          @open-window="$emit('open-task-window', task)"
          @add-subtask="$emit('add-subtask', task)"
          @remove="$emit('remove-task', task)"
        />
      </div>

      <!-- Empty column drop hint -->
      <div
        v-if="!localTasks.length"
        class="flex items-center justify-center h-20 rounded-lg border-2 border-dashed text-xs transition-colors duration-150"
        :class="isDragOver
          ? 'border-primary/50 text-primary/60 bg-primary/5'
          : 'border-base-100 text-base-content/20'"
      >
        {{ isDragOver ? 'Drop here' : 'No tasks' }}
      </div>
    </div>

    <!-- Footer: Add task -->
    <div v-if="allowCreate" class="shrink-0 p-2 border-t border-base-100">
      <button
        @click="$emit('new-task')"
        class="btn btn-ghost btn-xs w-full gap-1.5 text-base-content/30 hover:text-primary border border-dashed border-base-100 hover:border-primary/30 transition-all"
      >
        <i class="fa-solid fa-plus text-xs"></i> Add task
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SprintBoardColumn',
  props: {
    column: { type: Object, required: true },
    selectedTaskId: { type: String, default: null },
    // Creation affordances (header "+" and footer "Add task")
    allowCreate: { type: Boolean, default: true },
    // Kanban: show the per-column edit (ellipsis) button
    allowEdit: { type: Boolean, default: false },
    // Show the card hover actions (add subtask / remove from sprint)
    allowActions: { type: Boolean, default: true },
    // Kanban: allow within-column task reordering
    reorderable: { type: Boolean, default: false },
    // Kanban: the header acts as a drag handle for column reordering
    draggable: { type: Boolean, default: false },
    // Rendering over a board background image
    hasBackground: { type: Boolean, default: false }
  },
  emits: [
    'open-task', 'open-task-window', 'move-task', 'new-task', 'edit-column',
    'reorder-tasks', 'remove-task', 'add-subtask', 'column-drag-start', 'column-drag-end'
  ],
  data() {
    return {
      isDragOver: false,
      draggingTaskId: null,
      draggingTaskIndex: null,
      taskDropIndex: null,
      localTasks: [],
      // Prevents the store-driven watcher from reverting a local reorder while
      // the save round-trip is in flight
      pendingReorder: false
    }
  },
  computed: {
    tasks() {
      return this.column.tasks || []
    },
    columnClasses() {
      const surface = this.hasBackground
        ? 'border-base-100 bg-base-200/80 backdrop-blur-md shadow-xl'
        : 'border-base-100 bg-base-100'
      return this.isDragOver ? 'border-primary/50 bg-primary/5' : surface
    },
    // Accumulated cost (cxj) of every task in this column
    totalCost() {
      return this.tasks.reduce((sum, t) => sum + (t.cost || 0), 0)
    },
    // Sum of the per-task budgets, when the tasks define one
    totalBudget() {
      return this.tasks.reduce((sum, t) => sum + (t.estimation_cost || 0), 0)
    },
    costTooltip() {
      const count = this.tasks.length
      const label = `${count} task${count === 1 ? '' : 's'}`
      if (this.totalBudget > 0) {
        return `Accumulated cost: ${this.formatCoins(this.totalCost)} of ${this.formatCoins(this.totalBudget)} cxj (${label})`
      }
      return `Accumulated cost: ${this.formatCoins(this.totalCost)} cxj (${label})`
    }
  },
  watch: {
    tasks: {
      immediate: true,
      handler(newTasks) {
        // Skip sync while actively dragging or while a reorder save is pending
        if (this.draggingTaskIndex !== null || this.pendingReorder) return
        this.localTasks = [...newTasks]
      }
    }
  },
  methods: {
    formatCoins(val) {
      if (val == null) return '-'
      if (val >= 1_000_000) return (val / 1_000_000).toFixed(2) + 'M'
      if (val >= 1_000) return (val / 1_000).toFixed(2) + 'K'
      return Number(val).toFixed(2)
    },

    // ── Cross-column move (both boards) ─────────────────────────────────────
    // Emits `{ taskId, toColumn, status }` so the sprint view (status) and the
    // kanban view (toColumn) each pick what they need.
    emitMove(taskId) {
      if (!taskId) return
      this.$emit('move-task', {
        taskId,
        toColumn: this.column.title,
        status: this.column.value || null
      })
    },
    onDragOver(event) {
      // Only react to a task being dragged (kanban sets `taskId`, sprint `sprintTaskId`)
      const types = Array.from(event.dataTransfer.types || [])
      if (types.includes('taskid') || types.includes('sprinttaskid')) {
        event.dataTransfer.dropEffect = 'move'
        this.isDragOver = true
      }
    },
    onDragLeave() {
      this.isDragOver = false
      this.taskDropIndex = null
    },
    onDrop(event) {
      const taskId = this.readTaskId(event)
      const fromColumn = event.dataTransfer.getData('fromColumn')
      this.isDragOver = false
      this.draggingTaskId = null
      this.draggingTaskIndex = null
      this.taskDropIndex = null
      // Same-column drop is a no-op here (handled by the task list reorder)
      if (!taskId || fromColumn === this.column.title) return
      this.emitMove(taskId)
    },

    // ── Column drag (canvas reordering) ─────────────────────────────────────
    onColumnDragStart(event) {
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('columnDrag', this.column.title)
      this.$emit('column-drag-start')
    },

    // ── Task drag: cross-column AND within-column reorder ───────────────────
    onTaskDragStart(event, task, taskIndex) {
      this.draggingTaskId = task.id
      this.draggingTaskIndex = taskIndex
      event.dataTransfer.effectAllowed = 'move'
      // Keys understood by both boards (kanban `taskId`, sprint `sprintTaskId`)
      event.dataTransfer.setData('taskId', task.id)
      event.dataTransfer.setData('sprintTaskId', task.id)
      event.dataTransfer.setData('fromColumn', this.column.title)
      event.dataTransfer.setData('text/plain', task.id)
    },
    onTaskDragEnd() {
      this.draggingTaskId = null
      this.draggingTaskIndex = null
      this.taskDropIndex = null
      this.isDragOver = false
    },
    onTaskDragOver(event, taskIndex) {
      // Only handle if dragging a task from this same column
      if (this.draggingTaskIndex === null) return
      this.taskDropIndex = taskIndex
    },
    onTaskDrop(event, targetIndex) {
      const fromIndex = this.draggingTaskIndex
      if (fromIndex === null) {
        this.onTaskDragEnd()
        return
      }

      // Cross-column drop — let the store move it
      const fromColumn = event.dataTransfer.getData('fromColumn')
      if (fromColumn && fromColumn !== this.column.title) {
        const taskId = this.readTaskId(event)
        this.isDragOver = false
        this.draggingTaskId = null
        this.draggingTaskIndex = null
        this.emitMove(taskId)
        return
      }

      // Same-column reorder — kanban only
      if (!this.reorderable || fromIndex === targetIndex) {
        this.onTaskDragEnd()
        return
      }

      const reordered = [...this.localTasks]
      const [moved] = reordered.splice(fromIndex, 1)
      reordered.splice(targetIndex, 0, moved)
      this.localTasks = reordered

      // Mark pending so the watcher doesn't overwrite localTasks while the
      // async save resolves and triggers a store update
      this.pendingReorder = true
      this.$emit('reorder-tasks', { taskIds: reordered.map(t => t.id) })
      setTimeout(() => { this.pendingReorder = false }, 2000)

      this.onTaskDragEnd()
    },
    onTaskListDragOver() {
      // Dragging over the empty area at the bottom of the task list
      if (this.draggingTaskIndex !== null) {
        this.taskDropIndex = this.localTasks.length
      }
    },
    onTaskListDrop(event) {
      const fromColumn = event.dataTransfer.getData('fromColumn')
      if (fromColumn && fromColumn !== this.column.title) {
        // Cross-column drop into empty space
        const taskId = this.readTaskId(event)
        this.isDragOver = false
        this.draggingTaskId = null
        this.draggingTaskIndex = null
        this.emitMove(taskId)
        return
      }
      // Same-column drop at the end (reorder)
      if (this.reorderable && this.draggingTaskIndex !== null && this.taskDropIndex === this.localTasks.length) {
        this.onTaskDrop(event, this.localTasks.length)
      }
    },

    // Read a dragged task id from either board's dataTransfer key
    readTaskId(event) {
      return event.dataTransfer.getData('taskId')
        || event.dataTransfer.getData('sprintTaskId')
        || event.dataTransfer.getData('text/plain')
    }
  }
}
</script>