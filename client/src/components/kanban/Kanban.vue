<script setup>
import { v4 as uuidv4 } from 'uuid'
import KanbanList from './KanbanList.vue'
import FileFinder from '../filebrowser/FileFinder.vue'
import ProjectDetailt from '../ProjectDetailt.vue'
import KanbanGridView from './KanbanGridView.vue'
import KanbanFilesView from './KanbanFilesView.vue'
import Collapsible from '../Collapsible.vue'
import ChatHistory from './ChatHistory.vue'
import KanbanBoardModal from './KanbanBoardModal.vue'
</script>

<template>
  <div class="kanban h-full relative" v-if="kanban">
    <div class="absolute top-0 left-0 right-0 bottom-0 bg-cover opacity-20 rounded-lg z-0"
      :style="{ backgroundImage: `url(${activeKanbanBoard?.background}` }"
      v-if="activeKanbanBoard?.background"
    />
    <div class="absolute bottom-0 left-0 right-0 z-20 text-xs @xl:text-md" v-if="loadingChats">
      Loading...
      <progress class="progress w-full animate-pulse opacity-30"></progress>
    </div>

    <div class="h-full absolute top-0 left-0 right-0 bottom-0 z-1">
      <!-- Activity panel -->
      <div class="h-full overflow-auto relative" v-if="showActivity">
        <div class="flex gap-2 sticky top-0 bg-base-300 z-10 p-2 rounded-md">
          <button class="btn btn-warning btn-sm" @click="showActivity = false">
            <i class="fa-solid fa-clock-rotate-left"></i>
          </button>
          <div class="text-2xl">
            Recent activity <span v-if="project">: {{ project.project_name }}</span>
          </div>
        </div>
        <ChatHistory :projects="historyProjects" />
      </div>

      <!-- Main kanban layout -->
      <div class="flex flex-col h-full p-2" v-if="!showActivity">
        <!-- Top toolbar - Mobile Responsive -->
        <div class="flex flex-col sm:flex-row gap-2 sm:gap-4 sm:items-center w-full">
          
          <!-- Left section: Board navigation & title -->
          <div class="flex gap-2 items-center min-w-0 flex-shrink-0">
            <!-- Back button -->
            <div class="flex gap-2 items-center" @click="$projects.setActiveBoard()">
              <button class="btn btn-ghost btn-sm md:btn-md">
                <i class="fa-solid fa-circle-arrow-left text-lg"></i>
              </button>
            </div>
            
            <!-- Breadcrumb: Parent board (hidden on mobile) -->
            <div class="hidden sm:flex gap-1 items-center text-sm truncate">
              <div @click.stop="selectBoard(parentBoard?.title)" 
                v-if="parentBoard?.title"
                class="cursor-pointer hover:text-primary truncate">
                {{ parentBoard?.title }} /
              </div>
            </div>
            
            <!-- Board title with bookmark (responsive text) -->
            <div class="flex gap-1 items-center text-xs sm:text-sm md:text-xl truncate flex-1 sm:flex-none">
              <i
                class="fa-solid fa-bookmark flex-shrink-0 text-base cursor-pointer"
                :class="{ 'text-warning': activeKanbanBoard?.bookmark }"
                @click="toggleBookmark"
              ></i>
              <span class="truncate">{{ board }}</span>
            </div>
          </div>

          <!-- Center/Right section: Controls (responsive stacking) -->
          <div class="flex gap-2 items-center w-full sm:w-auto sm:ml-auto justify-between sm:justify-end flex-wrap">
            
            <!-- Search input - Responsive visibility -->
            <div class="grow sm:grow-0 input input-sm input-bordered flex items-center gap-2 tooltip tooltip-bottom min-w-0"
              data-tip="Find in tasks"
            >
              <input 
                type="text" 
                :class="{ hidden: !searchVisible }" 
                v-model="filter" 
                class="grow" 
                placeholder="Search..." 
              />
              <span class="cursor-pointer flex-shrink-0" v-if="filter" @click.stop="[filter = '', searchVisible = false]">
                <i class="fa-regular fa-circle-xmark"></i>
              </span>
              <span v-else class="flex-shrink-0">
                <i class="fa-solid fa-filter cursor-pointer" @click="searchVisible = !searchVisible"></i>
              </span>
            </div>

            <!-- View toggle: Board / Files (visible on all sizes) -->
            <div class="join tooltip tooltip-bottom" data-tip="Switch view">
              <button
                class="btn btn-sm join-item"
                :class="activeView === 'board' && 'btn-active'"
                @click="activeView = 'board'"
              >
                <i class="fa-solid fa-table-columns text-base"></i>
                <span class="hidden sm:inline text-xs">Board</span>
              </button>
              <button
                class="btn btn-sm join-item"
                :class="activeView === 'files' && 'btn-active'"
                @click="activeView = 'files'"
              >
                <i class="fa-solid fa-file-code text-base"></i>
                <span class="hidden sm:inline text-xs">Files</span>
              </button>
            </div>

            <!-- Secondary controls dropdown (mobile-optimized) -->
            <div class="dropdown dropdown-left">
              <button class="btn btn-sm md:btn-md tooltip tooltip-bottom" data-tip="More options">
                <i class="fa-solid fa-ellipsis-vertical"></i>
              </button>
              <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-50 w-52 p-2 shadow">
                <!-- Show child boards toggle -->
                <li class="text-xs sm:text-sm">
                  <a @click="showChildrenBoards = !showChildrenBoards"
                    :class="{ 'text-warning': showChildrenBoards }">
                    <i class="fa-brands fa-trello"></i>
                    Child boards
                  </a>
                </li>
                <!-- Show activity toggle -->
                <li class="text-xs sm:text-sm">
                  <a @click="showActivity = !showActivity">
                    <i class="fa-solid fa-clock-rotate-left"></i>
                    Activity
                  </a>
                </li>
                <li class="divider my-1"></li>
                <!-- Add column -->
                <li class="text-xs sm:text-sm">
                  <a @click="openAddColumnModal">
                    <i class="fa-solid fa-plus"></i> Column
                  </a>
                </li>
                <!-- Add board -->
                <li class="text-xs sm:text-sm">
                  <a @click="openNewBoardModal">
                    <i class="fa-solid fa-plus"></i> Board
                  </a>
                </li>
                <!-- Board settings -->
                <li class="text-xs sm:text-sm">
                  <a @click="openEditBoardModal">
                    <i class="fas fa-cogs"></i> Settings
                  </a>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Child boards collapsible -->
        <Collapsible
          v-if="showChildrenBoards"
          v-model="childBoardsOpen"
          class="mt-2"
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

        <div class="mt-3 grow relative flex flex-col gap-2 min-h-0">
          <!-- Board (grid) view -->
          <KanbanGridView
            v-if="activeView === 'board'"
            class="min-h-[50vw]"
            :columns="viewColumns"
            :lastUpdatedTaskId="lastUpdatedTask.id"
            @open-task="openChat"
            @new-task="newTask"
            @new-column="openAddColumnModal"
            @edit-column="openEditColumnModal"
            @move-task="onMoveTask"
          />

          <!-- Files view -->
          <KanbanFilesView
            v-if="activeView === 'files'"
            class="h-full bg-base-300/70"
            :columns="viewColumns"
            @open-task="openChat"
          />
        </div>
      </div>

      <!-- Board modal (new/edit/delete) -->
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

      <!-- Add/Edit Column modal -->
      <modal close="true" @close="showColumnModal = false" v-if="showColumnModal">
        <h2 class="font-bold text-lg">{{ selectedColumn ? 'Edit Column' : 'Add Column' }}</h2>
        <div class="flex gap-1 items-center">
          <input type="text" v-model="columnTitle" placeholder="Enter column name" class="grow input input-bordered w-full" />
        </div>
        <ProjectDetailt
          v-model="columnProject"
          :options="{ showFolders: false, showIcon: true, showSelector: true }"
        />
        <span v-if="editColumnError" class="text-error">{{ editColumnError }}</span>
        <div class="modal-action flex flex-col">
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
        <div class="badge badge-error" v-if="editColumnError">{{ editColumnError }}</div>
      </modal>

      <!-- Import Task modal -->
      <modal v-if="showImportModalForColumn">
        <h2 class="font-bold text-lg">Import Task</h2>
        <div class="form-control">
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
          <button class="btn" @click="confirmImportTask">Import</button>
          <button class="btn" @click="showImportModalForColumn = null">Cancel</button>
        </div>
      </modal>

      <modal close="true" @close="showFileFinder = false" v-if="showFileFinder">
        <FileFinder @select="onAddFile" />
      </modal>
    </div>
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
      showFileFinder: false,
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
    onAddFile(filePaths) {
      if (this.activeKanbanBoard) {
        this.activeKanbanBoard.file_list = [
          ...(this.activeKanbanBoard.file_list || []),
          ...filePaths
        ]
        this.saveKanban()
      }
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