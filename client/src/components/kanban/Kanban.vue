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
              <a>{{ tasksBoard.title }}</a>
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
          <button class="btn btn-sm" @click="showColumnModal = true">
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
          <li v-for="n in Math.max(columnPosition, columnList.length)" :key="n"
          class="step click" @click="columnPosition = n" :class="columnPosition === n && 'step-primary'"></li>
        </ul>
        <div class="modal-action">
          <button class="btn" @click="addOrUpdateColumn">OK</button>
          <button class="btn" @click="showColumnModal = false">Cancel</button>
        </div>
        <div class="badge badge-error" v-if="editColumnError">{{ editColumnError }}</div>
      </modal>
      <div class="grow grid grid-flow-col overflow-x-scroll relative gap-2">
        <div class="bg-neutral rounded-lg px-3 py-3 w-80 rounded overflow-auto flex flex-col"
          :class="column.color && 'border-t-2'"
          :style="{ borderColor: column.color }"
          v-for="column in columns" :key="column.name">
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
export default {
  data() {
    return {
      board: null,
      filter: null,
      columns: [],
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
      editColumnError: null
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
      return this.$projects.chats.map(c => ({
        ...c,
        board: c.board || this.board,
        column: c.column || "--none--"
      }))
    },
    activeBoard() {
      return this.boards[this.board] || {}
    },
    boardList() {
      return [
        ...Object.keys(this.boards || {}).map(title => ({ title, id: title })),
        { title: "All" }
      ]
    },
    columnList() {
      return this.board 
        ? (this.activeBoard?.columns || []) 
        : [...new Set(this.chats.map(c => c.column))]
            .filter(col => !!col)
            .map(title => ({ title }))
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
      this.board = Object.keys(this.boards || {}).find(b => this.boards[b].active) ||
                      this.$ui.kanban
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
      this.columns = this.columnList.map((column, index) => ({
        ...column,
        title: column.title,
        tasks: this.chats
          .filter(c => c.column === column.title && (!this.filter || c.name.toLowerCase().includes(this.filter.toLowerCase())))
          .sort((a, b) => a.chat_index - b.chat_index)
      }))
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
      if (this.columnName.trim()) {
        if (!this.activeBoard.columns) {
          this.activeBoard.columns = []
        }
        const activeBoardColumns = this.activeBoard.columns

        if (this.selectedColumn) {
          const oldColumnIndex = activeBoardColumns.findIndex(col => col.title === this.selectedColumn.title)
          if (oldColumnIndex !== -1) {
            this.chats.forEach(chat => {
              if (chat.column === this.selectedColumn.title) {
                chat.column = this.columnName
                this.$storex.api.chats.saveChatInfo(chat)
              }
            })
            activeBoardColumns.splice(oldColumnIndex, 1)
          }
        } else {
          const columnsWithSameName = activeBoardColumns.filter(
            (col) => col.title.toLowerCase() === this.columnName.toLowerCase()
          )

          if (columnsWithSameName.length > 1) {
            this.editColumnError = "Name already used"
            return
          }
        }

        const newColumn = {
          title: this.columnName,
          color: this.columnColor
        }

        activeBoardColumns.splice(this.columnPosition - 1, 0, newColumn)
        await this.saveBoards()
        this.buildKanban()
      }
      this.resetColumnModal()
    },
    resetColumnModal() {
      this.showColumnModal = false
      this.columnName = ''
      this.columnColor = '#000000'
      this.columnPosition = 1
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
      const columnIndex = this.columns.findIndex(c => c.title === column.title)
      this.selectedColumn = {
        ...column,
        index: columnIndex
      }
      this.columnName = column.title
      this.columnColor = column.color || '#000000'
      this.columnPosition = columnIndex + 1
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