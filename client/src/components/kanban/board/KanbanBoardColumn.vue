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
    <!-- Column header -->
    <div class="flex items-center gap-2 px-3 py-2.5 border-b border-base-100 shrink-0">
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
        @click="$emit('new-task')"
        class="btn btn-ghost btn-xs rounded-md h-5 min-h-0 px-1 text-base-content/30 hover:text-primary"
        title="Add task"
      >
        <i class="fa-solid fa-plus text-xs"></i>
      </button>
      <button
        @click="$emit('edit-column')"
        class="btn btn-ghost btn-xs rounded-md h-5 min-h-0 px-1 text-base-content/20 hover:text-base-content/60"
        title="Edit column"
      >
        <i class="fa-solid fa-ellipsis text-xs"></i>
      </button>
    </div>

    <!-- Tasks -->
    <div class="flex flex-col gap-2 p-2 overflow-y-auto max-h-[calc(100vh-14rem)]">
      <div
        v-for="task in tasks"
        :key="task.id"
        class="group relative cursor-pointer"
        draggable="true"
        @dragstart="onDragStart($event, task)"
        @dragend="onDragEnd"
        @click="$emit('open-task', task)"
      >
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
        v-if="!tasks.length"
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
    hasBackground: { type: Boolean, default: false }
  },
  emits: ['open-task', 'new-task', 'edit-column', 'move-task'],
  data() {
    return {
      isDragOver: false,
      draggingTaskId: null
    }
  },
  computed: {
    tasks() {
      return this.column.tasks || []
    }
  },
  methods: {
    onDragStart(event, task) {
      this.draggingTaskId = task.id
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('taskId', task.id)
      event.dataTransfer.setData('fromColumn', this.column.title)
    },
    onDragEnd() {
      this.draggingTaskId = null
      this.isDragOver = false
    },
    onDragOver(event) {
      event.dataTransfer.dropEffect = 'move'
      this.isDragOver = true
    },
    onDragLeave() {
      this.isDragOver = false
    },
    onDrop(event) {
      const taskId = event.dataTransfer.getData('taskId')
      const fromColumn = event.dataTransfer.getData('fromColumn')
      this.isDragOver = false
      this.draggingTaskId = null

      if (!taskId || fromColumn === this.column.title) return
      this.$emit('move-task', { taskId, toColumn: this.column.title })
    }
  }
}
</script>