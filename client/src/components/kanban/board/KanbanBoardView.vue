<script setup>
import KanbanBoardSidebar from './KanbanBoardSidebar.vue'
import SprintBoardCanvas from './SprintBoardCanvas.vue'
import KanbanBoardModals from './KanbanBoardModals.vue'
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
      @open-task="onSelectTask"
      @new-board="openNewBoardModal"
      @browse-boards="showBoardList = true"
    />

    <!-- ── Planning view ── -->
    <PlanningView v-if="activeView === 'planning'" class="flex-1 min-h-0" />

    <!-- ── Follow-up view ── -->
    <FollowupView v-if="activeView === 'followup'" class="flex-1 min-h-0" />

    <!-- Modals -->
    <KanbanBoardModals
      ref="modals"
      :columns="activeColumns"
      :boards="boards"
      :editingColumn="editingColumn"
      @task-created="onTaskCreated"
      @column-created="onColumnCreated"
      @column-updated="onColumnUpdated"
      @board-created="onBoardCreated"
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
    // Mobile: start with the board sidebar collapsed to maximise canvas space
    this.sidebarCompact = this.isMobile
    // Fall back to the board list only when the board view has no active board
    this.showBoardList = this.activeView === 'board' && !this.activeBoard?.title
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
      return this.$storex.kanban.activeKanbanBoard
    },
    // Sprint boards replace the kanban canvas/sidebar with the sprint shell
    isSprintBoard() {
      return this.activeBoard?.type === 'sprint'
    },
    activeColumns() {
      return this.activeBoard?.columns || []
    },
    viewColumns() {
      return this.$storex.kanban.buildViewColumns(null)
    },
    filteredViewColumns() {
      if (this.activeColumnFilter === 'all') return this.viewColumns
      return this.viewColumns.filter(c => c.title === this.activeColumnFilter)
    },
    boardChats() {
      return this.$storex.kanban.boardChats
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
    // Sprint boards only expose the board view — force it when one is selected
    activeBoard(board) {
      if (board?.type === 'sprint' && this.activeView !== 'board') {
        this.activeView = 'board'
      }
    },
    // Switching back to the board view without an active board shows the board list
    activeView(view) {
      if (view === 'board' && !this.activeBoard?.title) {
        this.showBoardList = true
      }
    },
    project() {
      this.selectedTaskId = null
      this.searchQuery = ''
      this.activeColumnFilter = 'all'
      this.showBoardList = false
    }
  },
  methods: {
    onSelectBoard(boardId) {
      this.$storex.kanban.setActiveBoard(boardId)
      this.selectedTaskId = null
      this.activeColumnFilter = 'all'
    },
    onSelectBoardFromList(boardTitle) {
      this.$storex.kanban.setActiveBoard(boardTitle)
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
      this.$refs.modals?.openNewBoard()
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
      await this.$storex.kanban.syncColumnOrder(reorderedColumns)
    },
    async onReorderTasks({ columnTitle, taskIds }) {
      await this.$storex.kanban.reorderTasksInColumn({ columnTitle, taskIds })
    },
    async onTaskCreated({ name, column, mode, profiles, llm_model }) {
      if (!name?.trim() || !this.activeBoard) return
      const chat = await this.$storex.kanban.newTask({ name, column, mode, profiles, llm_model })
      if (chat) {
        this.onSelectTask(chat)
      }
    },
    async onColumnCreated({ title, color }) {
      if (!title?.trim() || !this.activeBoard) return
      await this.$storex.kanban.addColumn({ title, color })
    },
    async onColumnUpdated({ id, title, color }) {
      if (!this.activeBoard) return
      await this.$storex.kanban.updateColumn({ id, title, color })
      this.editingColumn = null
    },
    async onBoardCreated({ title, description, type }) {
      if (!title?.trim()) return
      await this.$storex.kanban.addBoard({ title, description, type })
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