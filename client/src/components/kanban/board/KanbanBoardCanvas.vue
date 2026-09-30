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

        <!-- Column components -->
        <KanbanBoardColumn
          v-for="col in columns"
          :key="col.id || col.title"
          :column="col"
          :selectedTaskId="selectedTaskId"
          :hasBackground="!!boardBackground"
          @open-task="$emit('open-task', $event)"
          @new-task="$emit('new-task', { column: col.title })"
          @edit-column="$emit('edit-column', col.title)"
          @move-task="$emit('move-task', $event)"
        />

        <!-- Empty board state -->
        <div
          v-if="!columns.length"
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
          v-if="columns.length"
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
  emits: ['open-task', 'new-task', 'new-column', 'edit-column', 'move-task']
}
</script>