<script setup>
import KanbanBoardSidebar from './KanbanBoardSidebar.vue'
import KanbanBoardCanvas from './KanbanBoardCanvas.vue'
import KanbanBoardModals from './KanbanBoardModals.vue'
import KanbanList from '../KanbanList.vue'
</script>

<template>
  <div class="kanban-board-view flex h-full overflow-hidden bg-base-100 relative">

    <!-- Board list overlay (triggered from sidebar search icon) -->
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

    <!-- Sidebar -->
    <KanbanBoardSidebar
      :boards="boards"
      :activeBoard="activeBoard"
      :columns="activeColumns"
      :activeColumnFilter="activeColumnFilter"
      :tasks="sidebarTasks"
      :selectedTaskId="selectedTaskId"
      :isCompact="sidebarCompact"
      :searchQuery="searchQuery"
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

    <!-- Main canvas -->
    <KanbanBoardCanvas
      :columns="filteredViewColumns"
      :selectedTaskId="selectedTaskId"
      :activeBoardTitle="activeBoard?.title"
      :totalTasks="sidebarTasks.length"
      :boardBackground="activeBoard?.background || null"
      @open-task="onSelectTask"
      @new-task="openNewTaskModal"
      @new-column="openNewColumnModal"
      @edit-column="onEditColumn"
      @move-task="onMoveTask"
      @reorder-columns="onReorderColumns"
      @reorder-tasks="onReorderTasks"
    />

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
export default {
  props: {
    project: { type: Object, default: null }
  },
  data() {
    return {
      sidebarCompact: false,
      activeColumnFilter: 'all',
      selectedTaskId: null,
      searchQuery: '',
      editingColumn: null,
      showBoardList: false
    }
  },
  created() {
    this.showBoardList = !this.activeBoard?.title
  },
  computed: {
    boards() {
      return this.$storex.kanban.allBoards
    },
    activeBoard() {
      return this.$storex.kanban.activeKanbanBoard
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
  },
  watch: {
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
        // Open the newly created task immediately
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
    async onBoardCreated({ title, description }) {
      if (!title?.trim()) return
      await this.$storex.kanban.addBoard({ title, description })
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
</style>