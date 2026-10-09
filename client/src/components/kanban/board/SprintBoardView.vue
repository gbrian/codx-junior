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

      <div class="grow"></div>

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

      <!-- New Task (starts in To Do) -->
      <button v-if="!isVirtualBoard" class="btn btn-sm btn-primary gap-1.5" @click="openNewTask({ status: 'todo' })">
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
      :allowCreate="!isVirtualBoard"
      :selectedTaskId="selectedTaskId"
      :background="activeBoard?.background || null"
      @open-task="$emit('open-task', $event)"
      @move-task="onMoveTask"
      @new-task="openNewTask"
      @add-subtask="onAddSubtask"
      @remove-task="onRemoveTask"
    />

    <!-- ── Modals ── -->
    <SprintBoardModals
      ref="modals"
      :sprintId="boardId"
      :sprintTitle="activeBoardTitle"
      @task-created="onTaskCreated"
      @tasks-added="onTasksAdded"
    />
  </div>
</template>

<script>
export default {
  name: 'SprintBoardView',
  props: {
    // The board shown by this view is owned by the parent component so several
    // boards can be open at once.
    boardId: { type: String, default: null }
  },
  emits: ['new-board', 'open-task', 'browse-boards', 'edit-board', 'select-board'],
  data() {
    return {
      searchQuery: ''
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
    selectedTaskId() {
      return this.$storex.chats.activeChatId || null
    },
    // Fixed status columns from the kanban store (virtual board includes them)
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
      const done = this.columns.find(c => c.value === 'done')
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
      await this.$storex.kanban.removeTaskFromSprint({ taskId: task.id, sprintId: this.boardId })
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
        await this.$storex.chats.updateChatInfo({ chat, updates })
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
          await this.$storex.projects.chatWihProject(chat)
        }
      }
    },
    async onTasksAdded({ taskIds }) {
      await this.$storex.kanban.addTasksToSprint({ taskIds, sprintId: this.boardId })
    }
  }
}
</script>