<script setup>
import SprintBoardCanvas from './SprintBoardCanvas.vue'
import SprintBoardModals from './SprintBoardModals.vue'
</script>

<template>
  <div class="sprint-board-view flex flex-col h-full min-h-0 overflow-hidden">

    <!-- ── Sprint header / selector ── -->
    <div class="shrink-0 flex items-center gap-2 px-4 py-2.5 border-b border-base-100">
      <div class="dropdown">
        <button tabindex="0" role="button" class="btn btn-sm btn-ghost gap-2" :title="isVirtualBoard ? 'No board chats' : 'Switch sprint'">
          <i :class="['fa-solid text-xs', isVirtualBoard ? 'fa-inbox text-warning' : 'fa-calendar-days text-primary']"></i>
          <span class="font-medium text-sm truncate max-w-[16rem]">{{ activeBoardTitle }}</span>
          <span v-if="isVirtualBoard" class="badge badge-xs badge-warning badge-outline gap-1">
            <i class="fa-solid fa-inbox text-[8px]"></i> no board
          </span>
          <span v-else class="badge badge-xs badge-primary badge-outline gap-1">
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

      <!-- Board wall: recap of this sprint's tasks and events -->
      <button
        class="btn btn-ghost btn-xs gap-1.5 text-base-content/40 hover:text-primary"
        title="Board wall — recap of this sprint's activity"
        aria-label="Board wall"
        @click="$emit('board-wall')"
      >
        <i class="fa-solid fa-newspaper text-xs"></i>
        <span class="hidden sm:inline text-xs">Wall</span>
      </button>

      <div class="grow"></div>

      <!-- Add a column to the sprint (a task status) -->
      <button
        v-if="!isVirtualBoard"
        class="btn btn-ghost btn-xs gap-1.5 text-base-content/40 hover:text-primary"
        title="Add column"
        aria-label="Add column"
        @click="openNewColumn"
      >
        <i class="fa-solid fa-table-columns text-xs"></i>
        <span class="hidden sm:inline text-xs">New column</span>
      </button>

      <!-- Export / import this sprint (with all its tasks) -->
      <button
        v-if="!isVirtualBoard"
        class="btn btn-ghost btn-xs gap-1.5 text-base-content/40 hover:text-primary"
        title="Export or import board"
        aria-label="Export or import board"
        @click="$emit('transfer')"
      >
        <i class="fa-solid fa-right-left text-xs"></i>
        <span class="hidden sm:inline text-xs">Transfer</span>
      </button>

      <!-- Edit the board: name, description, background & participants -->
      <button
        v-if="!isVirtualBoard"
        class="btn btn-ghost btn-xs gap-1.5 text-base-content/40 hover:text-primary"
        @click="$emit('edit-board')"
      >
        <i class="fa-solid fa-gear text-xs"></i>
        <span class="hidden sm:inline text-xs">Board settings</span>
      </button>

      <!-- New sprint is only meaningful for real sprint boards -->
      <button
        v-if="!isVirtualBoard"
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

      <!-- Virtual board: read-only catch-all hint instead of create actions -->
      <span v-if="isVirtualBoard" class="badge badge-sm badge-ghost gap-1.5 text-base-content/50">
        <i class="fa-solid fa-inbox text-xs"></i>
        chats without a board
      </span>

      <!-- Stats toggle (stats panel is hidden by default) -->
      <button
        class="btn btn-ghost btn-xs gap-1.5"
        :class="showStats ? 'text-primary' : 'text-base-content/40 hover:text-primary'"
        :aria-pressed="showStats"
        title="Toggle sprint stats"
        @click="showStats = !showStats"
      >
        <i class="fa-solid fa-chart-simple text-xs"></i>
        <span class="hidden sm:inline text-xs">Stats</span>
      </button>

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
      <button v-if="!isVirtualBoard" class="btn btn-sm btn-ghost border border-base-100 gap-1.5" @click="openAddExisting">
        <i class="fa-solid fa-folder-plus text-xs"></i>
        <span class="text-xs font-medium">Add existing</span>
      </button>

      <!-- New Task (starts in the first column) -->
      <button v-if="!isVirtualBoard" class="btn btn-sm btn-primary gap-1.5" @click="openNewTask()">
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

    <!-- ── Stats panel (hidden by default; toggle in the toolbar) ── -->
    <div
      v-if="showStats"
      class="shrink-0 flex flex-wrap items-stretch gap-3 px-4 py-3 border-b border-base-100 bg-base-200/30"
    >
      <!-- Total days (oldest → newest task) -->
      <div class="flex flex-col justify-center rounded-lg bg-base-200 border border-base-100 px-4 py-2.5 min-w-[8.5rem]">
        <span class="text-[10px] uppercase tracking-wider text-base-content/40 flex items-center gap-1.5">
          <i class="fa-solid fa-calendar-day text-primary text-xs"></i> Duration
        </span>
        <div class="flex items-baseline gap-1 mt-1">
          <span class="text-2xl font-bold tabular-nums leading-none">{{ totalDays }}</span>
          <span class="text-xs text-base-content/40">{{ totalDays === 1 ? 'day' : 'days' }}</span>
        </div>
        <span class="text-[10px] text-base-content/40 mt-1" :title="createdRangeTooltip">{{ createdRangeLabel }}</span>
      </div>

      <!-- Average ticket cost -->
      <div class="flex flex-col justify-center rounded-lg bg-base-200 border border-base-100 px-4 py-2.5 min-w-[8.5rem]">
        <span class="text-[10px] uppercase tracking-wider text-base-content/40 flex items-center gap-1.5">
          <i class="fa-solid fa-coins text-amber-400 text-xs"></i> Avg ticket
        </span>
        <div class="flex items-baseline gap-1 mt-1">
          <span
            class="text-2xl font-bold tabular-nums leading-none"
            :class="averageCost > 0 ? 'text-amber-400' : 'text-base-content/30'"
          >
            {{ formatCoins(averageCost) }}
          </span>
          <span class="text-xs text-base-content/40">cxj</span>
        </div>
        <span class="text-[10px] text-base-content/40 mt-1">
          over {{ totalTasks }} {{ totalTasks === 1 ? 'task' : 'tasks' }}
        </span>
      </div>

      <!-- Tasks per user -->
      <div class="flex flex-col rounded-lg bg-base-200 border border-base-100 px-3 py-2.5 min-w-[15rem] flex-1">
        <span class="text-[10px] uppercase tracking-wider text-base-content/40 flex items-center gap-1.5">
          <i class="fa-solid fa-user text-info text-xs"></i> Tasks per user
          <span class="ml-auto normal-case tracking-normal text-base-content/30">done / total</span>
        </span>
        <div v-if="tasksByUser.length" class="flex flex-col gap-1.5 mt-2 max-h-28 overflow-y-auto pr-1">
          <div v-for="entry in tasksByUser" :key="entry.name" class="flex items-center gap-2">
            <span
              class="w-4 h-4 rounded-full bg-primary/20 text-primary text-[9px] font-semibold flex items-center justify-center shrink-0"
            >{{ initial(entry.name) }}</span>
            <span class="text-xs truncate flex-1 min-w-0" :title="entry.name">{{ entry.name }}</span>
            <progress
              class="progress progress-success h-1 w-12 shrink-0"
              :value="entry.total ? (entry.done / entry.total) * 100 : 0"
              max="100"
            ></progress>
            <span class="text-[10px] tabular-nums text-base-content/50 shrink-0 w-8 text-right">
              {{ entry.done }}/{{ entry.total }}
            </span>
          </div>
        </div>
        <span v-else class="text-[11px] text-base-content/30 mt-2 italic">No assignees</span>
      </div>

      <!-- Tasks per profile -->
      <div class="flex flex-col rounded-lg bg-base-200 border border-base-100 px-3 py-2.5 min-w-[15rem] flex-1">
        <span class="text-[10px] uppercase tracking-wider text-base-content/40 flex items-center gap-1.5">
          <i class="fa-solid fa-user-gear text-secondary text-xs"></i> Tasks per profile
          <span class="ml-auto normal-case tracking-normal text-base-content/30">done / total</span>
        </span>
        <div v-if="tasksByProfile.length" class="flex flex-col gap-1.5 mt-2 max-h-28 overflow-y-auto pr-1">
          <div v-for="entry in tasksByProfile" :key="entry.name" class="flex items-center gap-2">
            <span
              class="w-4 h-4 rounded-full bg-secondary/20 text-secondary text-[9px] font-semibold flex items-center justify-center shrink-0"
            >{{ initial(entry.name) }}</span>
            <span class="text-xs truncate flex-1 min-w-0" :title="entry.name">{{ entry.name }}</span>
            <progress
              class="progress progress-success h-1 w-12 shrink-0"
              :value="entry.total ? (entry.done / entry.total) * 100 : 0"
              max="100"
            ></progress>
            <span class="text-[10px] tabular-nums text-base-content/50 shrink-0 w-8 text-right">
              {{ entry.done }}/{{ entry.total }}
            </span>
          </div>
        </div>
        <span v-else class="text-[11px] text-base-content/30 mt-2 italic">No profiles</span>
      </div>
    </div>

    <!-- ── Canvas ── -->
    <SprintBoardCanvas
      class="flex-1 min-h-0"
      :columns="filteredColumns"
      :allowCreate="!isVirtualBoard"
      :allowNewColumn="!isVirtualBoard"
      :allowEditColumn="!isVirtualBoard"
      :allowReorderColumns="!isVirtualBoard"
      :selectedTaskId="activeSelectionId"
      :background="activeBoard?.background || null"
      @open-task="$emit('open-task', $event)"
      @open-task-window="$emit('open-task-window', $event)"
      @move-task="onMoveTask"
      @new-task="openNewTask"
      @new-column="openNewColumn"
      @edit-column="onEditColumn"
      @reorder-columns="onReorderColumns"
      @add-subtask="onAddSubtask"
      @remove-task="onRemoveTask"
    />

    <!-- ── Modals ── -->
    <SprintBoardModals
      ref="modals"
      boardType="sprint"
      :sprintId="boardId"
      :sprintTitle="activeBoardTitle"
      :columns="columns"
      :allowColumnDelete="!isVirtualBoard"
      @task-created="onTaskCreated"
      @tasks-added="onTasksAdded"
      @column-created="onColumnCreated"
      @column-updated="onColumnUpdated"
      @column-deleted="onColumnDeleted"
    />
  </div>
</template>

<script>
export default {
  name: 'SprintBoardView',
  props: {
    // The board shown by this view is owned by the parent component so several
    // boards can be open at once.
    boardId: { type: String, default: null },
    // Task highlighted by the parent (inline detail pane selection). Falls back
    // to the globally active chat when not provided.
    selectedTaskId: { type: String, default: null }
  },
  emits: ['new-board', 'open-task', 'open-task-window', 'browse-boards', 'edit-board', 'select-board', 'transfer', 'board-wall'],
  data() {
    return {
      searchQuery: '',
      // Sprint stats panel (duration · avg cost · tasks per user/profile).
      // Hidden by default — the toolbar "Stats" button reveals/hides it.
      showStats: false
    }
  },
  computed: {
    activeBoard() {
      return this.$storex.kanban.boardById(this.boardId)
    },
    // True when the synthetic "No board" board is active
    isVirtualBoard() {
      return !!this.activeBoard?.virtual
    },
    activeBoardTitle() {
      return this.activeBoard?.title || 'Sprint'
    },
    sprintBoards() {
      return this.$storex.kanban.sprintBoards
    },
    // Task to highlight: the parent-provided selection wins over the global one
    activeSelectionId() {
      return this.selectedTaskId || this.$storex.chats.activeChatId || null
    },
    // Sprint columns. Real boards expose their own (editable) columns; the
    // virtual board and unedited boards fall back to the canonical statuses.
    columns() {
      return this.$storex.kanban.sprintColumns(this.boardId)
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
      const done = this.columns.find(c => c.status === 'done')
      return done ? done.tasks.length : 0
    },
    progress() {
      return this.totalTasks ? Math.round((this.doneCount / this.totalTasks) * 100) : 0
    },
    // Total cost (cxj) spent across every task of the sprint
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
        return `Total sprint cost: ${this.formatCoins(this.totalCost)} of ${this.formatCoins(this.totalBudget)} cxj (${label})`
      }
      return `Total sprint cost: ${this.formatCoins(this.totalCost)} cxj (${label})`
    },

    // ── Stats ────────────────────────────────────────────────────────────────
    // Every task of the sprint (columns are the single source of grouping)
    allTasks() {
      return this.columns.reduce((acc, col) => acc.concat(col.tasks || []), [])
    },
    // Task creation dates, oldest first
    taskDates() {
      return this.allTasks
        .map(t => t.created_at)
        .filter(Boolean)
        .map(d => new Date(d))
        .filter(d => !Number.isNaN(d.getTime()))
        .sort((a, b) => a - b)
    },
    oldestTaskDate() {
      return this.taskDates[0] || null
    },
    newestTaskDate() {
      return this.taskDates[this.taskDates.length - 1] || null
    },
    // Total days spanned by the sprint: from the oldest task to the newest one
    totalDays() {
      if (!this.oldestTaskDate || !this.newestTaskDate) return 0
      return Math.max(0, Math.round((this.newestTaskDate - this.oldestTaskDate) / 86400000))
    },
    createdRangeLabel() {
      if (!this.oldestTaskDate) return 'No tasks yet'
      const fmt = date => date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
      if (this.totalDays === 0) return `since ${fmt(this.oldestTaskDate)}`
      return `${fmt(this.oldestTaskDate)} → ${fmt(this.newestTaskDate)}`
    },
    createdRangeTooltip() {
      if (!this.oldestTaskDate) return 'No tasks yet'
      const fmt = date => date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
      return `Oldest task: ${fmt(this.oldestTaskDate)} · Newest task: ${fmt(this.newestTaskDate)}`
    },
    // Average cost of a ticket (total spent ÷ number of tasks)
    averageCost() {
      if (!this.totalTasks) return 0
      return this.totalCost / this.totalTasks
    },
    // Tasks grouped by assignee (a task counts once per user it carries)
    tasksByUser() {
      return this.groupTasks(this.allTasks, 'users', 'Unassigned')
    },
    // Tasks grouped by profile (a task counts once per profile it carries)
    tasksByProfile() {
      return this.groupTasks(this.allTasks, 'profiles', 'No profile')
    }
  },
  methods: {
    formatCoins(val) {
      if (val == null) return '-'
      if (val >= 1_000_000) return (val / 1_000_000).toFixed(2) + 'M'
      if (val >= 1_000) return (val / 1_000).toFixed(2) + 'K'
      return Number(val).toFixed(2)
    },
    // First letter of a name, used as the avatar fallback in the stats lists
    initial(name) {
      return (name || '?').trim().charAt(0).toUpperCase() || '?'
    },
    // Group tasks by the values of an array field (`users` / `profiles`), keeping
    // a done and total count per value. Sorted by "done" so whoever closes more
    // tickets comes first. A task with no value is counted under `fallback`.
    groupTasks(tasks, field, fallback) {
      const map = {}
      tasks.forEach(task => {
        const names = task[field]?.length ? task[field] : [fallback]
        names.forEach(name => {
          if (!map[name]) map[name] = { name, total: 0, done: 0 }
          map[name].total += 1
          if (task.status === 'done') map[name].done += 1
        })
      })
      return Object.values(map)
        .sort((a, b) =>
          (b.done - a.done) || (b.total - a.total) || a.name.localeCompare(b.name))
    },
    onSelectSprint(boardId) {
      // The active board lives in the parent component — ask it to switch
      this.$emit('select-board', boardId)
      document.activeElement?.blur()
    },
    openNewTask(opts = {}) {
      // The virtual board is read-only — it must not create tasks
      if (this.isVirtualBoard) return
      this.$refs.modals?.openNewTask(opts)
    },
    openAddExisting() {
      if (this.isVirtualBoard) return
      this.$refs.modals?.openAddExisting()
    },
    // ── Sprint columns ───────────────────────────────────────────────────────
    // A column maps a UI title + color to the chat status it groups. Adding a
    // column defines a new status; removing one migrates its tasks to another
    // column (see the kanban store). The virtual board and unedited fallback
    // boards are handled by the store.
    openNewColumn() {
      if (this.isVirtualBoard) return
      this.$refs.modals?.openNewColumn()
    },
    onEditColumn(columnTitle) {
      if (this.isVirtualBoard) return
      const column = this.columns.find(c =>
        c.title === columnTitle || c.id === columnTitle || c.status === columnTitle)
      this.$refs.modals?.openNewColumn(column || null)
    },
    // Persist a new column order. Sprint columns group tasks by `status`, so
    // only the column order changes — no task is moved between statuses.
    async onReorderColumns(reorderedColumns) {
      if (this.isVirtualBoard || !reorderedColumns?.length) return
      await this.$storex.kanban.syncSprintColumnOrder({
        boardId: this.boardId,
        columns: reorderedColumns
      })
    },
    async onColumnCreated({ title, status, icon, color, profiles }) {
      if (this.isVirtualBoard || !title?.trim()) return
      await this.$storex.kanban.addSprintColumn({
        boardId: this.boardId,
        title,
        status,
        icon,
        color,
        profiles
      })
    },
    async onColumnUpdated({ id, title, status, icon, color, profiles }) {
      if (this.isVirtualBoard || !id) return
      await this.$storex.kanban.updateSprintColumn({
        boardId: this.boardId,
        id,
        title,
        status,
        icon,
        color,
        profiles
      })
    },
    async onColumnDeleted({ id }) {
      if (this.isVirtualBoard || !id) return
      await this.$storex.kanban.removeSprintColumn({ boardId: this.boardId, id })
    },
    onAddSubtask(task) {
      // "+" on a card → create a subtask linked to that task, landing in the
      // same column (status) as its parent.
      if (this.isVirtualBoard) return
      this.openNewTask({ parentId: task.id, status: task.status })
    },
    async onMoveTask({ taskId, status }) {
      await this.$storex.kanban.moveSprintStatus({ taskId, status })
    },
    async onRemoveTask(task) {
      await $storex.kanban.removeTaskFromSprint({ taskId: task.id, sprintId: this.boardId })
    },
    // Fallback content when the task is seeded with files/images but no text.
    // `addMessage` rejects empty content, so this must always be non-empty.
    defaultTaskMessage({ files, attachments }) {
      const names = [
        ...(files || []).map(f => f.split('/').reverse()[0]),
        ...(attachments || []).map(a => a.file_name)
      ].filter(Boolean)
      return names.length
        ? `Work on the attached content:\n${names.map(n => `- ${n}`).join('\n')}`
        : 'Run this task.'
    },
    async onTaskCreated(payload) {
      // `newSprintTask` only understands the core task fields (name, mode,
      // status, parentId, profiles, llm_model). Every other preference the user
      // picked in the dialog — project, assignees, deadline, cost budget and the
      // referenced files — is persisted afterwards through the shared metadata
      // endpoint so none of them are silently dropped.
      const { project_id, users, deadline, estimation_cost, message, files, attachments, profiles, run } = payload
      const chat = await this.$storex.kanban.newSprintTask({ ...payload, sprintId: this.boardId })
      if (!chat) return

      const updates = {}
      if (project_id) updates.project_id = project_id
      if (users?.length) updates.users = users
      if (deadline) updates.deadline = deadline
      if (estimation_cost != null) updates.estimation_cost = estimation_cost
      if (files?.length) updates.file_list = files

      if (Object.keys(updates).length) {
        await $storex.chats.updateChatInfo({ chat, updates })
      }

      // The initial message (text + files + attachments) becomes the task's
      // first user message so the agent has something to work with.
      const hasInitialContent = !!(message || files?.length || attachments?.length)
      if (hasInitialContent) {
        const userMessage = this.$service.chat.getUserMessage({
          message: message || this.defaultTaskMessage({ files, attachments }),
          files: files || [],
          profiles: profiles || [],
          attachments: attachments || [],
          user: this.$user?.username
        })
        await this.$storex.chats.addMessage({ chat, message: userMessage })

        // "Run" → create the task and start processing it immediately
        if (run) {
          await $storex.projects.chatWihProject(chat)
        }
      }
    },
    async onTasksAdded({ taskIds }) {
      await this.$storex.kanban.addTasksToSprint({ taskIds, sprintId: this.boardId })
    }
  }
}
</script>