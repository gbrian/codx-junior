<script setup>
import draggable from 'vuedraggable'
import TaskCard from './TaskCard.vue'
import TaskCardLite from './TaskCardLite.vue'
import ChatViewVue from '../../views/ChatView.vue'
import { v4 as uuidv4 } from 'uuid'
import KanbanList from './KanbanList.vue'
import ChatIcon from '../chat/ChatIcon.vue'
import FileFinder from '../filebrowser/FileFinder.vue'
import ProjectDetailt from '../ProjectDetailt.vue'
import ChatHistoryVue from './ChatHistory.vue'
</script>

<template>
  <div class="h-full relative" v-if="kanban">
    <div class="absolute top-0 left-0 right-0 bottom-0 bg-cover opacity-20 rounded-lg z-0"
      :style="{ backgroundImage: `url(${activeKanbanBoard?.background}` }"
      v-if="activeKanbanBoard?.background"
    />
    <div class="absolute bottom-0 left-0 right-0 z-20 text-xs @xl:text-md" v-if="loadingChats">
      Loading...
      <progress class="progress w-full animate-pulse opacity-30"></progress>
    </div>

    <div class="h-full absolute top-0 left-0 right-0 bottom-0 z-1">

      <!-- Kanban board view -->
      <div class="flex flex-col h-full" v-if="!$projects.activeChat && showKanban">
        <div class="flex gap-4 items-center">
          <div class="flex gap-2 items-center">
            <div tabindex="0" class="text-xl py-1 px-2 cursor-pointer flex items-center gap-2">
              <div class="flex gap-2 items-center" @click="$projects.setActiveBoard()">
                <i class="fa-solid fa-circle-arrow-left"></i>
              </div>
              <div @click.stop="selectBoard(parentBoard?.title)" v-if="parentBoard?.title">
                {{ parentBoard?.title }} /
              </div>
              <span>
                <i
                  class="fa-solid fa-bookmark"
                  :class="{ 'text-warning': activeKanbanBoard?.bookmark }"
                  @click="toggleBookmark"
                ></i>
                {{ board }}
              </span>
            </div>
          </div>
          <div class="grow"></div>
          <div class="flex gap-2 items-center">
            <div class="grow input input-sm input-bordered flex items-center gap-2 tooltip tooltip-bottom" 
              data-tip="Find in tasks"
            >
              <input type="text" :class="{ hidden: !searchVisible }" v-model="filter" class="grow" placeholder="Search..." />
              <span class="cursor-pointer" v-if="filter" @click.stop="[filter = '', searchVisible = false]">
                <i class="fa-regular fa-circle-xmark"></i>
              </span>
              <span v-else>
                <i class="fa-solid fa-filter click" @click="searchVisible = !searchVisible"></i>
              </span>
            </div>
            <button class="btn btn-sm tooltip tooltip-bottom" data-tip="Show child boards" 
              :class="showChildrenBoards && 'text-warning'"
              @click="showChildrenBoards = !showChildrenBoards">
              <i class="fa-brands fa-trello"></i>
            </button>
            <button class="btn btn-sm tooltip tooltip-bottom" 
              data-tip="Add column" @click="showColumnModal = true">
              <i class="fa-solid fa-table-columns"></i>
            </button>
            <div class="dropdown dropdown-left">
              <div tabindex="0" class="btn btn-sm mt-1">
                <i class="fa-solid fa-ellipsis-vertical"></i>
              </div>
              <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
                <li @click="showColumnModal = true"><a><i class="fa-solid fa-plus"></i> Column</a></li>
                <li @click="showNewBoardModal"><a><i class="fa-solid fa-plus"></i> Board</a></li>
                <li @click="onEditBoard()"><a><i class="fas fa-cogs"></i> Settings</a></li>
              </ul>
            </div>
          </div>
        </div>

        <KanbanList
          :boards="childBoards"
          v-if="showChildrenBoards"
        />

        <div class="mt-3 grow relative flex flex-col gap-2">
          <!-- Pinned/bookmarked tasks -->
          <div v-if="topChats?.length">
            <h1 class="px-2 text-2xl font-bold mb-4 flex justify-between border-b border-slate-700">
              <div>Bookmarks</div>
            </h1>
            <div class="grid grid-cols-2 grid-flow-row gap-2">
              <TaskCardLite
                v-for="task in topChats" :key="task.id"
                @click="setActiveChat(task)"
                :task="task"
                class="click h-20 overflow-hidden border rounded-md border-slate-600"
                :class="task.pinned && 'border-warning'"
              />
            </div>
          </div>

          <h1 class="px-2 text-2xl font-bold mb-4 flex justify-between border-b border-slate-700">
            <div>Tasks</div>
          </h1>

          <!-- Column drag container — uses viewColumns (component-only data) -->
          <draggable
            v-model="viewColumns"
            group="columns"
            itemKey="id"
            :disabled="$ui.isMobile"
            @end="onColumnTaskListChanged"
            class="min-h-60 grid grid-flow-col overflow-x-scroll relative gap-2 justify-start"
          >
            <template #item="{ element: column }">
              <div
                class="bg-info/20 rounded-lg px-3 py-3 w-80 rounded overflow-auto h-full flex flex-col"
                :class="column.color && 'border-t-4'"
                :style="{ borderColor: column.color }"
              >
                <div class="group font-semibold font-sans tracking-wide text-sm flex gap-2 items-center">
                  <div
                    class="cursor-pointer w-6 h-6 flex items-center justify-center rounded-md group shadow-lg bg-base-100"
                    :style="{ backgroundColor: column.color }"
                    @click="openColumnPropertiesModal(column)"
                  >
                    <span class="hidden group-hover:block"><i class="fa-solid fa-bars"></i></span>
                    <span class="group-hover:hidden">{{ column.tasks.length }}</span>
                  </div>
                  <div class="flex gap-2 items-center grow" :class="!column.valid && 'border border-dashed'">
                    <div class="flex flex-col">
                      {{ column.title }}
                      <div class="text-xs -mt-1" v-if="column.project">
                        {{ column.project.project_name }}
                      </div>
                    </div>
                  </div>
                  <div class="flex gap-2 items-center">
                    <div class="dropdown dropdown-end">
                      <div tabindex="0" role="button" class="btn btn-sm m-1 flex items-center">
                        <i class="mt-1 fa-solid fa-plus"></i>
                      </div>
                      <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
                        <li class="flex gap-2" @click="newTask(column, 'chat')">
                          <a><ChatIcon mode="chat" /> Chat</a>
                        </li>
                        <li class="flex gap-2" @click="newTask(column, 'task')">
                          <a><ChatIcon mode="task" /> Document</a>
                        </li>
                        <li class="flex gap-2" @click="newTask(column, 'topic')">
                          <a><ChatIcon mode="topic" /> Discussion</a>
                        </li>
                        <li class="flex gap-2" @click="newTask(column, 'prview')">
                          <a><ChatIcon mode="prview" /> Changes review</a>
                        </li>
                        <li class="flex gap-2" @click="importTask(column)">
                          <a>Import task</a>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div class="column-tasks grow overflow-y-auto">
                  <draggable
                    v-model="column.tasks"
                    group="tasks"
                    itemKey="id"
                    :disabled="$ui.isMobile"
                    @end="onColumnTaskListChanged(column)"
                    class="mt-3 h-full"
                  >
                    <template #item="{ element: task }">
                      <TaskCard
                        v-if="taskMatchesFilter(task)"
                        :task="task"
                        :itemKey="'id'"
                        class="cursor-pointer bg-base-100 overflow-hidden mt-2"
                        :class="[
                          task.pinned && 'border-warning',
                          lastUpdatedTask.id == task.id ? 'border border-primary border-dashed' : '',
                          (column.showSubTasks !== false) || !task.parent_id ? '' : 'hidden'
                        ]"
                        @click="openChat(task)"
                      />
                    </template>
                  </draggable>
                </div>
              </div>
            </template>
          </draggable>
        </div>
      </div>

      <!-- New/Edit Board modal -->
      <modal close="true" @close="showBoardModal = false" v-if="showBoardModal">
        <h2 class="font-bold text-3xl">{{ editBoard ? 'Edit Board' : 'Add New Board' }}</h2>
        <div class="collapse bg-contain" :style="`background-image:url('${newBoardBackground}')`">
          <input type="radio" name="newboard" v-model="newBoardType" value="manual" />
          <div class="hidden collapse-title text-xl font-medium"><i class="fa-solid fa-gear"></i> Manual settings</div>
          <div class="collapse-content">
            <div class="text-xl text-info font-bold" v-if="activeBoard">Parent {{ activeBoard.title }}</div>
            <input type="text" v-model="newBoardName" placeholder="Enter board name" class="input input-bordered w-full mt-2" />
            <input type="text" v-model="newBoardDescription" placeholder="Enter board description" class="input input-bordered w-full mt-2" />
            <input type="text" v-model="newBoardBackground" placeholder="Enter board background image" class="input input-bordered w-full mt-2" />
            <select v-model="newBoardParent" class="select select-bordered w-full mt-2">
              <option value="">-- none --</option>
              <option v-for="board in boards" :key="board.id" :value="board.id">{{ board.title }}</option>
            </select>
          </div>
        </div>
        <div class="modal-action flex gap-2">
          <button class="btn btn-error" @click="onDeleteBoard(newBoardName)">Delete</button>
          <div class="grow"></div>
          <button class="btn" @click="addOrUpdateBoard" :disabled="isBoardNameTaken || !newBoardName">Save</button>
        </div>
      </modal>

      <!-- Add/Edit Column modal -->
      <modal close="true" @close="showColumnModal = false" v-if="showColumnModal">
        <h2 class="font-bold text-lg">Add/Edit Column</h2>
        <div class="flex gap-1 items-center">
          <input type="text" v-model="columnTitle" placeholder="Enter column name" class="grow input input-bordered w-full" />
        </div>
        <ProjectDetailt
          :project="columnProject || $project"
          :options="{ showFolders: false, showIcon: true, showSelector: true }"
          @select="columnProject = $event"
        />
        <span v-if="editColumnError" class="text-error">{{ editColumnError }}</span>
        <div class="modal-action flex flex-col">
          <div class="flex gap-2 w-full">
            <button class="btn btn-error" @click="deleteColumn">
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
  data() {
    return {
      boardFilter: '',
      filter: null,
      showBoardModal: false,
      showColumnModal: false,
      newBoardType: 'manual',
      newBoardIssueLink: '',
      newBoardName: '',
      newBoardDescription: '',
      newBoardBackground: '',
      newBoardBranch: '',
      newBoardParent: null,
      columnTitle: '',
      columnColor: '#000000',
      isDropdownOpen: false,
      selectedColumn: null,
      editColumnError: null,
      // viewColumns: component-only enriched column objects, never written back to store
      viewColumns: [],
      selectedTemplate: null,
      showChildrenBoards: false,
      editBoard: null,
      originalBoardName: null,
      confirmDeleteColumn: false,
      showImportModalForColumn: null,
      importOption: 'clipboard',
      importUrl: '',
      searchVisible: false,
      showFileFinder: false,
      topChats: [],
      columnProject: null,
      loadingChats: false,
      showHistory: false
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
    showKanban() {
      return this.board
    },
    kanban() {
      return this.$projects.kanban || { boards: {} }
    },
    // Raw store boards — plain config objects, no tasks or view data attached
    rawBoards() {
      const { boards = {} } = this.kanban
      return Object.keys(boards).reduce((acc, id) => {
        acc[id] = { ...boards[id], id, title: id }
        return acc
      }, {})
    },
    // boards: enriched view-only map (adds tasks for KanbanList display)
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
    // activeBoard: pure config from store (no tasks)
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
    columnList() {
      const kanbanColumns = this.activeKanbanBoard?.columns?.map(c => c.title) || []
      const chatColumns = this.boardChats.map(c => c.column)
      return [...new Set([...kanbanColumns, ...chatColumns])]
    },
    visibleTasks() {
      return this.viewColumns.reduce((a, col) => a.concat(col.tasks || []), [])
    },
    isBoardNameTaken() {
      return (
        this.newBoardName &&
        this.newBoardName !== this.originalBoardName &&
        !!this.kanban.boards[this.newBoardName]
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
      if (newVal?.length && !oldVal?.length) this.showChildrenBoards = true
    }
  },
  methods: {
    async setActiveChat(chat) {
      chat && await this.$projects.reloadChat(chat)
      this.$projects.setActiveChat(chat)
    },

    async projectChanged() {
      await this.$projects.loadKanban()
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
        // Mark board active in store config without polluting with view data
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

    // Build component-only column view objects — never mutate store kanban boards
    buildViewColumns() {
      if (!this.kanban) return
      const columnTitles = this.columnList
      // chats order hints stored in kanban (read-only access)
      const columnChats = this.activeKanbanBoard?.columns?.chats || []

      const getChatIndex = (c) => columnChats.findIndex(kc => kc.id === c.id)

      // Build plain view column objects from scratch — spread store column config shallowly
      const builtColumns = columnTitles.map((col, ix) => {
        const storeColumn = this.activeKanbanBoard?.columns?.find(bc => bc.title === col) || {}
        return {
          // Spread only safe scalar store-config fields
          id: storeColumn.id || col,
          title: col,
          color: storeColumn.color || null,
          showSubTasks: storeColumn.showSubTasks,
          project_id: storeColumn.project_id || null,
          // View-only enriched fields
          valid: !!storeColumn.id,
          position: ix,
          project: this.$projects.allProjectsById[storeColumn.project_id] || null,
          tasks: this.boardChats
            .filter(t => (t.column || '--none--') === col && !t.pinned)
            .sort((a, b) => (a.pinned || getChatIndex(a) < getChatIndex(b) ? -1 : 1))
        }
      }).sort((a, b) => (a.position < b.position ? -1 : 1))

      this.viewColumns = this.applyFilter(builtColumns)
      this.topChats = this.activeBoard
        ? this.boardChats.filter(t => t.pinned)
        : []
    },

    // Apply text filter to a columns array — returns new filtered array
    applyFilter(columns) {
      if (!this.filter) return columns
      const text = this.filter.toLowerCase()
      return columns.map(col => ({
        ...col,
        tasks: col.tasks.filter(task =>
          task.name?.toLowerCase().includes(text) ||
          task.messages?.some(m => m.content?.toLowerCase().includes(text))
        )
      }))
    },

    async onColumnTaskListChanged() {
      if (this.$ui.isMobile) return
      // Write back only safe config fields + chat order to store — no view-only fields
      const kboard = this.kanban.boards[this.board]
      kboard.columns = await Promise.all(
        this.viewColumns.map(async (viewCol) => {
          // Find the original store column config by id/title
          const storeCol = this.activeKanbanBoard?.columns?.find(
            c => c.id === viewCol.id || c.title === viewCol.title
          ) || {}
          // Move tasks between columns if dragged
          await Promise.all(
            viewCol.tasks
              .filter(t => t.column !== viewCol.title)
              .map(task => this.$projects.saveChatInfo({ ...task, column: viewCol.title }))
          )
          // Return only store-safe column config with updated chat order
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

    newTask(column, mode) {
      this.createNewChat({
        column: column.title,
        name: 'New Task',
        mode: mode || 'chat',
        profiles: [],
        project_id: column.project_id || null
      })
    },

    async createNewChat(base, activateChat) {
      const chat = await this.$projects.createNewChat({
        ...base,
        id: uuidv4(),
        board: base.board || this.board
      })
      if (activateChat !== false) this.setActiveChat(chat)
      return chat
    },

    addNewFile() {
      this.showFileFinder = true
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
        this.$projects.saveChat(newChat)
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
      await this.$projects.saveChat(chat)
      if (description) this.$storex.projects.chatWihProject(chat)
    },

    async createSubTasks(event) {
      this.$projects.createSubtasks(event)
    },

    async addOrUpdateColumn() {
      this.columnTitle = this.columnTitle.trim()
      if (!this.columnTitle) return this.resetColumnModal()

      const existing = this.activeKanbanBoard.columns.find(
        c => c.title === this.columnTitle && c.id !== this.selectedColumn?.id
      )
      if (existing) {
        this.editColumnError = 'Column name already exists'
        return
      }

      if (this.selectedColumn) {
        // Update only store-safe fields on the store column object
        const storeCol = this.activeKanbanBoard.columns.find(c => c.id === this.selectedColumn.id)
        if (storeCol) {
          storeCol.title = this.columnTitle
          storeCol.color = this.columnColor
          storeCol.project_id = this.columnProject?.project_id || null
        }
      } else {
        this.activeKanbanBoard.columns.push({
          id: uuidv4(),
          title: this.columnTitle,
          color: this.columnColor,
          project_id: this.columnProject?.project_id || null,
          chats: []
        })
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
        await Promise.all(viewCol.tasks.map(chat => this.$projects.deleteChat(chat)))
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

    async addOrUpdateBoard() {
      const oldName = this.originalBoardName
      const boardName = this.newBoardName.trim()
      if (!boardName) return

      if (this.editBoard && boardName !== oldName && this.kanban.boards[boardName]) {
        throw new Error(`Board '${boardName}' already exists`)
      }

      // Get or create a clean store board config object
      let board = this.editBoard
        ? { ...this.kanban.boards[oldName] }
        : { title: boardName, columns: [], id: boardName }

      if (this.editBoard && boardName !== oldName) {
        // Update chats pointing to old board name
        await Promise.all(
          this.chats
            .filter(c => c.board === oldName)
            .map(c => this.$projects.saveChatInfo({ ...c, board: boardName }))
        )
        delete this.kanban.boards[oldName]
        // Update child board parent references
        Object.values(this.kanban.boards)
          .filter(b => b.parent_id === oldName)
          .forEach(b => (b.parent_id = boardName))
      }

      // Only write safe scalar config fields
      board.title = boardName
      board.description = this.newBoardDescription?.trim()
      board.background = this.newBoardBackground?.trim()
      board.parent_id = this.newBoardParent

      this.kanban.boards[boardName] = board
      await this.saveKanban()
      this.showBoardModal = false
      this.resetNewBoardInfo()
      this.buildViewColumns()
    },

    resetNewBoardInfo() {
      this.newBoardName = ''
      this.newBoardDescription = ''
      this.newBoardParent = null
      this.newBoardBackground = ''
      this.newBoardBranch = ''
      this.selectedTemplate = null
      this.newBoardIssueLink = ''
      this.editBoard = null
      this.originalBoardName = null
    },

    openColumnPropertiesModal(column) {
      // selectedColumn references the store column config (safe scalar fields only)
      this.selectedColumn = this.activeKanbanBoard?.columns?.find(c => c.id === column.id) || null
      this.columnTitle = column.title
      this.columnColor = column.color || '#000000'
      this.columnProject = this.$projects.allProjectsById[column.project_id] || this.$project
      this.confirmDeleteColumn = false
      this.showColumnModal = true
    },

    async saveKanban() {
      await this.$projects.saveKanban()
    },

    showNewBoardModal() {
      this.editBoard = null
      this.originalBoardName = null
      this.newBoardBackground = null
      this.newBoardName = null
      this.newBoardDescription = null
      this.newBoardParent = this.activeBoard?.id || null
      this.showBoardModal = true
    },

    onEditBoard(board) {
      const title = this.board
      this.$emit('edit-board', { title, ...this.kanban.boards[title] })
    },

    onDeleteBoard(boardTitle) {
      // TODO: define logic for child boards and chats cleanup
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

    taskMatchesFilter(task) {
      const text = this.filter?.toLowerCase() || ''
      if (!text) return true
      return (
        task.name?.toLowerCase().includes(text) ||
        task.messages?.some(m => m.content?.toLowerCase().includes(text))
      )
    },

    async moveChatsToColumn({ chats, column }) {
      await Promise.all(
        chats.map(chat => this.$projects.saveChatInfo({ ...chat, column }))
      )
      this.buildViewColumns()
    }
  }
}
</script>