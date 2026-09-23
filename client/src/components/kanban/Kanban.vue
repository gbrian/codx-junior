<script setup>
import { v4 as uuidv4 } from 'uuid'
import KanbanList from './KanbanList.vue'
import ProjectDetailt from '../ProjectDetailt.vue'
import KanbanGridView from './KanbanGridView.vue'
import KanbanFilesView from './KanbanFilesView.vue'
import Collapsible from '../Collapsible.vue'
import ChatHistory from './ChatHistory.vue'
import KanbanBoardModal from './KanbanBoardModal.vue'
</script>

<template>
  <div class="kanban h-full relative" v-if="kanban">

    <!-- Background image -->
    <div class="absolute top-0 left-0 right-0 bottom-0 bg-cover opacity-20 rounded-lg z-0"
      :style="{ backgroundImage: `url(${activeKanbanBoard?.background}` }"
      v-if="activeKanbanBoard?.background"
    />

    <!-- Loading bar -->
    <div class="absolute bottom-0 left-0 right-0 z-20 text-xs" v-if="loadingChats">
      <progress class="progress w-full animate-pulse opacity-30"></progress>
    </div>

    <!-- ── Activity panel (full-screen slide-in drawer) ── -->
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
    <div class="h-full absolute top-0 left-0 right-0 bottom-0 z-1 flex flex-col"
      :class="isMobile ? 'pb-14' : ''">

      <!-- ── Top toolbar ── -->
      <div class="flex items-center gap-2 px-2 pt-2 pb-1 shrink-0 min-w-0">

        <!-- Back button -->
        <button class="btn btn-ghost btn-sm shrink-0" @click="$projects.setActiveBoard()">
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
              @click="toggleBookmark"
            ></i>
            <span class="font-semibold text-sm sm:text-base truncate">{{ board }}</span>
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
          <span class="cursor-pointer" v-if="filter" @click.stop="[filter = '', searchVisible = false]">
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

        <!-- More options dropdown (desktop) -->
        <div class="hidden sm:block dropdown dropdown-left">
          <button class="btn btn-sm tooltip tooltip-bottom" data-tip="More options">
            <i class="fa-solid fa-ellipsis-vertical"></i>
          </button>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-50 w-52 p-2 shadow">
            <li>
              <a @click="showChildrenBoards = !showChildrenBoards"
                :class="{ 'text-warning': showChildrenBoards }">
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
      <Collapsible
        v-if="showChildrenBoards"
        v-model="childBoardsOpen"
        class="mx-2 mt-1"
      >
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
            @select="$emit('select-board', $event)"
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
          @new-task="newTask"
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

    <!-- ── Mobile bottom navigation bar ── -->
    <transition name="slide-up-bar">
      <div
        v-if="isMobile"
        class="absolute bottom-0 left-0 right-0 z-20 flex items-center justify-around gap-1 px-2 py-1 bg-base-200/95 backdrop-blur border-t border-base-300 safe-area-bottom"
      >
        <!-- Search toggle -->
        <button
          class="btn btn-ghost btn-sm flex-1 flex flex-col items-center gap-0 h-auto py-1"
          :class="searchVisible ? 'text-primary' : ''"
          @click="searchVisible = !searchVisible"
        >
          <i class="fa-solid fa-filter text-base"></i>
          <span class="text-xs leading-none">Filter</span>
        </button>

        <!-- Board view -->
        <button
          class="btn btn-ghost btn-sm flex-1 flex flex-col items-center gap-0 h-auto py-1"
          :class="activeView === 'board' ? 'text-primary' : ''"
          @click="activeView = 'board'"
        >
          <i class="fa-solid fa-table-columns text-base"></i>
          <span class="text-xs leading-none">Board</span>
        </button>

        <!-- Files view -->
        <button
          class="btn btn-ghost btn-sm flex-1 flex flex-col items-center gap-0 h-auto py-1"
          :class="activeView === 'files' ? 'text-primary' : ''"
          @click="activeView = 'files'"
        >
          <i class="fa-solid fa-file-code text-base"></i>
          <span class="text-xs leading-none">Files</span>
        </button>

        <!-- Activity -->
        <button
          class="btn btn-ghost btn-sm flex-1 flex flex-col items-center gap-0 h-auto py-1"
          @click="showActivity = true"
        >
          <i class="fa-solid fa-clock-rotate-left text-base"></i>
          <span class="text-xs leading-none">Activity</span>
        </button>

        <!-- More (add column/board/settings) -->
        <div class="dropdown dropdown-top dropdown-end flex-1">
          <button tabindex="0" class="btn btn-ghost btn-sm w-full flex flex-col items-center gap-0 h-auto py-1">
            <i class="fa-solid fa-ellipsis-vertical text-base"></i>
            <span class="text-xs leading-none">More</span>
          </button>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-50 w-52 p-2 shadow mb-1">
            <li>
              <a @click="showChildrenBoards = !showChildrenBoards"
                :class="{ 'text-warning': showChildrenBoards }">
                <i class="fa-brands fa-trello"></i> Child boards
              </a>
            </li>
            <li class="divider my-1"></li>
            <li><a @click="openAddColumnModal"><i class="fa-solid fa-plus"></i> Column</a></li>
            <li><a @click="openNewBoardModal"><i class="fa-solid fa-plus"></i> Board</a></li>
            <li><a @click="openEditBoardModal"><i class="fas fa-cogs"></i> Settings</a></li>
          </ul>
        </div>
      </div>
    </transition>

    <!-- ── Mobile search bar (slide-down when active) ── -->
    <transition name="slide-down-search">
      <div
        v-if="isMobile && searchVisible"
        class="absolute top-12 left-0 right-0 z-20 px-3 py-2 bg-base-200/95 backdrop-blur border-b border-base-300"
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
        :currentBoardId="board"
        :project="project"
        @save="onBoardSave"
        @delete="onBoardDelete"
        @cancel="showBoardModal = false"
      />
    </modal>

    <!-- ── Add/Edit Column modal ── -->
    <modal close="true" @close="showColumnModal = false" v-if="showColumnModal">
      <h2 class="font-bold text-lg">{{ selectedColumn ? 'Edit Column' : 'Add Column' }}</h2>
      <div class="flex gap-1 items-center mt-2">
        <input type="text" v-model="columnTitle" placeholder="Enter column name" class="grow input input-bordered w-full" />
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

    <!-- ── Import Task modal ── -->
    <modal v-if="showImportModalForColumn">
      <h2 class="font-bold text-lg">Import Task</h2>
      <div class="form-control mt-2">
        <label class="label cursor-pointer">
          <span class="label-text">Import from clipboard</span>
          <input type="radio" name="importOptions" value="clipboard" v-model="importOption" class="radio" />
        </label>
        <label class="label cursor-pointer">
          <span class="label-text">Import from URL</span>
          <input type="radio" name="importOptions" value="url" v-model="importOption" class="radio" />
        </label>
        <input v-if="importOption === 'url'" type="text" v-model="importUrl" placeholder="Paste URL here" class="input input-bordered w-full mt-2" />
      </div>
      <div class="modal-action">
        <button class="btn btn-primary" @click="confirmImportTask">Import</button>
        <button class="btn btn-ghost" @click="showImportModalForColumn = null">Cancel</button>
      </div>
    </modal>
  </div>
</template>

<script>
const ALL_BOARD_TITLE_ID = '$ALL'

export default {
  props: ['project'],
  data() {
    return {
      boardFilter: '',
      filter: null,
      showBoardModal: false,
      showColumnModal: false,
      editingBoard: null,
      columnTitle: '',
      columnColor: '#000000',
      isDropdownOpen: false,
      selectedColumn: null,
      editColumnError: null,
      viewColumns: [],
      selectedTemplate: null,
      showChildrenBoards: false,
      childBoardsOpen: true,
      confirmDeleteColumn: false,
      showImportModalForColumn: null,
      importOption: 'clipboard',
      importUrl: '',
      searchVisible: false,
      topChats: [],
      columnProject: null,
      loadingChats: false,
      showActivity: false,
      activeView: 'board'
    }
  },
  created() {
    this.projectChanged()
  },
  computed: {
    isMobile() {
      return this.$ui.isMobile
    },
    filteredBoards() {
      if (!this.boardFilter) return this.parentBoards
      return Object.values(this.rawBoards).filter(board =>
        board.title.toLowerCase().includes(this.boardFilter.toLowerCase())
      )
    },
    board() {
      return this.kanban?.boards[this.$projects.activeBoard]
        ? this.$projects.activeBoard
        : null
    },
    lastUpdatedTask() {
      return this.visibleTasks
        .sort((a, b) =>
          (a.updated_at || new Date(1900, 1, 1)) > (b.updated_at || new Date(1900, 1, 1)) ? -1 : 1
        )
        .slice(0, 1)[0] || {}
    },
    kanban() {
      return this.project?.$state?.kanban || { boards: {} }
    },
    rawBoards() {
      const { boards = {} } = this.kanban
      return Object.keys(boards).reduce((acc, id) => {
        acc[id] = { ...boards[id], id, title: id }
        return acc
      }, {})
    },
    boards() {
      const raw = this.rawBoards
      return Object.keys(raw).reduce((acc, id) => {
        acc[id] = {
          ...raw[id],
          tasks: this.chats
            .filter(c => !c.message_id && (id === ALL_BOARD_TITLE_ID || c.board === id))
            .sort((a, b) => (a.pinned && !b.pinned ? -1 : 1))
        }
        return acc
      }, {})
    },
    activeBoard() {
      return this.rawBoards[this.$projects.activeBoard] || null
    },
    activeKanbanBoard() {
      return this.kanban?.boards[this.board] || null
    },
    chats() {
      const allChats = this.$projects.allChats
      return Object.values(allChats || {}).map(c => ({
        ...c,
        column: c.column || '--none--'
      }))
    },
    lastMessages() {
      return this.chats.sort((a, b) => a.last_update > b.last_update ? -1 : 1)
    },
    boardChats() {
      return this.chats.filter(c => c.board === this.board)
    },
    parentBoards() {
      return Object.values(this.boards).filter(b => !b.parent_id)
    },
    childBoards() {
      return Object.values(this.boards).filter(b => b.parent_id === this.activeBoard?.id)
    },
    parentBoard() {
      return this.rawBoards[this.activeBoard?.parent_id] || null
    },
    parentBoardOptions() {
      return Object.values(this.rawBoards)
    },
    columnList() {
      const kanbanColumns = this.activeKanbanBoard?.columns?.map(c => c.title) || []
      const chatColumns = this.boardChats.map(c => c.column)
      return [...new Set([...kanbanColumns, ...chatColumns])]
    },
    visibleTasks() {
      return this.viewColumns.reduce((a, col) => a.concat(col.tasks || []), [])
    },
    historyProjects() {
      const allProjects = this.$projects.allProjects || []
      if (!allProjects.length) return []
      const boardProjectIds = new Set(
        this.boardChats.map(c => c.project_id).filter(Boolean)
      )
      return allProjects.filter(p =>
        p.$api &&
        (boardProjectIds.has(p.project_id) ||
          p.project_id === this.$projects.activeProject?.project_id)
      )
    }
  },
  watch: {
    filter(newValue, oldValue) {
      if ((!newValue && oldValue) || newValue?.length > 3) {
        this.buildViewColumns()
      }
    },
    board() {
      this.selectBoard()
    },
    project() {
      this.projectChanged()
    },
    chats(newValue, oldValue) {
      const ids = arr => arr.map(c => c.id).sort().join()
      if (ids(newValue) !== ids(oldValue)) this.buildViewColumns()
    },
    kanban() {
      this.buildViewColumns()
    },
    childBoards(newVal, oldVal) {
      if (newVal?.length && !oldVal?.length) {
        this.showChildrenBoards = true
        this.childBoardsOpen = true
      }
    }
  },
  methods: {
    async setActiveChat(chat) {
      chat && this.$chats.reloadChat(chat)
      this.$chats.setActiveChat(chat)
      if (this.$ui.isVibeMode) {
        this.$ui.openVibeCoding()
      }
    },
    async projectChanged() {
      await this.$storex.projects.loadKanban({ project: this.project })
      this.selectBoard()
      this.buildViewColumns()
    },
    async selectBoard(board) {
      this.loadingChats += 1
      board = board || this.board
      try {
        this.viewColumns = []
        if (board !== this.board) {
          await this.$projects.setActiveBoard(board)
        }
        this.isDropdownOpen = false
        if (board && this.kanban.boards[board] && !this.kanban.boards[board].active) {
          Object.keys(this.kanban.boards)
            .filter(b => this.kanban.boards[b])
            .forEach(b => (this.kanban.boards[b].active = b === board))
          this.kanban.boards[board].last_update = new Date().toISOString()
          this.saveKanban()
        }
        this.buildViewColumns()
        this.showChildrenBoards = !!this.childBoards?.length
      } finally {
        this.loadingChats -= 1
      }
    },
    setView(view) {
      if (!this.activeKanbanBoard) return
      this.activeKanbanBoard.view = view
      this.saveKanban()
    },
    buildViewColumns() {
      if (!this.kanban) return
      const columnTitles = this.columnList
      const columnChats = this.activeKanbanBoard?.columns?.chats || []

      const getChatIndex = (c) => columnChats.findIndex(kc => kc.id === c.id)

      const builtColumns = columnTitles.map((col, ix) => {
        const storeColumn = this.activeKanbanBoard?.columns?.find(bc => bc.title === col) || {}
        return {
          id: storeColumn.id || col,
          title: col,
          color: storeColumn.color || null,
          showSubTasks: storeColumn.showSubTasks,
          project_id: storeColumn.project_id || null,
          valid: !!storeColumn.id,
          position: ix,
          project: this.$projects.allProjectsById[storeColumn.project_id] || null,
          tasks: this.boardChats
            .filter(t => (t.column || '--none--') === col)
            .sort((a, b) => (a.pinned || getChatIndex(a) < getChatIndex(b) ? -1 : 1))
        }
      }).sort((a, b) => (a.position < b.position ? -1 : 1))

      this.viewColumns = this.applyFilter(builtColumns)
      this.topChats = this.activeBoard
        ? this.boardChats.filter(t => t.pinned)
        : []
    },
    applyFilter(columns) {
      if (!this.filter) return columns
      const text = this.filter.toLowerCase()
      return columns.map(col => ({
        ...col,
        tasks: col.tasks.filter(task =>
          Object.keys(task)
            .reduce((acc, k) => `${acc} ${JSON.stringify(task[k])}`, '')
            .toLowerCase().includes(text)
        )
      }))
    },
    onColumnOrderChanged(reorderedColumns) {
      this.viewColumns = reorderedColumns
      this.onColumnTaskListChanged()
    },
    async onColumnTaskListChanged(column) {
      if (this.$ui.isMobile) return
      const kboard = this.kanban.boards[this.board]
      kboard.columns = await Promise.all(
        this.viewColumns.map(async (viewCol) => {
          const storeCol = this.activeKanbanBoard?.columns?.find(
            c => c.id === viewCol.id || c.title === viewCol.title
          ) || {}
          await Promise.all(
            viewCol.tasks
              .filter(t => t.column !== viewCol.title)
              .map(task => this.$chats.saveChatInfo({ ...task, column: viewCol.title }))
          )
          return {
            id: storeCol.id || viewCol.id,
            title: viewCol.title,
            color: storeCol.color || viewCol.color,
            project_id: storeCol.project_id || viewCol.project_id || null,
            showSubTasks: storeCol.showSubTasks,
            chats: viewCol.tasks.map(t => t.id)
          }
        })
      )
      kboard.last_update = new Date().toISOString()
      this.saveKanban()
    },
    newTask({ mode, column }) {
      this.createNewChat({
        mode: mode || 'chat',
        profiles: [],
        column
      })
    },
    async createNewChat(base, activateChat) {
      const chat = await this.$chats.createNewChat({
        ...base,
        id: uuidv4(),
        board: base.board || this.board
      })
      if (activateChat !== false) this.setActiveChat(chat)
      return chat
    },
    async importTask(column) {
      this.showImportModalForColumn = column
    },
    async confirmImportTask() {
      if (this.importOption === 'clipboard') {
        const text = await navigator.clipboard.readText()
        const existingChat = JSON.parse(text)
        const newChat = await this.createNewChat({
          ...existingChat,
          id: null,
          column: this.showImportModalForColumn.title
        })
        this.$chats.saveChat(newChat)
      } else if (this.importOption === 'url') {
        await this.$projects.createNewChatFromUrl({
          board: this.board || 'Default',
          column: this.showImportModalForColumn.title,
          name: 'Import from url',
          mode: 'chat',
          url: this.importUrl
        })
      }
      this.showImportModalForColumn = null
      this.importUrl = null
    },
    async openChat(element) {
      element.id === -1 ? this.newTask({}) : await this.setActiveChat(element)
    },
    async onChatEditDone(board) {
      if (this.board !== board) this.selectBoard(board)
      await this.setActiveChat()
      this.buildViewColumns()
    },
    async createSubTask({ parent, name, mode, description, project_id, parent_id, message_id, file_list, activateChat, child_index, column, profiles }) {
      const chat = await this.createNewChat({
        board: parent.board,
        name,
        mode,
        profiles,
        column: column || parent.column,
        parent_id: parent_id || parent.id,
        message_id,
        project_id: project_id || parent.project_id,
        messages: description ? [{ role: 'user', content: description }] : [],
        file_list,
        child_index
      }, activateChat)
      await this.$chats.saveChat(chat)
      if (description) this.$storex.projects.chatWihProject(chat)
    },
    async createSubTasks(event) {
      this.$projects.createSubtasks(event)
    },
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
      this.columnTitle = this.columnTitle.trim()
      if (!this.columnTitle) return this.resetColumnModal()

      const existing = this.activeKanbanBoard.columns?.find(
        c => c.title === this.columnTitle && c.id !== this.selectedColumn?.id
      )
      if (existing) {
        this.editColumnError = 'Column name already exists'
        return
      }

      if (this.selectedColumn) {
        const storeCol = this.activeKanbanBoard.columns.find(c => c.id === this.selectedColumn.id)
        if (storeCol) {
          storeCol.title = this.columnTitle
          storeCol.color = this.columnColor
          storeCol.project_id = this.columnProject?.project_id || null
        }
      } else {
        this.activeKanbanBoard.columns = [
          ...this.activeKanbanBoard.columns || [],
          {
            id: uuidv4(),
            title: this.columnTitle,
            color: this.columnColor,
            project_id: this.columnProject?.project_id || null,
            chats: []
          }
        ]
      }

      this.activeKanbanBoard.last_update = new Date().toISOString()
      await this.saveKanban()
      this.resetColumnModal()
      this.buildViewColumns()
    },
    async deleteColumn() {
      if (!this.confirmDeleteColumn) {
        this.confirmDeleteColumn = true
        return
      }
      const viewCol = this.viewColumns.find(c => c.title === this.columnTitle)
      if (viewCol) {
        await Promise.all(viewCol.tasks.map(chat => this.$chats.deleteChat(chat)))
      }
      this.activeKanbanBoard.columns = this.activeKanbanBoard.columns.filter(
        c => c.title !== this.columnTitle
      )
      await this.saveKanban()
      this.resetColumnModal()
      this.buildViewColumns()
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
    async onMoveTask({ taskId, toColumn }) {
      const task = this.visibleTasks.find(t => t.id === taskId)
      if (!task) return
      await this.$chats.saveChatInfo({ ...task, column: toColumn })
      this.buildViewColumns()
    },
    openNewBoardModal() {
      this.editingBoard = null
      this.showBoardModal = true
    },
    openEditBoardModal() {
      const boardTitle = this.board
      const boardData = this.kanban.boards[boardTitle]
      this.editingBoard = {
        id: boardTitle,
        ...boardData
      }
      this.showBoardModal = true
    },
    async onBoardSave({ originalTitle, board }) {
      const oldName = originalTitle
      const newName = board.title?.trim()

      if (!newName) return

      if (oldName && oldName !== newName) {
        await Promise.all(
          this.chats
            .filter(c => c.board === oldName)
            .map(c => this.$chats.saveChatInfo({ ...c, board: newName }))
        )
        delete this.kanban.boards[oldName]
        Object.values(this.kanban.boards)
          .filter(b => b.parent_id === oldName)
          .forEach(b => (b.parent_id = newName))
      }

      this.kanban.boards[newName] = {
        ...this.kanban.boards[newName],
        title: newName,
        description: board.description || '',
        background: board.background || '',
        parent_id: board.parent_id || null,
        project_id: board.project_id || null
      }

      await this.saveKanban()
      this.showBoardModal = false
      this.editingBoard = null
      this.buildViewColumns()
    },
    async onBoardDelete(board) {
      const boardTitle = board.title

      const chatsToDelete = this.boardChats.filter(c => c.board === boardTitle)
      await Promise.all(chatsToDelete.map(c => this.$chats.deleteChat(c)))

      const childBoardsList = Object.values(this.kanban.boards)
        .filter(b => b.parent_id === boardTitle)
      childBoardsList.forEach(b => this.onBoardDelete(b))

      delete this.kanban.boards[boardTitle]

      await this.saveKanban()
      this.showBoardModal = false
      this.editingBoard = null

      if (this.board === boardTitle) {
        const parentTitle = board.parent_id || Object.keys(this.kanban.boards)[0]
        await this.selectBoard(parentTitle)
      }
      this.buildViewColumns()
    },
    openColumnPropertiesModal(column) {
      this.openEditColumnModal(column.title)
    },
    async saveKanban() {
      await this.$storex.projects.saveKanban({ project: this.project })
    },
    toggleBookmark({ title } = {}) {
      const boardTitle = title || this.activeBoard?.title
      const board = this.kanban.boards[boardTitle]
      if (board) {
        board.bookmark = !board.bookmark
        this.saveKanban()
      }
    },
    async moveChatsToColumn({ chats, column }) {
      await Promise.all(
        chats.map(chat => this.$chats.saveChatInfo({ ...chat, column }))
      )
      this.buildViewColumns()
    }
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

.slide-up-bar-enter-active,
.slide-up-bar-leave-active {
  transition: transform 0.2s ease;
}
.slide-up-bar-enter-from,
.slide-up-bar-leave-to {
  transform: translateY(100%);
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