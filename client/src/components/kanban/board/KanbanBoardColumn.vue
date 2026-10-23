<script setup>
import TaskCard from '../TaskCard.vue'
</script>

<template>
  <div
    class="kanban-board-column flex flex-col rounded-xl border w-60 shrink-0 self-start transition-colors duration-150"
    :class="[
      isDragOver ? 'border-primary/50' : 'border-base-100',
      hasBackground
        ? 'bg-base-200/80 backdrop-blur-md shadow-xl'
        : 'bg-base-200'
    ]"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <!-- Column header — drag handle for column reordering -->
    <div
      class="flex items-center gap-2 px-3 py-2.5 border-b border-base-100 shrink-0 cursor-grab active:cursor-grabbing select-none"
      draggable="true"
      @dragstart="onColumnDragStart"
      @dragend="onColumnDragEnd"
    >
      <i class="fa-solid fa-grip-vertical text-xs text-base-content/20 shrink-0"></i>
      <span
        class="w-2 h-2 rounded-full shrink-0"
        :style="column.color ? `background: ${column.color}` : ''"
        :class="!column.color ? 'bg-base-content/20' : ''"
      ></span>
      <span class="text-xs font-semibold text-base-content/70 flex-1 truncate">
        {{ column.title }}
      </span>
      <span class="text-xs text-base-content/30 bg-base-100 rounded-full px-1.5">
        {{ tasks.length }}
      </span>
      <button
        @click.stop="$emit('new-task')"
        class="btn btn-ghost btn-xs rounded-md h-5 min-h-0 px-1 text-base-content/30 hover:text-primary"
        title="Add task"
        draggable="false"
      >
        <i class="fa-solid fa-plus text-xs"></i>
      </button>
      <button
        @click.stop="$emit('edit-column')"
        class="btn btn-ghost btn-xs rounded-md h-5 min-h-0 px-1 text-base-content/20 hover:text-base-content/60"
        title="Edit column"
        draggable="false"
      >
        <i class="fa-solid fa-ellipsis text-xs"></i>
      </button>
    </div>

    <!-- Tasks (sortable) -->
    <div
      class="flex flex-col gap-2 p-2 overflow-y-auto max-h-[calc(100vh-14rem)]"
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
        @click="$emit('open-task', task)"
      >
        <!-- Drop indicator above this task -->
        <div
          v-if="taskDropIndex === taskIndex && draggingTaskIndex !== taskIndex && draggingTaskIndex !== taskIndex - 1"
          class="h-0.5 bg-primary/60 rounded-full mb-1 mx-1"
        ></div>

        <TaskCard
          :task="task"
          class="border overflow-hidden transition-all duration-150 hover:border-primary/30"
          :class="[
            selectedTaskId === task.id ? 'border-primary/50 bg-primary/5' : 'border-base-100',
            draggingTaskId === task.id ? 'opacity-40' : ''
          ]"
        />
      </div>

      <!-- Empty column drop hint -->
      <div
        v-if="!localTasks.length"
        class="flex items-center justify-center h-12 rounded-lg border-2 border-dashed text-xs transition-colors duration-150"
        :class="isDragOver
          ? 'border-primary/50 text-primary/60 bg-primary/5'
          : 'border-base-100 text-base-content/20'"
      >
        {{ isDragOver ? 'Drop here' : 'No tasks' }}
      </div>
    </div>

    <!-- Footer: Add task -->
    <div class="shrink-0 p-2 border-t border-base-100">
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
  props: {
    column: { type: Object, required: true },
    selectedTaskId: { type: String, default: null },
    hasBackground: { type: Boolean, default: false },
    isDraggingColumn: { type: Boolean, default: false }
  },
  emits: ['open-task', 'new-task', 'edit-column', 'move-task', 'reorder-tasks', 'column-drag-start', 'column-drag-end'],
  data() {
    return {
      isDragOver: false,
      draggingTaskId: null,
      draggingTaskIndex: null,
      taskDropIndex: null,
      localTasks: [],
      // Flag to prevent store-driven watcher from reverting a local reorder
      // while the save is in-flight
      pendingReorder: false
    }
  },
  computed: {
    tasks() {
      return this.column.tasks || []
    }
  },
  watch: {
    tasks: {
      immediate: true,
      handler(newTasks) {
        // Skip sync while actively dragging or while a reorder save is pending
        if (this.draggingTaskIndex !== null || this.pendingReorder) return
        // The store rebuilds every column (and its task array) whenever the
        // chats change — opening a chat, a socket event, a status change…
        // When the cards are literally the same objects nothing changed for
        // this column, so keep the mounted list as-is instead of replacing
        // `localTasks` and re-rendering every card (same data, new array).
        if (this.sameTasks(newTasks)) return
        this.localTasks = [...newTasks]
      }
    }
  },
  methods: {
    // True when `next` holds exactly the tasks already mounted (same objects,
    // same order).
    sameTasks(next) {
      if (next.length !== this.localTasks.length) return false
      return next.every((task, index) => task === this.localTasks[index])
    },
    // ── Column drag (for canvas reordering) ────────────────────────────────
    onColumnDragStart(event) {
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('columnDrag', this.column.title)
      this.$emit('column-drag-start')
    },
    onColumnDragEnd() {
      this.$emit('column-drag-end')
    },

    // ── Task cross-column drag (original behaviour) ─────────────────────────
    onDragOver(event) {
      // Only handle cross-column task drops (not column-level drags)
      if (event.dataTransfer.types.includes('taskid')) {
        event.dataTransfer.dropEffect = 'move'
        this.isDragOver = true
      }
    },
    onDragLeave() {
      this.isDragOver = false
      this.taskDropIndex = null
    },
    onDrop(event) {
      const taskId = event.dataTransfer.getData('taskId')
      const fromColumn = event.dataTransfer.getData('fromColumn')
      this.isDragOver = false
      this.draggingTaskId = null

      if (!taskId || fromColumn === this.column.title) return
      this.$emit('move-task', { taskId, toColumn: this.column.title })
    },

    // ── Task within-column drag (reordering) ────────────────────────────────
    onTaskDragStart(event, task, taskIndex) {
      this.draggingTaskId = task.id
      this.draggingTaskIndex = taskIndex
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('taskId', task.id)
      event.dataTransfer.setData('fromColumn', this.column.title)
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
      if (fromIndex === null || fromIndex === targetIndex) {
        this.onTaskDragEnd()
        return
      }

      // Cross-column task drop — let parent handle it
      const fromColumn = event.dataTransfer.getData('fromColumn')
      if (fromColumn && fromColumn !== this.column.title) {
        const taskId = event.dataTransfer.getData('taskId')
        this.isDragOver = false
        this.draggingTaskId = null
        this.$emit('move-task', { taskId, toColumn: this.column.title })
        return
      }

      // Same-column reorder
      const reordered = [...this.localTasks]
      const [moved] = reordered.splice(fromIndex, 1)
      reordered.splice(targetIndex, 0, moved)
      this.localTasks = reordered

      // Mark pending so the watcher doesn't overwrite localTasks
      // while the async save resolves and triggers a store update
      this.pendingReorder = true
      this.$emit('reorder-tasks', { taskIds: reordered.map(t => t.id) })

      // Clear pending flag after a short delay (enough for the save round-trip)
      setTimeout(() => { this.pendingReorder = false }, 2000)

      this.onTaskDragEnd()
    },
    onTaskListDragOver(event) {
      // When dragging over the empty area at the bottom of the task list
      if (this.draggingTaskIndex !== null) {
        this.taskDropIndex = this.localTasks.length
      }
    },
    onTaskListDrop(event) {
      const fromColumn = event.dataTransfer.getData('fromColumn')
      if (fromColumn && fromColumn !== this.column.title) {
        // Cross-column drop into empty space
        const taskId = event.dataTransfer.getData('taskId')
        this.isDragOver = false
        this.$emit('move-task', { taskId, toColumn: this.column.title })
        return
      }
      // Same-column drop at end
      if (this.draggingTaskIndex !== null && this.taskDropIndex === this.localTasks.length) {
        this.onTaskDrop(event, this.localTasks.length)
      }
    }
  }
}
</script>