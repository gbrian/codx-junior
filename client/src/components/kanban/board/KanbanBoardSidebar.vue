<script setup>
import KanbanBoardTaskRow from './KanbanBoardTaskRow.vue'
</script>

<template>
  <aside
    class="kanban-board-sidebar flex flex-col h-full bg-base-200 border-r border-base-100 transition-all duration-200 shrink-0 overflow-hidden"
    :class="isCompact ? 'w-14' : 'w-64'"
  >

    <!-- ── Header: Board list + column filter ── -->
    <div class="shrink-0 border-b border-base-100" v-show="!isCompact">

      <!-- Board selector -->
      <div class="px-3 pt-3 pb-2">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-bold text-base-content/40 uppercase tracking-widest">
            <i class="fa-brands fa-trello text-primary mr-1.5"></i>Boards
          </span>
          <button
            @click="$emit('new-board')"
            class="btn btn-ghost btn-xs text-base-content/40 hover:text-primary"
            title="New board"
          >
            <i class="fa-solid fa-plus text-xs"></i>
          </button>
        </div>

        <!-- Board rows — scrollable when list is long -->
        <div class="flex flex-col gap-0.5 overflow-y-auto max-h-40 pr-0.5">
          <div
            v-for="board in boards"
            :key="board.id"
            @click="$emit('select-board', board.id)"
            class="flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors duration-150 shrink-0"
            :class="activeBoard?.id === board.id
              ? 'bg-primary/15 border-l-2 border-primary'
              : 'hover:bg-base-content/5'"
          >
            <i
              class="text-xs shrink-0"
              :class="activeBoard?.id === board.id
                ? 'fa-solid fa-circle-dot text-primary'
                : 'fa-regular fa-circle text-base-content/30'"
            ></i>
            <span
              class="text-xs flex-1 truncate font-medium"
              :class="activeBoard?.id === board.id ? 'text-primary' : 'text-base-content/60'"
            >{{ board.title }}</span>
            <span class="text-xs text-base-content/30 bg-base-100 rounded-full px-1.5 shrink-0">
              {{ boardTaskCount(board.id) }}
            </span>
          </div>

          <!-- Empty boards state -->
          <div v-if="!boards.length" class="text-xs text-base-content/30 px-2 py-2 italic">
            No boards yet
          </div>
        </div>
      </div>

      <!-- Column filter pills — always shown when sidebar is expanded -->
      <div class="px-3 pb-2.5 border-t border-base-100/60 pt-2">
        <div class="flex items-center justify-between mb-1.5">
          <span class="text-xs font-bold text-base-content/40 uppercase tracking-widest">
            <i class="fa-solid fa-table-columns text-xs mr-1.5"></i>Columns
          </span>
          <button
            @click="$emit('new-column')"
            class="btn btn-ghost btn-xs text-base-content/30 hover:text-primary"
            title="New column"
          >
            <i class="fa-solid fa-plus text-xs"></i>
          </button>
        </div>

        <div class="flex flex-wrap gap-1.5">
          <!-- All pill -->
          <span
            @click="onAllColumnsClick"
            class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border cursor-pointer transition-colors duration-150"
            :class="activeColumnFilter === 'all'
              ? 'border-primary/40 bg-primary/15 text-primary'
              : 'border-base-100 text-base-content/50 hover:border-primary/30 hover:text-primary'"
          >All</span>

          <!-- Column pills -->
          <span
            v-for="col in columns"
            :key="col.id || col.title"
            @click="$emit('toggle-column-filter', col.title)"
            class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs border cursor-pointer transition-colors duration-150"
            :class="activeColumnFilter === col.title
              ? 'border-primary/40 bg-primary/15 text-primary'
              : 'border-base-100 text-base-content/50 hover:border-primary/30 hover:text-primary'"
          >
            <span
              class="w-1.5 h-1.5 rounded-full shrink-0"
              :style="col.color ? `background: ${col.color}` : ''"
              :class="!col.color ? 'bg-base-content/30' : ''"
            ></span>
            {{ col.title }}
          </span>

          <!-- No columns empty state -->
          <span
            v-if="!columns.length"
            class="text-xs text-base-content/25 italic px-1"
          >No columns yet</span>
        </div>
      </div>

      <!-- Search bar -->
      <div class="px-3 pb-3">
        <label class="input input-sm input-bordered flex items-center gap-2 w-full">
          <i class="fa-solid fa-magnifying-glass text-xs text-base-content/40"></i>
          <input
            type="text"
            :value="searchQuery"
            @input="$emit('update-search', $event.target.value)"
            placeholder="Search tasks…"
            class="grow bg-transparent outline-none text-xs min-w-0"
          />
          <button
            v-if="searchQuery"
            @click="$emit('update-search', '')"
            class="btn btn-ghost btn-xs btn-circle"
          >
            <i class="fa-solid fa-xmark text-xs"></i>
          </button>
        </label>
      </div>
    </div>

    <!-- Compact header -->
    <div v-show="isCompact" class="shrink-0 flex flex-col items-center gap-2 px-1 pt-3 pb-2 border-b border-base-100">
      <button
        @click="$emit('new-board')"
        class="btn btn-ghost btn-xs w-10 h-10 rounded-lg flex items-center justify-center text-base-content/40 hover:text-primary"
        title="Boards"
      >
        <i class="fa-brands fa-trello text-sm"></i>
      </button>
    </div>

    <!-- ── Scrollable task list ── -->
    <div class="flex-1 overflow-y-auto min-h-0 py-1" v-show="!isCompact">

      <!-- Per-column groups -->
      <template v-if="groupedTasks && Object.keys(groupedTasks).length">
        <div
          v-for="(group, colTitle) in groupedTasks"
          :key="colTitle"
          class="mb-3"
        >
          <!-- Column group label -->
          <div class="flex items-center gap-1.5 px-3 py-1 sticky top-0 bg-base-200 z-10">
            <span
              class="w-1.5 h-1.5 rounded-full shrink-0"
              :style="getColumnColor(colTitle) ? `background: ${getColumnColor(colTitle)}` : ''"
              :class="!getColumnColor(colTitle) ? 'bg-base-content/20' : ''"
            ></span>
            <span class="text-xs font-bold text-base-content/40 uppercase tracking-widest">
              {{ colTitle }}
            </span>
            <span class="text-xs text-base-content/20 ml-0.5">{{ group.length }}</span>
          </div>

          <!-- Tasks -->
          <div class="px-2">
            <KanbanBoardTaskRow
              v-for="task in group"
              :key="task.id"
              :task="task"
              :isSelected="selectedTaskId === task.id"
              :columnColor="getColumnColor(colTitle)"
              @select="$emit('select-task', task)"
              @add-subtask="$emit('new-task', { parentId: task.id, column: task.column })"
            />
          </div>
        </div>
      </template>

      <!-- Flat list when column filter is active or search results -->
      <div v-else-if="tasks.length" class="px-2">
        <KanbanBoardTaskRow
          v-for="task in tasks"
          :key="task.id"
          :task="task"
          :isSelected="selectedTaskId === task.id"
          :columnColor="getColumnColor(task.column)"
          @select="$emit('select-task', task)"
          @add-subtask="$emit('new-task', { parentId: task.id, column: task.column })"
        />
      </div>

      <!-- Empty / no results -->
      <div v-else class="flex flex-col items-center gap-2 py-10 px-4 text-center">
        <i class="fa-solid fa-inbox text-2xl text-base-content/20"></i>
        <span class="text-xs text-base-content/30">
          {{ searchQuery ? 'No tasks found' : 'No tasks yet' }}
        </span>
      </div>
    </div>

    <!-- ── Footer: New Task + Collapse ── -->
    <div class="shrink-0 border-t border-base-100 p-2 flex flex-col gap-2">
      <button
        v-show="!isCompact"
        @click="$emit('new-task', {})"
        class="btn btn-sm w-full gap-2 bg-primary/10 border border-primary/25 text-primary hover:bg-primary/20 hover:border-primary/50 transition-all"
      >
        <i class="fa-solid fa-plus text-xs"></i> New Task
      </button>

      <button
        @click="$emit('toggle-compact')"
        class="btn btn-ghost btn-sm w-full flex items-center justify-center gap-1.5 text-base-content/30 hover:text-base-content/60"
        :title="isCompact ? 'Expand sidebar' : 'Collapse sidebar'"
      >
        <i :class="isCompact ? 'fa-solid fa-angle-right' : 'fa-solid fa-angle-left'" class="text-xs"></i>
        <span v-show="!isCompact" class="text-xs">Collapse</span>
      </button>
    </div>
  </aside>
</template>

<script>
export default {
  props: {
    boards: { type: Array, default: () => [] },
    activeBoard: { type: Object, default: null },
    columns: { type: Array, default: () => [] },
    activeColumnFilter: { type: String, default: 'all' },
    tasks: { type: Array, default: () => [] },
    selectedTaskId: { type: String, default: null },
    isCompact: { type: Boolean, default: false },
    searchQuery: { type: String, default: '' }
  },
  emits: ['select-board', 'toggle-column-filter', 'select-task', 'new-task', 'new-board', 'new-column', 'update-search', 'toggle-compact'],
  computed: {
    groupedTasks() {
      // Only group when showing ALL columns with no search
      if (this.activeColumnFilter !== 'all' || this.searchQuery) return null

      const groups = {}
      this.columns.forEach(col => {
        const colTasks = this.tasks.filter(t => (t.column || '--none--') === col.title)
        if (colTasks.length) groups[col.title] = colTasks
      })

      // Tasks with no matching column
      const knownCols = new Set(this.columns.map(c => c.title))
      const orphans = this.tasks.filter(t => !knownCols.has(t.column || '--none--'))
      if (orphans.length) groups['Other'] = orphans

      return Object.keys(groups).length ? groups : null
    }
  },
  methods: {
    boardTaskCount(boardId) {
      return Object.values(this.$storex.chats.chats || {})
        .filter(c => c.board === boardId).length
    },
    getColumnColor(colTitle) {
      const col = this.columns.find(c => c.title === colTitle)
      return col?.color || null
    },
    onAllColumnsClick() {
      if (this.activeColumnFilter !== 'all') {
        this.$emit('toggle-column-filter', this.activeColumnFilter)
      }
    }
  }
}
</script>