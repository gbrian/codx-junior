<script setup>
import SprintBoardColumn from './SprintBoardColumn.vue'
</script>

<template>
  <div class="sprint-board-canvas flex-1 min-h-0 overflow-x-auto overflow-y-hidden">
    <div class="flex gap-3 h-full p-4 w-max min-w-full">
      <SprintBoardColumn
        v-for="col in columns"
        :key="col.value"
        :column="col"
        :allowCreate="allowCreate"
        :selectedTaskId="selectedTaskId"
        @open-task="$emit('open-task', $event)"
        @move-task="$emit('move-task', $event)"
        @new-task="$emit('new-task', { status: col.value })"
        @add-subtask="$emit('add-subtask', $event)"
        @remove-task="$emit('remove-task', $event)"
      />
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
    allowCreate: { type: Boolean, default: true }
  },
  emits: ['open-task', 'move-task', 'new-task', 'add-subtask', 'remove-task']
}
</script>