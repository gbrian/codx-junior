<script setup>
import draggable from "vuedraggable"
import TaskCard from "./TaskCard.vue"
import ChatViewVue from '../../views/ChatView.vue'
import { v4 as uuidv4 } from 'uuid'
import VSwatches from "../VSwatches.vue"
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
</script>

<template>
  <SplitterGroup id="splitter-group-1" direction="horizontal" auto-save-id="splitter-group-1">
    <SplitterPanel :order="0" class="flex flex-col gap-2 grow overflow-auto pb-2">
      <div class="md:text-2xl flex gap-4 items-center">
        <div class="dropdown">
          <button tabindex="0" class="btn btn-primary btn-sm mt-1" @click="toggleDropdown">
            Board {{ activeBoard?.title }} <i class="fa-solid fa-sort-down"></i>
          </button>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
            <li class="flex gap-2 text-secondary" @click="showNewBoardModal"><a><i class="fa-solid fa-plus"></i> New board</a></li>
            <li v-for="tasksBoard in boards" :key="tasksBoard.id" @click="selectBoard(tasksBoard.id)">
              <a>{{ tasksBoard.title }} <span v-if="tasksBoard.tasks?.length"> - {{ tasksBoard.tasks.length }} <i class="fa-regular fa-file-lines"></i></span> </a>
            </li>
          </ul>
        </div>
        <div class="grow"></div>
        <div class="flex gap-2">
          <div class="hidden grow input input-sm input-bordered flex items-center gap-2">
            <input type="text" v-model="filter" class="grow" placeholder="Search" />
            <span class="click" v-if="filter" @click.stop="filter = null">
              <i class="fa-regular fa-circle-xmark"></i>
            </span>
            <span v-else><i class="fa-solid fa-filter"></i></span>
          </div>
          <button class="btn btn-sm" @click="showColumnModal = true" v-if="columnList?.length">
            <i class="fa-solid fa-plus"></i>
            <span class="text-xs md:text-md">Column</span>
          </button>
        </div>
      </div>
      <modal v-if="showBoardModal">
        <h2 class="font-bold text-lg">Add New Board</h2>
        <input type="text" v-model="newBoardName" placeholder="Enter board name" class="input input-bordered w-full mt-2"/>
        <div class="modal-action">
          <button class="btn" @click="addBoard">OK</button>
          <button class="btn" @click="showBoardModal = false">Cancel</button>
        </div>
      </modal>
      <modal v-if="showColumnModal">
        <h2 class="font-bold text-lg">Add/Edit Column</h2>
        <div class="flex gap-1 items-center">
          <input type="text" v-model="columnName" placeholder="Enter column name"
            class="grow input input-bordered w-full"/>
          <VSwatches v-model="columnColor" class="h-full mt-1" />
        </div>
        <span v-if="editColumnError" class="text-error">{{ editColumnError }}</span>
        <div class="modal-action">
          <button class="btn" @click="addOrUpdateColumn">OK</button>
          <button class="btn" @click="showColumnModal = false">Cancel</button>
        </div>
        <div class="badge badge-error" v-if="editColumnError">{{ editColumnError }}</div>
      </modal>
      <div class="grow">
        <button class="btn btn-wide btn-primary" @click="showColumnModal = true" v-if="!columnList?.length">
          <i class="fa-solid fa-plus"></i>
          <span class="text-xs md:text-md">Column</span>
        </button>
        <draggable
          v-model="columns"
          group="tasks"
          :itemKey="c => c.title + c.position"
          @end="onColumnTaskListChanged"
          class="mt-3 min-h-60 grid grid-flow-col overflow-x-scroll relative gap-2 justify-start"
        >
          <template #item="{ element: column }">
            <div class="bg-neutral rounded-lg px-3 py-3 w-80 rounded overflow-auto flex flex-col"
              :class="column.color && 'border-t-2'"
              :style="{ borderColor: column.color }"
            >
              <div class="group text-neutral-content font-semibold font-sans tracking-wide text-sm flex gap-2 items-center">
                <div class="click w-6 h-6 flex items-center justify-center rounded-md group shadow-lg bg-base-100" 
                  :style="{ backgroundColor: column.color }" @click="openColumnPropertiesModal(column)">
                  <span class="hidden group-hover:block">
                    <i class="fa-solid fa-pen-to-square"></i>
                  </span>
                </div>
                <div class="flex gap-2 items-center grow">
                  <div>{{column.title}}</div>
                </div>
                <div class="flex gap-2 items-center">
                  <div class="dropdown dropdown-end">
                    <div tabindex="0" role="button" class="btn btn-sm m-1 flex items-center">
                      <span v-if="column.tasks?.length">({{ column.tasks.length  }})</span>
                      <i class="mt-1 fa-solid fa-plus"></i>
                    </div>
                    <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
                      <li class="flex gap-2" @click="newAnalysisTask(column.title)">
                        <a>Analysis task</a>
                      </li>
                      <li class="flex gap-2" @click="newCodingTask(column.title)">
                        <a>Coding task</a>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
              <div class="grow overflow-y-auto">
                <draggable
                  v-model="column.tasks"
                  group="tasks"
                  :itemKey="column.title"
                  @end="onColumnTaskListChanged(column)"
                  class="mt-3"
                >
                  <template #item="{ element: task }">
                    <task-card
                      :task="task"
                      :itemKey="task.id"
                      class="cursor-move overflow-hidden mt-2"
                      @click="openChat(task)"
                    />
                  </template>
                </draggable>
              </div>
            </div>
          </template>
        </draggable>
      </div>
    </SplitterPanel>
    <SplitterResizeHandle 
      id="splitter-group-1-resize-handle-2" 
      class="bg-stone-800 hover:bg-slate-600 w-1" v-if="chat">
    </SplitterResizeHandle>
    <SplitterPanel :order="1" class="flex-shrink-0 w-1/3 flex" v-if="chat">
      <ChatViewVue
        class="ml-2 w-full"
        @chats="onChatEditDone"
        @sub-task="createSubTask"
        @chat="$projects.setActiveChat($event)"
      />
    </SplitterPanel>
  </SplitterGroup>
</template>

<script>
const ALL_BOARD_TITLE = "All"
const ALL_BOARD_TITLE_ID = "$$$$All@@@@"

export default {
  data() {
    return {
      board: null,
      filter: null,
      showBoardModal: false,
      showColumnModal: false,
      newBoardName: '',
      columnName: '',
      columnColor: '#000000',
      isDropdownOpen: false,
      kanban: {},
      selectedColumn: null,
      editColumnError: null,
      columns: []
    }
  },
  mounted() {
    this.projectChanged()
  },
  computed: {
    chats() {
      const allChats = this.$projects.allChats
      return Object.values(allChats || {}).map(c => ({
          ...c,
          column: c.column || "--none--"
        }))
    },
    chat() {
      return this.$projects.activeChat
    },
    project() {
      return this.$projects.activeProject
    },
    activeBoard() {
      return this.boards[this.board]
    },
    boardColumns() {
      return this.boards[this.board]?.columns
    },
    columnList() {
      return this.boards[this.board]?.columns?.map(c => c.title) || []
    },
    boards() {
      const boards = this.kanban?.boards || {} 
      return [
                ...Object.keys(boards).map(board => ({ ...boards[board], id: board, title: board })), 
                {
                  title: ALL_BOARD_TITLE,
                  id: ALL_BOARD_TITLE_ID,
                  columns: Object.values(this.kanban?.boards || {}).reduce((acc, b) => acc.concat(b.columns.map(c => ({ ...c, board: b }))), [])
                }
              ].reduce((acc, b) => ({ ...acc, [b.id]: {
                ...b,
                tasks: this.chats.filter(c => b.id === ALL_BOARD_TITLE_ID || c.board === b.title)
            }}), {})
    }
  },
  watch: {
    filter(newValue, oldValue) {
      if ((!newValue && oldValue) || newValue?.length > 3) {
        this.buildKanban()
      }
    },
    project() {
      this.projectChanged()
    },
    board() {
      this.buildKanban()
    },
    chats() {
      this.buildKanban()
    }
  },
  methods: {
    async projectChanged() {
      this.kanban = await this.$storex.api.chats.kanban.load()
      this.selectBoard(Object.keys(this.boards || {}).find(b => this.boards[b].active) ||
                      this.$ui.kanban || ALL_BOARD_TITLE_ID)
      this.buildKanban()
    },
    toggleDropdown() {
      this.isDropdownOpen = !this.isDropdownOpen
    },
    selectBoard(board) {
      board = board || ALL_BOARD_TITLE_ID
      this.board = board
      this.$ui.setKanban(board)
      this.isDropdownOpen = false
      if (this.kanban.boards[board] && !this.kanban.boards[board].active) {
        Object.keys(this.kanban.boards)
          .forEach(b => this.kanban.boards[b].active = (b === board))
        this.saveKanban()
      }
    },
    createNewChat(base) {
      return this.$projects.createNewChat({
        id: uuidv4(),
        name: "New chat " + this.chats.length + 1,
        mode: 'task',
        profiles: ["analyst"],
        board: this.board || "Default",
        chat_index: 0,
        ...base
      })
    },
    newAnalysisTask(column) {
      this.createNewChat({
        column,
        name: "New Analysis Task",
        mode: 'task',
        profiles: ["analyst"]
      })
    },
    newCodingTask(column) {
      this.createNewChat({
        column,
        name: "New Coding Task",
        mode: 'chat',
        profiles: ["software_developer"]
      })
    },
    async buildKanban() {
      if (this.board && !this.boards[this.board]) {
        this.board = Object.keys(this.boards)[0]
        this.$ui.setKanban(this.board)
      }
      this.buildColumns()
    },
    buildColumns() {
      const columnTitles = this.columnList 
      this.columns = columnTitles
          .map((col, ix) => {
            const boardColumn = this.boards[this.board]?.columns?.find(bc => bc.title === col)||{}
            const columnChats = boardColumn.chats || {}
            const getChatIndex = c => {
              return columnChats[c.id]?.chat_index || 0 
            }
            return { 
              title: col,
              ...boardColumn,
              tasks: this.activeBoard.tasks
                      .filter(t => (t.column || "--none--") === col)
                      .sort((a, b) => getChatIndex(a) < getChatIndex(b) ? -1 : 1),
              position: ix
            }
          }).sort((a, b) => a.position < b.position ? -1: 1)
          || []
    },
    async onColumnTaskListChanged() {
      const { columns } = this.boards[this.board]
      this.boards[this.board].columns = await Promise.all(this.columns.map(async (column, ix) => {
        const currentColumn = columns.find(c => c.title === column.title)
        currentColumn.chats = column.tasks.reduce((acc, t, chat_index) => ({ ...acc, [t.id]: { chat_index }}), {})
        await Promise.all(column.tasks.filter(t => t.column !== column.title)
          .map(task => this.$storex.projects.saveChatInfo({ ...task, column: column.title })))
        return currentColumn
      }))
      
      this.saveKanban()
    },
    async openChat(element) {
      if (element.id === -1) {
        this.newChat()
      } else {
        await this.$projects.setActiveChat(element)
      }
    },
    async onChatEditDone() {
      await this.$projects.setActiveChat()
      this.buildKanban()
    },
    async createSubTask(parent) {
      const chat = this.createNewChat(parent.column)
      if (!parent.id) {
        parent.id = uuidv4()
      }
      chat.parent_id = parent.id
      chat.column = parent.column
      chat.column_ix = parent.column_ix
      this.$projects.newChat(chat)
    },
    async addOrUpdateColumn() {
      this.columnName = this.columnName.trim()
      if (!this.columnName) {
        return this.resetColumnModal()
      }
      if (this.selectedColumn?.title !== this.columnName && this.columns[this.columnName]) {
        this.editColumnError = "Name already used"
        return
      }
      if (this.selectedColumn) {
        this.chats.forEach(chat => {
          if (chat.column === this.selectedColumn.title) {
            chat.column = this.columnName
            this.$storex.api.chats.saveChatInfo(chat)
          }
        })
        this.selectedColumn.title = this.columnName
        this.selectedColumn.color = this.columnColor
      } else {
        const newColumn = {
          id: uuidv4(),
          title: this.columnName,
          color: this.columnColor
        }
        if (this.boardColumns) {
          this.boardColumns.push(newColumn)
        } else {
          this.boards[this.board].columns = [newColumn]
        }
      }
      
      await this.saveKanban()
      this.selectBoard(this.activeBoard.title)
      this.resetColumnModal()
    },
    resetColumnModal() {
      this.showColumnModal = false
      this.columnName = ''
      this.columnColor = '#000000'
      this.selectedColumn = null
      this.editColumnError = null
    },
    async addBoard() {
      const boardName = this.newBoardName.trim()
      if (boardName && !this.boards[boardName]) {
        this.kanban.boards[boardName] = {
          id: uuidv4(),
          columns: []
        }
        await this.saveKanban()
      }
      this.newBoardName = ''
      this.showBoardModal = false
      this.board = boardName
      this.buildKanban()
    },
    openColumnPropertiesModal(column) {
      this.selectedColumn = column
      this.columnName = column?.title
      this.columnColor = column?.color || '#000000'
      this.showColumnModal = true
    },
    async saveKanban() {
      await this.$storex.api.chats.kanban.save(this.kanban)
    },
    showNewBoardModal() {
      this.showBoardModal = true
    }
  }
}
</script>