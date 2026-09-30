<script setup>
import { v4 as uuidv4 } from 'uuid'
import KanbanGridView from './KanbanGridView.vue'
import KanbanFilesView from './KanbanFilesView.vue'
import KanbanList from './KanbanList.vue'
import Collapsible from '../Collapsible.vue'
import ChatHistory from './ChatHistory.vue'
import KanbanBoardModal from './KanbanBoardModal.vue'
import ProjectDetailt from '../ProjectDetailt.vue'
</script>

<template>
  <div class="kanban h-full relative" v-if="kanban">

    <!-- Background image -->
    <div
      class="absolute top-0 left-0 right-0 bottom-0 bg-cover opacity-20 rounded-lg z-0"
      :style="{ backgroundImage: `url(${activeKanbanBoard?.background})` }"
      v-if="activeKanbanBoard?.background"
    />

    <!-- Loading bar -->
    <div class="absolute bottom-0 left-0 right-0 z-20 text-xs" v-if="isLoading">
      <progress class="progress w-full animate-pulse opacity-30"></progress>
    </div>

    <!-- ── Activity panel ── -->
    <transition name="slide-up">
      <div class="absolute inset-0 z-30 flex flex-col bg-base-100" v-if="showActivity">
        <div class="flex gap-2 items-center shrink-0 bg-base-300 z-10 p-2 border-b border-base-200">
          <button class="btn btn-sm btn-ghost" @click="showActivity = false">
            <i class="fa-solid fa-arrow-left"></i>
          </button>
          <div class="text-lg font-semibold truncate">
            Activity<span v-if="project" class="text-base-content/50 font-normal"> · {{ project.project_name }}</span>
          </div>
        </div>
        <div class="flex-1 min-h-0 overflow-auto">
          <ChatHistory :projects="historyProjects" />
        </div>
      </div>
    </transition>

    <!-- ── Main kanban layout ── -->
    <div
      class="h-full absolute top-0 left-0 right-0 bottom-0 z-1 flex flex-col"
      :class="isMobile ? 'pb-14' : ''"
    >
      <!-- ── Top toolbar ── -->
      <div class="flex items-center gap-2 px-2 pt-2 pb-1 shrink-0 min-w-0">

        <!-- Back button -->
        <button class="btn btn-ghost btn-sm shrink-0" @click="$kanban.setActiveBoard(null)">
          <i class="fa-solid fa-circle-arrow-left text-lg"></i>
        </button>

        <!-- Board title + breadcrumb -->
        <div class="flex flex-col min-w-0 flex-1">
          <div v-if="parentBoard?.title" class="hidden sm:block text-xs text-base-content/50 truncate leading-none mb-0.5">
            {{ parentBoard.title }} /
          </div>
          <div class="flex items-center gap-1.5 min-w-0">
            <i
              class="fa-solid fa-bookmark text-sm cursor-pointer shrink-0"
              :class="activeKanbanBoard?.bookmark ? 'text-warning' : 'text-base-content/30'"
              @click="$kanban.toggleBookmark(activeBoard)"
            ></i>
            <span class="font-semibold text-sm sm:text-base truncate">{{ activeBoard }}</span>
          </div>
        </div>

        <!-- Search (desktop) -->
        <div
          class="hidden sm:flex input input-sm input-bordered items-center gap-2 tooltip tooltip-bottom"
          data-tip="Find in tasks"
        >
          <input
            type="text"
            :class="{ hidden: !searchVisible }"
            v-model="filter"
            class="grow"
            placeholder="Search..."
          />
          <span class="cursor-pointer" v-if="filter" @click.stop="clearSearch">
            <i class="fa-regular fa-circle-xmark text-sm"></i>
          </span>
          <i class="fa-solid fa-filter cursor-pointer text-sm" v-else @click="searchVisible = !searchVisible"></i>
        </div>

        <!-- View toggle (desktop) -->
        <div class="hidden sm:flex join tooltip tooltip-bottom" data-tip="Switch view">
          <button
            class="btn btn-sm join-item"
            :class="activeView === 'board' && 'btn-active'"
            @click="activeView = 'board'"
          >
            <i class="fa-solid fa-table-columns"></i>
            <span class="hidden md:inline text-xs ml-1">Board</span>
          </button>
          <button
            class="btn btn-sm join-item"
            :class="activeView === 'files' && 'btn-active'"
            @click="activeView = 'files'"
          >
            <i class="fa-solid fa-file-code"></i>
            <span class="hidden md:inline text-xs ml-1">Files</span>
          </button>
        </div>

        <!-- More options dropdown -->
        <div class="hidden sm:block dropdown dropdown-left">
          <button class="btn btn-sm tooltip tooltip-bottom" data-tip="More options">
            <i class="fa-solid fa-ellipsis-vertical"></i>
          </button>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-50 w-52 p-2 shadow">
            <li>
              <a @click="showChildrenBoards = !showChildrenBoards" :class="{ 'text-warning': showChildrenBoards }">
                <i class="fa-brands fa-trello"></i> Child boards
              </a>
            </li>
            <li>
              <a @click="showActivity = !showActivity">
                <i class="fa-solid fa-clock-rotate-left"></i> Activity
              </a>
            </li>
            <li class="divider my-1"></li>
            <li><a @click="openAddColumnModal"><i class="fa-solid fa-plus"></i> Column</a></li>
            <li><a @click="openNewBoardModal"><i class="fa-solid fa-plus"></i> Board</a></li>
            <li><a @click="openEditBoardModal"><i class="fas fa-cogs"></i> Settings</a></li>
          </ul>
        </div>
      </div>

      <!-- Child boards collapsible -->
      <Collapsible v-if="showChildrenBoards" v-model="childBoardsOpen" class="mx-2 mt-1">
        <template #icon>
          <i class="fa-brands fa-trello text-xs opacity-60"></i>
        </template>
        <template #title>
          Child boards
          <span class="badge badge-sm ml-1">{{ childBoards.length }}</span>
        </template>
        <div class="p-2 overflow-auto">
          <KanbanList
            :boards="childBoards"
            :project="project"
            @new-board="openNewBoardModal"
            @toogle-history="showActivity = !showActivity"
            @select="$kanban.setActiveBoard($event)"
          />
        </div>
      </Collapsible>

      <!-- ── Board / Files views ── -->
      <div class="grow relative flex flex-col gap-2 min-h-0 px-2 pt-1">
        <KanbanGridView
          v-if="activeView === 'board'"
          class="h-full"
          :columns="viewColumns"
          :lastUpdatedTaskId="lastUpdatedTask.id"
          @open-task="openChat"
          @new-task="onNewTask"
          @new-column="openAddColumnModal"
          @edit-column="openEditColumnModal"
          @move-task="onMoveTask"
        />
        <KanbanFilesView
          v-if="activeView === 'files'"
          class="h-full bg-base-300/70"
          :columns="viewColumns"
          @open-task="openChat"
        />
      </div>
    </div>

    <!-- ── Mobile search bar ── -->
    <transition name="slide-down-search">
      <div
        v-if="isMobile && searchVisible"
        class="absolute top-12 left-0 right-0 z-20 px-3 py-2 bg-base-200/95 backdrop-blur border-b border-base-100"
      >
        <div class="input input-sm input-bordered flex items-center gap-2 w-full">
          <i class="fa-solid fa-magnifying-glass opacity-50 text-sm"></i>
          <input
            type="text"
            v-model="filter"
            class="grow bg-transparent outline-none"
            placeholder="Search tasks..."
            autofocus
          />
          <span v-if="filter" class="cursor-pointer" @click="filter = ''">
            <i class="fa-regular fa-circle-xmark text-sm"></i>
          </span>
          <span class="cursor-pointer text-xs font-medium" @click="searchVisible = false">Done</span>
        </div>
      </div>
    </transition>

    <!-- ── Board modal (new/edit/delete) ── -->
    <modal close="true" @close="showBoardModal = false" v-if="showBoardModal">
      <KanbanBoardModal
        :board="editingBoard"
        :boards="parentBoardOptions"
        :currentBoardId="activeBoard"
        :project="project"
        @save="onBoardSave"
        @delete="onBoardDelete"
        @cancel="showBoardModal = false"
      />
    </modal>

    <!-- ── Add/Edit Column modal ── -->
    <modal close="true" @close="resetColumnModal" v-if="showColumnModal">
      <h2 class="font-bold text-lg">{{ selectedColumn ? 'Edit Column' : 'Add Column' }}</h2>
      <div class="flex gap-1 items-center mt-2">
        <input
          type="text"
          v-model="columnTitle"
          placeholder="Enter column name"
          class="grow input input-bordered w-full"
        />
      </div>
      <ProjectDetailt
        v-model="columnProject"
        :options="{ showFolders: false, showIcon: true, showSelector: true }"
        class="mt-2"
      />
      <span v-if="editColumnError" class="text-error text-sm mt-1 block">{{ editColumnError }}</span>
      <div class="modal-action flex flex-col gap-2 mt-4">
        <div class="flex gap-2 w-full">
          <button class="btn btn-error" @click="deleteColumn" v-if="selectedColumn">
            <span v-if="confirmDeleteColumn">Confirm delete?</span>
            <span v-else>Delete</span>
          </button>
          <div class="grow"></div>
          <button class="btn" @click="addOrUpdateColumn">Save</button>
        </div>
        <div class="text-error text-xs p-2" v-if="confirmDeleteColumn">
          Are you sure you want to delete this column? All tasks will be removed.
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  props: ['project'],
  data() {
    return {
      filter: null,
      searchVisible: false,
      activeView: 'board',
      showActivity: false,
      showBoardModal: false,
      showColumnModal: false,
      editingBoard: null,
      selectedColumn: null,
      columnTitle: '',
      columnColor: '#000000',
      columnProject: null,
      editColumnError: null,
      confirmDeleteColumn: false,
      showChildrenBoards: false,
      childBoardsOpen: true,
    }
  },
  async created() {
    await this.$storex.kanban.loadKanban(this.project)
  },
  computed: {
    isMobile() {
      return this.$ui.isMobile
    },
    kanban() {
      return this.project?.$state?.kanban || { boards: {} }
    },
    activeBoard() {
      return this.$kanban.activeBoard
    },
    activeKanbanBoard() {
      return this.$kanban.activeKanbanBoard
    },
    parentBoard() {
      return this.$kanban.parentBoard
    },
    parentBoardOptions() {
      return this.$kanban.parentBoardOptions
    },
    childBoards() {
      return this.$kanban.childBoards
    },
    viewColumns() {
      return this.$kanban.buildViewColumns(this.filter)
    },
    lastUpdatedTask() {
      return this.$kanban.lastUpdatedTask
    },
    isLoading() {
      return this.$kanban.isLoading
    },
    historyProjects() {
      const allProjects = this.$projects.allProjects || []
      if (!allProjects.length) return []
      const boardChats = this.$kanban.boardChats
      const boardProjectIds = new Set(boardChats.map(c => c.project_id).filter(Boolean))
      return allProjects.filter(p =>
        p.$api && (
          boardProjectIds.has(p.project_id) ||
          p.project_id === this.$projects.activeProject?.project_id
        )
      )
    }
  },
  watch: {
    project() {
      this.$storex.kanban.loadKanban(this.project)
    },
    childBoards(newVal, oldVal) {
      if (newVal?.length && !oldVal?.length) {
        this.showChildrenBoards = true
        this.childBoardsOpen = true
      }
    }
  },
  methods: {
    clearSearch() {
      this.filter = ''
      this.searchVisible = false
    },

    async openChat(task) {
      if (task.id === -1) {
        await this.onNewTask({})
      } else {
        await this.$chats.reloadChat(task)
        await this.$chats.setActiveChat(task)
        if (this.$ui.isVibeMode) {
          this.$ui.openVibeCoding()
        }
      }
    },

    async onNewTask({ mode, column }) {
      const chat = await this.$kanban.newTask({ mode, column })
      if (chat) await this.openChat(chat)
    },

    async onMoveTask({ taskId, toColumn }) {
      await this.$kanban.moveTask({ taskId, toColumn })
    },

    // ── Column modal ──────────────────────────────────────────────────────────
    openAddColumnModal() {
      this.selectedColumn = null
      this.columnTitle = ''
      this.columnColor = '#000000'
      this.columnProject = null
      this.confirmDeleteColumn = false
      this.editColumnError = null
      this.showColumnModal = true
    },

    openEditColumnModal(columnTitle) {
      const storeCol = this.activeKanbanBoard?.columns?.find(c => c.title === columnTitle) || null
      this.selectedColumn = storeCol
      this.columnTitle = columnTitle
      this.columnColor = storeCol?.color || '#000000'
      this.columnProject = this.$projects.allProjectsById?.[storeCol?.project_id] || null
      this.confirmDeleteColumn = false
      this.editColumnError = null
      this.showColumnModal = true
    },

    async addOrUpdateColumn() {
      const title = this.columnTitle.trim()
      if (!title) return this.resetColumnModal()

      const columns = this.activeKanbanBoard?.columns || []
      const duplicate = columns.find(
        c => c.title === title && c.id !== this.selectedColumn?.id
      )
      if (duplicate) {
        this.editColumnError = 'Column name already exists'
        return
      }

      if (this.selectedColumn) {
        await this.$kanban.updateColumn({
          id: this.selectedColumn.id,
          title,
          color: this.columnColor,
          project_id: this.columnProject?.project_id || null
        })
      } else {
        await this.$kanban.addColumn({
          title,
          color: this.columnColor,
          project_id: this.columnProject?.project_id || null
        })
      }

      this.resetColumnModal()
    },

    async deleteColumn() {
      if (!this.confirmDeleteColumn) {
        this.confirmDeleteColumn = true
        return
      }
      await this.$kanban.deleteColumn({ title: this.columnTitle })
      this.resetColumnModal()
    },

    resetColumnModal() {
      this.showColumnModal = false
      this.columnTitle = ''
      this.columnColor = '#000000'
      this.selectedColumn = null
      this.editColumnError = null
      this.confirmDeleteColumn = false
      this.columnProject = null
    },

    // ── Board modal ───────────────────────────────────────────────────────────
    openNewBoardModal() {
      this.editingBoard = null
      this.showBoardModal = true
    },

    openEditBoardModal() {
      const boardTitle = this.activeBoard
      const boardData = this.kanban.boards[boardTitle]
      this.editingBoard = { id: boardTitle, ...boardData }
      this.showBoardModal = true
    },

    async onBoardSave({ originalTitle, board }) {
      await this.$kanban.saveBoard({ originalTitle, board })
      this.showBoardModal = false
      this.editingBoard = null
    },

    async onBoardDelete(board) {
      await this.$kanban.deleteBoard(board)
      this.showBoardModal = false
      this.editingBoard = null
    },
  }
}
</script>

<style scoped>
.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.25s ease, opacity 0.25s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

.slide-down-search-enter-active,
.slide-down-search-leave-active {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.slide-down-search-enter-from,
.slide-down-search-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}
</style>