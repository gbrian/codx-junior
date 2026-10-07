<script setup>
import SprintTaskCard from './SprintTaskCard.vue'
</script>

<template>
  <div
    class="sprint-board-column flex flex-col rounded-xl border w-64 shrink-0 self-start transition-colors duration-150 bg-base-100"
    :class="isDragOver ? 'border-primary/50 bg-primary/5' : 'border-base-100'"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <!-- Header (status icon + text — never colour alone) -->
    <div
      class="flex items-center gap-2 px-3 py-2.5 border-b border-base-100 border-l-4 rounded-tl-xl shrink-0"
      :class="column.borderColor"
    >
      <div class="flex items-center gap-1">
        <i :class="[column.icon, column.textColor, 'text-xs']"></i>
        <span class="text-xs text-base-content/30 bg-base-100 rounded-full">({{ column.tasks.length }})</span>
        <span class="text-xs font-semibold text-base-content/70 flex-1 truncate">{{ column.title }}</span>
      </div>
      <div class="grow"></div>
      <!-- Accumulated cost of the tasks in this column -->
      <span
        v-if="totalCost > 0"
        class="flex items-center gap-0.5 text-xs font-semibold text-amber-400 shrink-0 tabular-nums tooltip tooltip-bottom"
        :data-tip="costTooltip"
      >
        <i class="fa-solid fa-coins text-[10px]"></i>{{ formatCoins(totalCost) }}
      </span>
      <button
        @click="$emit('new-task')"
        class="btn btn-ghost btn-xs rounded-md h-5 min-h-0 px-1 text-base-content/30 hover:text-primary"
        title="Add task"
      >
        <i class="fa-solid fa-plus text-xs"></i>
      </button>
    </div>

    <!-- Tasks -->
    <div class="flex flex-col gap-2 p-2 overflow-y-auto max-h-[calc(100vh-16rem)]">
      <div
        v-for="task in column.tasks"
        :key="task.id"
        draggable="true"
        class="cursor-grab active:cursor-grabbing"
        :class="draggingTaskId === task.id ? 'opacity-40' : ''"
        @dragstart="onDragStart($event, task)"
        @dragend="onDragEnd"
      >
        <SprintTaskCard
          :task="task"
          :selected="selectedTaskId === task.id"
          @open="$emit('open-task', task)"
          @add-subtask="$emit('add-subtask', task)"
          @remove="$emit('remove-task', task)"
        />
      </div>

      <!-- Empty drop hint -->
      <div
        v-if="!column.tasks.length"
        class="flex items-center justify-center h-20 rounded-lg border-2 border-dashed text-xs transition-colors duration-150"
        :class="isDragOver
          ? 'border-primary/50 text-primary/60 bg-primary/5'
          : 'border-base-100 text-base-content/20'"
      >
        {{ isDragOver ? 'Drop here' : 'No tasks' }}
      </div>
    </div>

    <!-- Footer -->
    <div class="shrink-0 p-2 border-t border-base-100">
      <button
        @click="$emit('new-task')"
        class="btn btn-ghost btn-xs w-full gap-1.5 text-base-content/30 hover:text-primary border border-dashed border-base-100 hover:border-primary/30 transition-all"
      >
        <i class="fa-solid fa-plus text-xs"></i> New Task
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SprintBoardColumn',
  props: {
    column: { type: Object, required: true },
    selectedTaskId: { type: String, default: null }
  },
  emits: ['open-task', 'move-task', 'new-task', 'add-subtask', 'remove-task'],
  data() {
    return {
      isDragOver: false,
      draggingTaskId: null
    }
  },
  computed: {
    // Accumulated cost (cxj) of every task in this column
    totalCost() {
      return (this.column.tasks || []).reduce((sum, t) => sum + (t.cost || 0), 0)
    },
    // Sum of the per-task budgets, when the tasks define one
    totalBudget() {
      return (this.column.tasks || []).reduce((sum, t) => sum + (t.estimation_cost || 0), 0)
    },
    costTooltip() {
      const count = this.column.tasks?.length || 0
      const label = `${count} task${count === 1 ? '' : 's'}`
      if (this.totalBudget > 0) {
        return `Accumulated cost: ${this.formatCoins(this.totalCost)} of ${this.formatCoins(this.totalBudget)} cxj (${label})`
      }
      return `Accumulated cost: ${this.formatCoins(this.totalCost)} cxj (${label})`
    }
  },
  methods: {
    formatCoins(val) {
      if (val == null) return '-'
      if (val >= 1_000_000) return (val / 1_000_000).toFixed(2) + 'M'
      if (val >= 1_000) return (val / 1_000).toFixed(2) + 'K'
      return Number(val).toFixed(2)
    },
    onDragOver() {
      this.isDragOver = true
    },
    onDragLeave() {
      this.isDragOver = false
    },
    onDragStart(event, task) {
      this.draggingTaskId = task.id
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('sprintTaskId', task.id)
      event.dataTransfer.setData('text/plain', task.id)
    },
    onDragEnd() {
      this.draggingTaskId = null
      this.isDragOver = false
    },
    onDrop(event) {
      const taskId = event.dataTransfer.getData('sprintTaskId')
        || event.dataTransfer.getData('text/plain')
      // Guard: dropping a card back on its own column is a no-op
      const isOwnActiveDrag = this.draggingTaskId && this.draggingTaskId === taskId
      this.isDragOver = false
      this.draggingTaskId = null
      if (!taskId || isOwnActiveDrag) return
      this.$emit('move-task', { taskId, status: this.column.value })
    }
  }
}
</script>