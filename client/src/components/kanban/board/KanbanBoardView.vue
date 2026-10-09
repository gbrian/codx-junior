<script setup>
import KanbanBoardSidebar from './KanbanBoardSidebar.vue'
import SprintBoardCanvas from './SprintBoardCanvas.vue'
import SprintBoardModals from './SprintBoardModals.vue'
import SprintBoardView from './SprintBoardView.vue'
import KanbanList from '../KanbanList.vue'
import PlanningView from './PlanningView.vue'
import FollowupView from './FollowupView.vue'
</script>

<template>
  <div class="kanban-board-view flex flex-col h-full overflow-hidden relative">

    <!-- Board list overlay (available from kanban and sprint views) -->
    <transition name="fade-slide">
      <div
        v-if="showBoardList"
        class="absolute inset-0 z-40 bg-base-100 flex flex-col overflow-hidden"
      >
        <!-- Back bar -->
        <div class="shrink-0 flex items-center gap-3 px-4 py-3 border-b border-base-100 bg-base-200">
          <button
            @click="showBoardList = false"
            class="btn btn-ghost btn-sm gap-1.5 text-base-content/60"
          >
            <i class="fa-solid fa-arrow-left text-xs"></i>
            <span class="text-xs">Back to board</span>
          </button>
          <span class="text-xs font-semibold text-base-content/40 uppercase tracking-wide">
            All Boards
          </span>
        </div>

        <!-- KanbanList -->
        <div class="flex-1 overflow-auto p-4">
          <KanbanList
            @select="onSelectBoardFromList"
            @new-board="openNewBoardModal"
            @bookmark="onBookmark"
          />
        </div>
      </div>
    </transition>

    <!-- View switcher (kanban boards only — sprint boards render their own toolbar) -->
    <div
      v-if="!isSprintBoard"
      class="shrink-0 flex items-center gap-1 px-3 py-2 border-b border-base-100 bg-base-200 z-20"
    >
      <button
        v-for="tab in viewTabs"
        :key="tab.id"
        @click="activeView = tab.id"
        class="btn btn-ghost btn-sm gap-2 rounded-lg transition-all duration-150"
        :class="activeView === tab.id ? 'bg-primary/15 text-primary' : 'text-base-content/60 hover:bg-base-content/5'"
      >
        <i :class="tab.icon" class="text-xs"></i>
        <span class="text-xs font-medium">{{ tab.label }}</span>
        <span
          v-if="tab.count != null"
          class="badge badge-xs"
          :class="activeView === tab.id ? 'badge-primary' : 'badge-ghost text-base-content/40'"
        >{{ tab.count }}</span>
      </button>
    </div>

    <!-- ── Kanban board view ── -->
    <div v-show="activeView === 'board' && !isSprintBoard" class="flex-1 min-h-0 flex overflow-hidden relative">
      <!-- Mobile scrim: tapping the canvas collapses the sidebar drawer -->
      <transition name="fade">
        <div
          v-if="sidebarOverlay"
          class="absolute inset-0 z-30 bg-black/50 backdrop-blur-[1px]"
          @click="sidebarCompact = true"
        ></div>
      </transition>

      <!-- Sidebar (overlay drawer on mobile when expanded) -->
      <KanbanBoardSidebar
        :boards="boards"
        :activeBoard="activeBoard"
        :columns="activeColumns"
        :activeColumnFilter="activeColumnFilter"
        :tasks="sidebarTasks"
        :selectedTaskId="selectedTaskId"
        :isCompact="sidebarCompact"
        :searchQuery="searchQuery"
        :class="sidebarOverlay ? 'absolute inset-y-0 left-0 z-40 shadow-2xl' : ''"
        @select-board="onSelectBoard"
        @toggle-column-filter="onToggleColumnFilter"
        @select-task="onSelectTask"
        @new-task="openNewTaskModal"
        @new-board="openNewBoardModal"
        @new-column="openNewColumnModal"
        @update-search="onUpdateSearch"
        @toggle-compact="sidebarCompact = !sidebarCompact"
        @show-board-list="showBoardList = true"
      />

      <!-- Main canvas column -->
      <div class="flex-1 min-w-0 flex flex-col overflow-hidden">
        <!-- Top bar (moved out of the canvas so the canvas stays reusable) -->
        <div class="shrink-0 flex items-center gap-3 px-4 py-2.5 border-b border-base-100 bg-base-200">
          <div class="flex flex-col min-w-0 flex-1">
            <span class="font-semibold text-sm text-base-content truncate">
              {{ activeBoard?.title || 'Select a board' }}
            </span>
            <span class="text-xs text-base-content/40">
              {{ activeColumns.length }} columns · {{ sidebarTasks.length }} tasks
            </span>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            <button
              @click="openEditBoardModal"
              class="btn btn-ghost btn-sm gap-1.5 text-base-content/50"
              title="Board settings"
            >
              <i class="fa-solid fa-gear text-xs"></i>
              <span class="hidden sm:inline text-xs">Board</span>
            </button>

            <button
              class="btn btn-ghost btn-sm gap-1.5 text-base-content/50"
              title="Filter"
            >
              <i class="fa-solid fa-filter text-xs"></i>
              <span class="hidden sm:inline text-xs">Filter</span>
            </button>

            <button
              @click="openNewTaskModal({})"
              class="btn btn-primary btn-sm gap-1.5"
            >
              <i class="fa-solid fa-plus text-xs"></i>
              <span class="hidden sm:inline text-xs font-medium">New Task</span>
            </button>
          </div>
        </div>

        <!-- Shared canvas (SprintBoardCanvas), configured for the kanban board -->
        <SprintBoardCanvas
          class="flex-1 min-h-0"
          :columns="filteredViewColumns"
          :selectedTaskId="selectedTaskId"
          :background="activeBoard?.background || null"
          :allowCreate="true"
          :allowReorderColumns="true"
          :allowNewColumn="true"
          :allowEditColumn="true"
          :allowActions="false"
          :reorderable="true"
          @open-task="onSelectTask"
          @new-task="openNewTaskModal"
          @new-column="openNewColumnModal"
          @edit-column="onEditColumn"
          @move-task="onMoveTask"
          @reorder-columns="onReorderColumns"
          @reorder-tasks="onReorderTasks"
        />
      </div>
    </div>

    <!-- ── Sprint board view ── -->
    <SprintBoardView
      v-if="isSprintBoard && activeView === 'board'"
      class="flex-1 min-h-0"
      :boardId="activeBoardId"
      @open-task="onSelectTask"
      @new-board="openNewBoardModal"
      @edit-board="openEditBoardModal"
      @select-board="onSelectBoard"
      @browse-boards="showBoardList = true"
    />

    <!-- ── Planning view ── -->
    <PlanningView v-if="activeView === 'planning'" class="flex-1 min-h-0" />

    <!-- ── Follow-up view ── -->
    <FollowupView v-if="activeView === 'followup'" class="flex-1 min-h-0" />

    <!-- Modals (shared with the sprint board — SprintBoardModals) -->
    <SprintBoardModals
      ref="modals"
      :boardType="boardModalsType"
      :boardTitle="activeBoard?.title"
      :sprintId="activeBoard?.id"
      :sprintTitle="activeBoard?.title"
      :columns="activeColumns"
      :editingColumn="editingColumn"
      @task-created="onTaskCreated"
      @column-created="onColumnCreated"
      @column-updated="onColumnUpdated"
      @board-created="onBoardCreated"
      @board-updated="onBoardUpdated"
    />
  </div>
</template>

<script>
// Views exposed by this component
const VALID_VIEWS = ['board', 'planning', 'followup']

export default {
  props: {
    project: { type: Object, default: null },
    // Dockview/app panels receive the app params (e.g. { view: 'planning' }).
    // In router mode no prop is passed, so we also read the route query (?view=planning).
    params: { type: Object, default: () => ({}) }
  },
  data() {
    return {
      // The active board lives here (NOT in the store) so several board panels
      // can each show a different board at the same time.
      activeBoardId: null,
      // Board requested through the app params / route, snapshotted once at
      // creation so later app-info writes can't redirect it to the fallback.
      initialRequestedBoardId: null,
      // Whether the requested board has already been applied (see `boards`)
      boardAppliedFromParams: false,
      activeView: 'board',
      sidebarCompact: false,
      activeColumnFilter: 'all',
      selectedTaskId: null,
      searchQuery: '',
      editingColumn: null,
      showBoardList: false
    }
  },
  created() {
    if (this.requestedView) {
      this.activeView = this.requestedView
    }
    // Snapshot the board requested through the app params / route *before* we
    // publish anything, so `syncAppInfo` can't make it point at the fallback.
    this.initialRequestedBoardId = this.resolveRequestedBoardId()
    // Load the board requested through the app params / route; fall back to the
    // first available board when the panel was opened without a specific one.
    this.activeBoardId = this.initialBoardId
    this.boardAppliedFromParams = !!this.initialRequestedBoardId &&
      this.activeBoardId === this.initialRequestedBoardId
    // Mobile: start with the board sidebar collapsed to maximise canvas space
    this.sidebarCompact = this.isMobile
    // Fall back to the board list only when the board view has no active board
    this.showBoardList = this.activeView === 'board' && !this.activeBoardId
    // Publish the board to the app info so the tab shows its name. If the boards
    // were not loaded yet, this re-runs once they arrive (see `boards` watcher).
    this.syncAppInfo()
  },
  computed: {
    // Resolve a requested initial view from app params (multiple shapes) or the route query
    requestedView() {
      const candidates = [
        this.params?.view,
        this.params?.params?.view,
        this.$route?.query?.view
      ]
      return candidates.find(v => VALID_VIEWS.includes(v)) || null
    },
    // Live app host for this panel — read from the store so runtime app-info
    // updates (such as the active board) are reflected without recreating the
    // panel. Falls back to the static panel snapshot.
    app() {
      const snapshot = this.params?.app || this.params?.params?.app || null
      const tabId = snapshot?.tabId
      return (tabId && this.$storex.ui.openApps[tabId]) || snapshot || null
    },
    // Tab id of the app/panel hosting this board view (used to update app info)
    appTabId() {
      return this.app?.tabId || this.params?.params?.app?.tabId || null
    },
    // Resolve the initial board from the board requested through params/route
    // (snapshotted in `created`), falling back to the first available board.
    initialBoardId() {
      const requested = this.initialRequestedBoardId
      if (requested && this.$storex.kanban.boardById(requested)) return requested
      return this.$storex.kanban.allBoards[0]?.id || null
    },
    isMobile() {
      return this.$ui.isMobile
    },
    // On mobile the expanded sidebar floats over the canvas instead of pushing it
    sidebarOverlay() {
      return this.isMobile && !this.sidebarCompact
    },
    boards() {
      return this.$storex.kanban.allBoards
    },
    activeBoard() {
      return this.$storex.kanban.boardById(this.activeBoardId)
    },
    // Sprint boards replace the kanban canvas/sidebar with the sprint shell
    isSprintBoard() {
      return this.activeBoard?.type === 'sprint'
    },
    // Flavour handed to the shared modals (enables the kanban column picker)
    boardModalsType() {
      return this.isSprintBoard ? 'sprint' : 'kanban'
    },
    activeColumns() {
      return this.activeBoard?.columns || []
    },
    viewColumns() {
      return this.$storex.kanban.buildViewColumns(this.activeBoardId, null)
    },
    filteredViewColumns() {
      if (this.activeColumnFilter === 'all') return this.viewColumns
      return this.viewColumns.filter(c => c.title === this.activeColumnFilter)
    },
    boardChats() {
      return this.$storex.kanban.boardChats(this.activeBoardId)
    },
    sidebarTasks() {
      const query = this.searchQuery?.toLowerCase()?.trim()
      const tasks = this.activeColumnFilter === 'all'
        ? this.boardChats
        : this.boardChats.filter(c => (c.column || '--none--') === this.activeColumnFilter)

      if (!query) return tasks

      return tasks.filter(task => {
        const inName = task.name?.toLowerCase().includes(query)
        const inMessages = task.messages?.some(m => m.content?.toLowerCase().includes(query))
        const inFiles = task.file_list?.some(f => f.toLowerCase().includes(query))
        const inProfiles = task.profiles?.some(p => p.toLowerCase().includes(query))
        return inName || inMessages || inFiles || inProfiles
      })
    },
    viewTabs() {
      const planning = this.$storex.planning
      return [
        { id: 'board', label: 'Board', icon: 'fa-solid fa-columns', count: this.sidebarTasks.length },
        { id: 'planning', label: 'Planning', icon: 'fa-solid fa-list-check', count: planning?.allTasks?.length || 0 },
        { id: 'followup', label: 'Follow-up', icon: 'fa-solid fa-chart-line', count: planning?.metrics?.overdue || 0 }
      ]
    }
  },
  watch: {
    // Apply a view requested through params/route (e.g. /kanban?view=planning)
    requestedView(view) {
      this.activeView = view || 'board'
    },
    // Keep the sidebar collapsed whenever we cross into the mobile breakpoint
    isMobile(mobile) {
      this.sidebarCompact = mobile
    },
    // Sprint boards only expose the board view — force it when one is selected.
    // Also keep the app info (tab title) in sync with the active board.
    activeBoard(board) {
      if (board?.type === 'sprint' && this.activeView !== 'board') {
        this.activeView = 'board'
      }
      this.syncAppInfo()
    },
    // If the selected board disappears (deleted / renamed / project change),
    // fall back to the first available board. Also applies a board requested
    // through params that only becomes available after the boards finish
    // loading (reload case), so each panel keeps its own board.
    boards(boards) {
      const requested = this.initialRequestedBoardId
      if (requested && !this.boardAppliedFromParams && this.$storex.kanban.boardById(requested)) {
        this.boardAppliedFromParams = true
        this.activeBoardId = requested
        this.selectedTaskId = null
        this.showBoardList = false
        return
      }
      if (this.activeBoardId && !this.$storex.kanban.boardById(this.activeBoardId)) {
        this.activeBoardId = boards[0]?.id || null
        this.showBoardList = this.activeView === 'board' && !this.activeBoardId
      }
    },
    // Switching back to the board view without an active board shows the board list
    activeView(view) {
      if (view === 'board' && !this.activeBoardId) {
        this.showBoardList = true
      }
    },
    project() {
      // The project changed: the previously requested board no longer applies
      this.boardAppliedFromParams = true
      this.activeBoardId = null
      this.selectedTaskId = null
      this.searchQuery = ''
      this.activeColumnFilter = 'all'
      this.showBoardList = false
    }
  },
  methods: {
    // Board requested through the app params (persisted per panel) or the route
    resolveRequestedBoardId() {
      return [
        // Live app params — updated when the board changes (persisted per panel)
        this.app?.params?.board,
        // Panel params snapshot (kept in sync by `updateAppParams`)
        this.params?.board,
        this.params?.params?.board,
        // Route (router mode)
        this.$route?.params?.board,
        this.$route?.query?.board
      ].find(Boolean) || null
    },
    // Publish the active board to the hosting app's info so the desktop tab can
    // display the board name and the layout restores the same board on reload.
    syncAppInfo() {
      const tabId = this.appTabId
      if (!tabId) return
      // Nothing resolved yet — don't clobber the board persisted in the params
      if (!this.activeBoardId || !this.activeBoard) return
      this.$storex.ui.updateAppParams({
        tabId,
        params: {
          board: this.activeBoardId,
          boardName: this.activeBoard?.title || null
        }
      })
    },
    onSelectBoard(boardId) {
      // A manual selection wins over the board requested through params
      this.boardAppliedFromParams = true
      this.activeBoardId = boardId
      this.selectedTaskId = null
      this.activeColumnFilter = 'all'
      this.showBoardList = false
    },
    onSelectBoardFromList(boardTitle) {
      this.boardAppliedFromParams = true
      this.activeBoardId = boardTitle
      this.selectedTaskId = null
      this.activeColumnFilter = 'all'
      this.showBoardList = false
    },
    onBookmark(board) {
      this.$storex.kanban.toggleBookmark(board.title)
    },
    onToggleColumnFilter(colTitle) {
      this.activeColumnFilter = this.activeColumnFilter === colTitle ? 'all' : colTitle
    },
    onSelectTask(task) {
      this.selectedTaskId = task?.id || null
      if (task) {
        this.$chats.setActiveChat(task)
      }
    },
    onUpdateSearch(query) {
      this.searchQuery = query
    },
    openNewTaskModal(opts = {}) {
      this.$refs.modals?.openNewTask(opts)
    },
    openNewColumnModal() {
      this.editingColumn = null
      this.$refs.modals?.openNewColumn()
    },
    openNewBoardModal() {
      // New boards inherit the current flavour (sprint boards create sprints)
      this.$refs.modals?.openNewBoard({ type: this.isSprintBoard ? 'sprint' : 'kanban' })
    },
    openEditBoardModal() {
      if (!this.activeBoard) return
      this.$refs.modals?.openEditBoard(this.activeBoard)
    },
    onEditColumn(colTitle) {
      const col = this.activeColumns.find(c => c.title === colTitle)
      this.editingColumn = col || null
      this.$refs.modals?.openNewColumn()
    },
    async onMoveTask({ taskId, toColumn }) {
      await this.$storex.kanban.moveTask({ taskId, toColumn })
    },
    async onReorderColumns(reorderedColumns) {
      await this.$storex.kanban.syncColumnOrder({
        boardId: this.activeBoardId,
        viewColumns: reorderedColumns
      })
    },
    async onReorderTasks({ columnTitle, taskIds }) {
      await this.$storex.kanban.reorderTasksInColumn({
        boardId: this.activeBoardId,
        columnTitle,
        taskIds
      })
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
    // Unified task creation — same richness the sprint board offers (initial
    // message, files, attachments, assignees, deadline, cost budget, Run).
    async onTaskCreated(payload) {
      if (!this.activeBoard) return
      const {
        name, column, mode, profiles, llm_model,
        project_id, users, deadline, estimation_cost,
        message, files, attachments, parentId, run
      } = payload

      // Core task (board + destination column + optional parent link)
      const chat = await this.$storex.kanban.newTask({
        name,
        column,
        mode,
        profiles,
        llm_model,
        board: this.activeBoardId,
        parentId: parentId || null,
        project_id: project_id || null
      })
      if (!chat) return

      // Preferences the create payload does not persist are written through the
      // shared metadata endpoint so none of them are silently dropped.
      const updates = {}
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

      this.onSelectTask(chat)
    },
    async onColumnCreated({ title, color }) {
      if (!title?.trim() || !this.activeBoard) return
      await this.$storex.kanban.addColumn({ boardId: this.activeBoardId, title, color })
    },
    async onColumnUpdated({ id, title, color }) {
      if (!this.activeBoard) return
      await this.$storex.kanban.updateColumn({ boardId: this.activeBoardId, id, title, color })
      this.editingColumn = null
    },
    async onBoardCreated({ title, description, type, background }) {
      if (!title?.trim()) return
      const created = await this.$storex.kanban.addBoard({
        title,
        description,
        type,
        background,
        // A board created from the board view becomes a child of the open board
        parent_id: this.activeBoard?.id || null
      })
      if (created) {
        // Open the freshly created (child) board
        this.boardAppliedFromParams = true
        this.activeBoardId = created.title
        this.selectedTaskId = null
        this.activeColumnFilter = 'all'
        this.showBoardList = false
      }
    },
    async onBoardUpdated({ originalTitle, board }) {
      await this.$storex.kanban.saveBoard({ originalTitle, board })
      // Follow the board when it was renamed while being the active one
      if (originalTitle && board.title && originalTitle !== board.title
        && this.activeBoardId === originalTitle) {
        this.boardAppliedFromParams = true
        this.activeBoardId = board.title
      }
    }
  }
}
</script>

<style scoped>
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>