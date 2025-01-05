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
    ></ChatViewVue>
    <div class="flex flex-col gap-2 grow overflow-auto pb-2" v-else>
      <div class="md:text-2xl flex gap-4 items-center justify-between">
        <div class="dropdown">
          <button tabindex="0" class="btn mt-1 dropdown-toggle" @click="toggleDropdown">
            {{ board }} <i class="fa-solid fa-sort-down"></i>
          </button>
          <ul v-if="isDropdownOpen" tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
            <li class="flex gap-2" @click="showBoardModal = true"><a>New board ...</a></li>
            <hr>
            <li v-for="tasksBoard in boardList" :key="tasksBoard" @click="selectBoard(tasksBoard)">
              <a>{{ tasksBoard }}</a>
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
        Position:
        <ul class="steps">
          <li v-for="n in columnList.length" :key="n"
          class="step click" @click="columnPosition = n" :class="columnPosition === n && 'step-primary'"></li>
        </ul>
        <div class="modal-action">
          <button class="btn" @click="addOrUpdateColumn">OK</button>
          <button class="btn" @click="showColumnModal = false">Cancel</button>
        </div>
      </modal>
      <div class="flex grow w-full overflow-x-scroll relative">
        <div class="bg-neutral rounded-lg px-3 py-3 column-width rounded mr-8 overflow-auto"
          v-for="column in columns" :key="column.name">
          <div class="group text-neutral-content font-semibold font-sans tracking-wide text-sm flex gap-2 items-center">
            <span class="click" @click="openColumnPropertiesModal(column)">
              <i class="fa-solid fa-pen-to-square"></i>
            </span>
            <div class="flex gap-2 items-center grow">
              <div>{{column.title}}</div>
            </div>
            <div class="flex gap-2 items-center">
              <button class="btn btn-sm" @click="newChat(column.title)">
                <i class="fa-solid fa-plus"></i>
              </button>
            </div>
          </div>
            <task-card
              v-for="task in column.tasks" :key="task.name"
              :task="task"
              class="mt-3 cursor-move overflow-hidden"
              @click="openChat(task)"
            ></task-card>
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
      boards: [],
    };
  },
  created () {
    this.board = this.$ui.kanban
    this.buildKanba()
  },
  computed: {
    chat () {
      return this.$projects.activeChat
    },
    project () {
      return this.$projects.activeProject
    },
    chats () {
      return this.$projects.chats
            .filter(({ board }) => this.board === board)
            .map(c => ({
              ...c,
              board: c.board || this.board,
              column: c.column || "tasks"
            }))
    },
    boardList () {
      return Object.keys(this.boards || {})
    },
    columnList () {
      return this.boards ? Object.keys(this.boards[this.board].columns) : []
    }
  },
  watch: {
    filter (newValue, oldValue) {
      if ((!newValue && oldValue) || newValue?.length > 3) {
        this.buildKanba()
      }
    },
    project () {
      this.buildKanba()
    },
    board () {
      this.buildKanba()
    }
  },
  methods: {
    toggleDropdown() {
      this.isDropdownOpen = !this.isDropdownOpen;
    },
    selectBoard(board) {
      this.board = board;
      this.$ui.setKanban(board)
      this.isDropdownOpen = false;
    },
    createNewChat (column) {
      return {
        id: uuidv4(),
        name: "New chat " + this.chats.length + 1,
        mode: 'task',
        board: this.board,
        column: column,
        column_index: 10000,
        chat_index: 0
      }
    },
    newChat (column) {
      this.$projects.newChat(this.createNewChat(column))
    },
    async buildKanba () {
      this.boards = await this.$storex.api.chats.boards.load()
      await this.$projects.loadChats()
      if (!this.boards[this.board]) {
        this.board = Object.keys(this.boards)[0]
        this.$ui.setKanban(this.board)
      }
      this.columns = this.columnList.map(columnName => ({
          title: columnName,
          tasks: this.chats.filter(c => c.column === columnName &&
              (!this.filter || c.name.toLowerCase().indexOf(this.filter.toLowerCase()) !== -1)
            )
            .sort((a, b) => a.chat_index < b.chat_index ? -1 : 1)

        })).sort((a, b) => a.tasks[0]?.column_index < b.tasks[0]?.column_index ? -1 : 1)
    },
    async onColumnTaskListChanged() {
      await Promise.all(this.columns.map(column =>
        this.updateColumnTaskList(column )))
      this.buildKanba()
    },
    async updateColumnTaskList(column) {
      const column_index = this.columns.findIndex(c => c.title === column.title)
      await Promise.all(column.tasks
        .filter(t => t.column !== column.title)
        .map(async (task, ix) => {
          task.column = column.title,
          task.column_index = column_index
          task.chat_index = ix
          if (task.id) {
            await this.$projects.saveChatInfo(task)
          }
        }))
    },
    onEditColumnTitle(column) {
      column.newTitle = column.title
      column.editTitle = true
    },
    onColumnTitleChanged(column) {
      column.title = column.newTitle
      column.editTitle = false
      this.onColumnTaskListChanged(column)
    },
    onColumnsChanged() {},
    async openChat(element) {
      if (element.id === -1) {
        this.newChat()
      } else {
        await this.$projects.setActiveChat(element)
      }
    },
    onChatEditDone () {
      this.$projects.setActiveChat()
      this.buildKanba()
    },
    async createSubTask(parent) {
      const chat = this.createNewChat(parent.column)
      if (!parent.id) {
        parent.id = uuidv4() // Legacy...
      }
      chat.parent_id = parent.id
      chat.column = parent.column
      chat.column_ix = parent.column_ix
      this.$projects.newChat(chat)
    },
    addColumn (columnName) {
      this.columns = [
        ...this.columns,
        {
          title: columnName,
          tasks: []
        }]
    },
    addOrUpdateColumn() {
      if (this.columnName.trim()) {
        const newColumn = {
          title: this.columnName,
          color: this.columnColor,
          position: this.columnPosition,
          tasks: []
        };
        
        this.columns.push(newColumn);
        this.sortColumnsByPosition();
      }
      this.resetColumnModal();
    },
    sortColumnsByPosition() {
      this.columns.sort((a, b) => a.position - b.position);
    },
    resetColumnModal() {
      this.showColumnModal = false;
      this.columnName = '';
      this.columnColor = '#000000';
      this.columnPosition = 1;
    },
    addBoard() {
      if (this.newBoardName.trim()) {
        this.board = this.newBoardName;
      }
      this.newBoardName = '';
      this.showBoardModal = false;
    },
    openColumnPropertiesModal(column) {
      this.showColumnModal = column;
    }
  }
};
</script>

<style scoped>
.column-width {
  min-width: 320px;
  width: 320px;
}
/* Unfortunately @apply cannot be setup in codesandbox, 
but you'd use "@apply border opacity-50 border-blue-500 bg-gray-200" here */
.ghost-card {
  opacity: 0.5;
  background: #F7FAFC;
  border: 1px solid #4299e1;
}
</style>