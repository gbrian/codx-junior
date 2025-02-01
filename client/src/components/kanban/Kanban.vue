<script setup>
import draggable from "vuedraggable"
import TaskCard from "./TaskCard.vue"
import ChatViewVue from '../../views/ChatView.vue'
import { v4 as uuidv4 } from 'uuid'
import VSwatches from "../VSwatches.vue"
</script>

<template>
  <div class="flex flex-col gap-2 h-full">
    <ChatViewVue v-if="chat" 
      @chats="onChatEditDone"
      @sub-task="createSubTask"
      @chat="$projects.setActiveChat($event)"
    />
    <div class="flex flex-col gap-2 grow overflow-auto pb-2" v-else>
      <div class="md:text-2xl flex gap-4 items-center justify-between">
        <div class="dropdown">
          <button tabindex="0" class="btn mt-1" @click="toggleDropdown">
            {{ board || "All" }} <i class="fa-solid fa-sort-down"></i>
          </button>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
            <li class="flex gap-2" @click="showNewBoardModal"><a>New board ...</a></li>
            <li v-for="tasksBoard in boardList" :key="tasksBoard.id" @click="selectBoard(tasksBoard.id)">
              <a>{{ tasksBoard.title }} <span v-if="tasksBoard.tasks?.length"> - {{ tasksBoard.tasks.length }} <i class="fa-regular fa-file-lines"></i></span> </a>
            </li>
          </ul>
        </div>
        <div class="flex gap-2">
          <label class="hidden grow input input-sm input-bordered flex items-center gap-2">
            <input type="text" v-model="filter" class="grow" placeholder="Search" />
            <span class="click" v-if="filter" @click.stop="filter = null">
              <i class="fa-regular fa-circle-xmark"></i>
            </span>
            <span v-else><i class="fa-solid fa-filter"></i></span>
          </label>
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
        Position:
        <ul class="steps">
          <li v-for="n in columnList.length" :key="n" :title="n"
          class="step click" @click="columnPosition = n" :class="columnPosition === n && 'step-primary'"></li>
        </ul>
        <div class="modal-action">
          <button class="btn" @click="addOrUpdateColumn">OK</button>
          <button class="btn" @click="showColumnModal = false">Cancel</button>
        </div>
        <div class="badge badge-error" v-if="editColumnError">{{ editColumnError }}</div>
      </modal>
      <div class="grow grid grid-flow-col overflow-x-scroll relative gap-2 justify-start">
        <button class="btn btn-wide btn-primary" @click="showColumnModal = true" v-if="!columnList?.length">
          <i class="fa-solid fa-plus"></i>
          <span class="text-xs md:text-md">Column</span>
        </button>
        <div class="bg-neutral rounded-lg px-3 py-3 w-80 rounded overflow-auto flex flex-col"
          :class="column.color && 'border-t-2'"
          :style="{ borderColor: column.color }"
          v-for="column in columns" :key="column.title" :title="column.position">
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
                <div tabindex="0" role="button" class="btn btn-sm m-1">
                  <i class="fa-solid fa-plus"></i>
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
              @end="onColumnTaskListChanged"
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
      </div>
    </div>
  </div>
</template>

<script>
const ALL_BOARTD_TITLE = "All"
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
      columnPosition: 1,
      isDropdownOpen: false,
      isTaskDropdownOpen: false,
      boards: [],
      selectedColumn: null,
      editColumnError: null,
      activeBoard: null
    }
  },
  created() {
    this.projectChanged()
  },
  computed: {
    chat() {
      return this.$projects.activeChat
    },
    project() {
      return this.$projects.activeProject
    },
    chats() {
      return Object.values(this.$projects.allChats || {}).map(c => ({
        ...c,
        column: c.column || "--none--"
      }))
    },
    boardList() {
      return [
        ...Object.keys(this.boards || {}).map(title => ({ 
          title, 
          id: title,
          tasks: this.chats.filter(c => c.board === title)
        })),
        { title: ALL_BOARTD_TITLE, tasks: this.chats }
      ].reduce((acc, board) => ({ ...acc, [board.title]: board }), {})
    },
    boardColumns () {
      return this.boards[this.board]?.columns
    },
    columns() {
      const columnTitles = this.columnList 
      return columnTitles
          .map((col, ix) => {
            const boardColumn = this.boards[this.board]?.columns.find(bc => bc.title === col)||{}
            return { 
              title: col,
              ...boardColumn,
              tasks: this.activeBoard.tasks.filter(t => (t.column || "--none--") === col),
              position: boardColumn.position || (ix + 1)
            }
          }).sort((a, b) => a.position < b.position ? -1: 1) 
          || []
    },
    columnList() {
      return [...new Set([
        ...this.activeBoard?.tasks.map(t => t.column || "--none--") ||[],
        ...this.boards[this.board]?.columns.map(c => c.title) || []
        ])]
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
    }
  },
  methods: {
    async projectChanged() {
      this.boards = await this.$storex.api.chats.boards.load()
      this.selectBoard(Object.keys(this.boards || {}).find(b => this.boards[b].active) ||
                      this.$ui.kanban || ALL_BOARTD_TITLE)

      this.buildKanban()
    },
    toggleDropdown() {
      this.isDropdownOpen = !this.isDropdownOpen
    },
    selectBoard(board) {
      this.board = board
      this.$ui.setKanban(board)
      this.isDropdownOpen = false
      Object.keys(this.boards || {})
        .forEach(b => this.boards[b].active = (b === board))
      this.activeBoard = this.boardList[this.board] || this.boardList[ALL_BOARTD_TITLE]
      this.saveBoards()
    },
    createNewChat(column) {
      return {
        id: uuidv4(),
        name: "New chat " + this.chats.length + 1,
        mode: 'task',
        profiles: ["analyst"],
        board: this.board || "Default",
        column: column,
        chat_index: 0
      }
    },
    newAnalysisTask(column) {
      this.$projects.newChat({
        ...this.createNewChat(column),
        name: "New Analysis Task",
        mode: 'task',
        profiles: ["analyst"]
      })
    },
    newCodingTask(column) {
      this.$projects.newChat({
        ...this.createNewChat(column),
        name: "New Coding Task",
        mode: 'chat',
        profiles: ["software_developer"]
      })
    },
    async buildKanban() {
      await this.$projects.loadChats()
      if (this.board && !this.boards[this.board]) {
        this.board = Object.keys(this.boards)[0]
        this.$ui.setKanban(this.board)
      }
    },
    async onColumnTaskListChanged() {
      await Promise.all(this.columns.filter(({ tasks }) => !!tasks)
        .map(column => this.updateColumnTaskList(column)))
      this.buildKanban()
      this.saveBoards()
    },
    async updateColumnTaskList(column) {
      if (column.tasks) {
        await Promise.all(column.tasks
          .filter(t => t.column !== column.title)
          .forEach(async (task, ix) => {
            if (task.column !== column.title) {
              task.column = column.title
              task.chat_index = ix
              if (task.id) {
                await this.$projects.saveChatInfo(task)
              }
            }
          }))
      }
    },
    async openChat(element) {
      if (element.id === -1) {
        this.newChat()
      } else {
        await this.$projects.setActiveChat(element)
      }
    },
    onChatEditDone() {
      this.$projects.setActiveChat()
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
      // Move positions
      if (this.selectedColumn?.position !== this.columnPosition
          && this.boardColumns.find(c => c.position === this.columnPosition)) {
            this.boardColumns.filter(c => c.position >= this.columnPosition)
                .map(c => c.position++)
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
        this.selectedColumn.position = this.columnPosition
      } else {
        const newColumn = {
          title: this.columnName,
          color: this.columnColor
        }
        this.boardColumns.push(newColumn)
      }
      
      await this.saveBoards()
      this.selectBoard(this.activeBoard.title)
      this.resetColumnModal()
    },
    resetColumnModal() {
      this.showColumnModal = false
      this.columnName = ''
      this.columnColor = '#000000'
      this.columnPosition = this.boards[this.board].columns.length - 1
      this.selectedColumn = null
      this.editColumnError = null
    },
    async addBoard() {
      const boardName = this.newBoardName.trim()
      if (boardName && !this.boards[boardName]) {
        this.boards[boardName] = {}
        this.board = boardName
        await this.saveBoards()
        this.buildKanban()
      }
      this.newBoardName = ''
      this.showBoardModal = false
    },
    openColumnPropertiesModal(column) {
      this.selectedColumn = column
      this.columnName = column?.title
      this.columnColor = column?.color || '#000000'
      this.columnPosition = column?.position || this.columnList.length
      this.showColumnModal = true
    },
    async saveBoards() {
      await this.$storex.api.chats.boards.save(this.boards)
    },
    showNewBoardModal() {
      this.showBoardModal = true
    }
  }
}
</script>