<script setup>
import SprintBoardCanvas from './SprintBoardCanvas.vue'
import SprintBoardModals from './SprintBoardModals.vue'
</script>

<template>
  <div class="sprint-board-view flex flex-col h-full min-h-0 overflow-hidden">

    <!-- ── Sprint header / selector ── -->
    <div class="shrink-0 flex items-center gap-2 px-4 py-2.5 border-b border-base-100">
      <div class="dropdown">
        <button tabindex="0" role="button" class="btn btn-sm btn-ghost gap-2" title="Switch sprint">
          <i class="fa-solid fa-calendar-days text-xs text-primary"></i>
          <span class="font-medium text-sm truncate max-w-[16rem]">{{ activeBoardTitle }}</span>
          <span class="badge badge-xs badge-primary badge-outline gap-1">
            <i class="fa-solid fa-layer-group text-[8px]"></i> sprint
          </span>
          <i class="fa-solid fa-chevron-down text-xs opacity-60"></i>
        </button>
        <ul
          tabindex="0"
          class="dropdown-content menu bg-base-200 border border-base-100 rounded-box z-40 w-72 p-1 mt-1 shadow-lg"
        >
          <li class="menu-title text-xs opacity-50">Sprint boards</li>
          <li v-for="b in sprintBoards" :key="b.id">
            <a
              class="flex items-center gap-2"
              :class="activeBoard?.id === b.id ? 'active' : ''"
              @click="onSelectSprint(b.id)"
            >
              <i :class="['fa-solid fa-calendar-days text-xs', activeBoard?.id === b.id ? 'text-primary' : 'opacity-40']"></i>
              <span class="text-sm truncate">{{ b.title }}</span>
            </a>
          </li>
          <li v-if="!sprintBoards.length" class="menu-title text-xs opacity-40">No sprints yet</li>
        </ul>
      </div>

      <button
        class="btn btn-ghost btn-xs gap-1.5 text-base-content/40 hover:text-primary"
        @click="$emit('browse-boards')"
      >
        <i class="fa-solid fa-table-list text-xs"></i>
        <span class="hidden sm:inline text-xs">All boards</span>
      </button>

      <div class="grow"></div>

      <button
        class="btn btn-ghost btn-xs gap-1.5 text-base-content/40 hover:text-primary"
        @click="$emit('new-board')"
      >
        <i class="fa-solid fa-plus text-xs"></i>
        <span class="hidden sm:inline text-xs">New sprint</span>
      </button>
    </div>

    <!-- ── Toolbar ── -->
    <div class="shrink-0 flex flex-wrap items-center gap-2 px-4 py-2.5 border-b border-base-100">
      <div class="min-w-0 flex flex-col">
        <span class="text-sm font-semibold truncate">{{ activeBoardTitle }}</span>
        <span class="text-xs text-base-content/40">{{ totalTasks }} tasks · {{ doneCount }} done</span>
      </div>

      <div class="grow"></div>

      <!-- Search -->
      <label class="input input-sm input-bordered flex items-center gap-2 w-52">
        <i class="fa-solid fa-magnifying-glass text-xs text-base-content/40"></i>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search tasks…"
          class="grow bg-transparent outline-none text-xs min-w-0"
        />
        <button v-if="searchQuery" class="btn btn-ghost btn-xs btn-circle" @click="searchQuery = ''">
          <i class="fa-solid fa-xmark text-xs"></i>
        </button>
      </label>

      <!-- Add existing -->
      <button class="btn btn-sm btn-ghost border border-base-100 gap-1.5" @click="openAddExisting">
        <i class="fa-solid fa-folder-plus text-xs"></i>
        <span class="text-xs font-medium">Add existing</span>
      </button>

      <!-- New Task (starts in To Do) -->
      <button class="btn btn-sm btn-primary gap-1.5" @click="openNewTask({ status: 'todo' })">
        <i class="fa-solid fa-plus text-xs"></i>
        <span class="text-xs font-medium">New Task</span>
      </button>
    </div>

    <!-- ── Progress + total cost ── -->
    <div class="shrink-0 flex items-center gap-3 px-4 py-2 border-b border-base-100">
      <progress class="progress progress-primary h-1.5 w-full max-w-md" :value="progress" max="100"></progress>
      <span class="text-xs text-base-content/40 shrink-0">{{ progress }}% done</span>

      <!-- Total cost of the sprint (sum of every column) -->
      <span
        class="ml-auto flex items-center gap-1 text-xs font-semibold shrink-0 tabular-nums tooltip tooltip-bottom"
        :class="totalCost > 0 ? 'text-amber-400' : 'text-base-content/30'"
        :data-tip="costTooltip"
      >
        <i class="fa-solid fa-coins text-xs"></i>
        {{ formatCoins(totalCost) }}
        <span v-if="totalBudget > 0" class="opacity-60 font-normal">/ {{ formatCoins(totalBudget) }}</span>
      </span>
    </div>

    <!-- ── Canvas ── -->
    <SprintBoardCanvas
      class="flex-1 min-h-0"
      :columns="filteredColumns"
      :selectedTaskId="selectedTaskId"
      @open-task="$emit('open-task', $event)"
      @move-task="onMoveTask"
      @new-task="openNewTask"
      @add-subtask="onAddSubtask"
      @remove-task="onRemoveTask"
    />

    <!-- ── Modals ── -->
    <SprintBoardModals
      ref="modals"
      :sprintId="activeBoard?.id"
      :sprintTitle="activeBoardTitle"
      @task-created="onTaskCreated"
      @tasks-added="onTasksAdded"
    />
  </div>
</template>

<script>
export default {
  name: 'SprintBoardView',
  emits: ['new-board', 'open-task', 'browse-boards'],
  data() {
    return {
      searchQuery: ''
    }
  },
  computed: {
    activeBoard() {
      return this.$storex.kanban.activeKanbanBoard
    },
    activeBoardTitle() {
      return this.activeBoard?.title || 'Sprint'
    },
    sprintBoards() {
      return this.$storex.kanban.sprintBoards
    },
    selectedTaskId() {
      return this.$storex.chats.activeChatId || null
    },
    // Fixed status columns from the kanban store
    columns() {
      return this.$storex.kanban.sprintColumns
    },
    filteredColumns() {
      const q = this.searchQuery?.trim().toLowerCase()
      if (!q) return this.columns
      return this.columns.map(col => ({
        ...col,
        tasks: col.tasks.filter(t =>
          `${t.name || ''} ${t.description || ''}`.toLowerCase().includes(q)
        )
      }))
    },
    totalTasks() {
      return this.columns.reduce((n, col) => n + col.tasks.length, 0)
    },
    doneCount() {
      const done = this.columns.find(c => c.value === 'done')
      return done ? done.tasks.length : 0
    },
    progress() {
      return this.totalTasks ? Math.round((this.doneCount / this.totalTasks) * 100) : 0
    },
    // Total cost (cxjcoins) spent across every task of the sprint
    totalCost() {
      return this.columns.reduce((sum, col) =>
        sum + (col.tasks || []).reduce((s, t) => s + (t.cost || 0), 0), 0)
    },
    // Sum of all task budgets, when defined
    totalBudget() {
      return this.columns.reduce((sum, col) =>
        sum + (col.tasks || []).reduce((s, t) => s + (t.estimation_cost || 0), 0), 0)
    },
    costTooltip() {
      const label = `${this.totalTasks} task${this.totalTasks === 1 ? '' : 's'}`
      if (this.totalBudget > 0) {
        return `Total sprint cost: ${this.formatCoins(this.totalCost)} of ${this.formatCoins(this.totalBudget)} cxjcoins (${label})`
      }
      return `Total sprint cost: ${this.formatCoins(this.totalCost)} cxjcoins (${label})`
    }
  },
  methods: {
    formatCoins(val) {
      if (val == null) return '-'
      if (val >= 1_000_000) return (val / 1_000_000).toFixed(2) + 'M'
      if (val >= 1_000) return (val / 1_000).toFixed(2) + 'K'
      return Number(val).toFixed(2)
    },
    onSelectSprint(boardId) {
      this.$storex.kanban.setActiveBoard(boardId)
      document.activeElement?.blur()
    },
    openNewTask(opts = {}) {
      this.$refs.modals?.openNewTask(opts)
    },
    openAddExisting() {
      this.$refs.modals?.openAddExisting()
    },
    onAddSubtask(task) {
      // "+" on a card → create a subtask linked to that task
      this.openNewTask({ parentId: task.id })
    },
    async onMoveTask({ taskId, status }) {
      await this.$storex.kanban.moveSprintStatus({ taskId, status })
    },
    async onRemoveTask(task) {
      await this.$storex.kanban.removeTaskFromSprint({ taskId: task.id })
    },
    async onTaskCreated(payload) {
      const chat = await this.$storex.kanban.newSprintTask(payload)
      if (chat) this.$emit('open-task', chat)
    },
    async onTasksAdded({ taskIds }) {
      await this.$storex.kanban.addTasksToSprint({ taskIds })
    }
  }
}
</script>