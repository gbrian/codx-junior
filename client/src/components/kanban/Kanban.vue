<script setup>
import draggable from "vuedraggable"
import TaskCard from "./TaskCard.vue"
import { API } from '../../api/api'
import ChatViewVue from '../../views/ChatView.vue'
</script>
<template>
  <div class="flex flex-col gap-2 h-full">
    <ChatViewVue v-if="chat" @chats="onChatEditDone" ></ChatViewVue>
    <div class="flex flex-col gap-2 grow overflow-auto pb-2" v-else>
      <div class="md:text-2xl flex gap-4 items-center justify-between">
        <div class="dropdown">
          <button tabindex="0" class="btn m-1 dropdown-toggle" @click="toggleDropdown">
            {{ board || 'Kanban' }} <i class="fa-solid fa-sort-down"></i>
          </button>
          <ul v-if="isDropdownOpen" tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
            <li class="flex gap-2" @click="showModal = true"><a>New board ...</a></li>
            <hr>
            <li v-for="tasksBoard in boards" :key="tasksBoard" @click="selectBoard(tasksBoard)">
              <a>{{ tasksBoard || 'Kanban board' }}</a>
            </li>
          </ul>
        </div>
        <div class="flex gap-2">
          <label class="grow input input-sm input-bordered flex items-center gap-2">
            <input type="text" v-model="filter" class="grow" placeholder="Search" />
            <span class="click" v-if="filter" @click.stop="filter = null">
              <i class="fa-regular fa-circle-xmark"></i>
            </span>
            <span v-else><i class="fa-solid fa-filter"></i></span>
          </label>
          <button class="btn btn-sm" @click="addColumn">
            <i class="fa-solid fa-plus"></i>
            <span class="hidden md:block">Column</span>
          </button>
        </div>
      </div>  
      <modal v-if="showModal">
        <div class="modal-box">
          <h2 class="font-bold text-lg">Add New Board</h2>
          <input type="text" v-model="newBoardName" placeholder="Enter board name" class="input input-bordered w-full mt-2"/>
          <div class="modal-action">
            <button class="btn" @click="addBoard">OK</button>
            <button class="btn" @click="showModal = false">Cancel</button>
          </div>
        </div>
      </modal>
      <div class="flex grow w-full overflow-x-scroll relative">
        <draggable 
            v-model="columns"
            group="columns" 
            @change="onColumnsChanged()" 
            item-key="title"
            class="flex overflow-auto absolute top-0 left-0 right-0 bottom-0"
          >
          <template #item="{element}">
            <div class="bg-neutral rounded-lg px-3 py-3 column-width rounded mr-8 overflow-auto">
              <p class="text-neutral-content font-semibold font-sans tracking-wide text-sm flex justify-between items-center">
                <div class="flex input input-bordered input-sm" v-if="element.editTitle">
                  <input type="text" v-model="element.newTitle"
                    @keydown.esc="element.editTitle = false"
                    @keydown.enter="onColumnTitleChanged(element)"
                  >
                </div>
                <div class="click" @click="onEditColumnTitle(element)" v-else>{{element.title}}</div>
                <button class="btn btn-sm" @click="newChat(element.title)">
                  <i class="fa-solid fa-plus"></i>
                </button>
              </p>
              <draggable 
                v-model="element.tasks" 
                group="tasks" 
                @change="onColumnTaskListChanged(element)" 
                item-key="title">
                <template #item="{element}">
                  <task-card
                    :task="element"
                    class="mt-3 cursor-move overflow-hidden"
                    @click="openChat(element)"
                  ></task-card>
                </template>
              </draggable>
            </div>
          </template>
        </draggable>
      </div>
    </div>
  </div>
</template>
<script>
const unassigned = ""
export default {
  data() {
    return {
      board: unassigned,
      filter: null,
      columns: [],
      showModal: false,
      newBoardName: '',
      isDropdownOpen: false,
    };
  },
  created () {
    this.buildKanba()
  },
  computed: {
    chat () {
      return this.$projects.activeChat
    },
    project () {
      return this.$projects.activeProject
    },
    boards () {
      return [...new Set(this.$projects.chats?.map(c => c.board))] 
    },
    chats () {
      return this.$projects.chats
            .filter(({ board }) => this.board === board)
            .map(c => ({
              ...c,
              board: c.board || unassigned,
              column: c.column || unassigned
            }))
    },
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
      this.isDropdownOpen = false;
    },
    createNewChat (column) {
      return {
        id: 0,
        name: "New chat " + this.chats.length + 1,
        mode: 'chat',
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
      await this.$projects.loadChats()
      const columnName = [...new Set(this.chats?.map(c => c.column))]
      const columns = columnName.map(columnName => ({
          title: columnName,
          tasks: this.chats.filter(c => c.column === columnName &&
              (!this.filter || c.name.toLowerCase().indexOf(this.filter.toLowerCase()) !== -1)
            )
            .sort((a, b) => a.chat_index < b.chat_index ? -1 : 1)

        })).sort((a, b) => a.tasks[0]?.column_index < b.tasks[0]?.column_index ? -1 : 1)
      this.columns = columns
      if (!this.columns.length) {
        this.addColumn()
      }
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
    addColumn () {
      this.columns = [
        ...this.columns,
        {
          title: "new column",
          tasks: []
        }]
    },
    addBoard() {
      if (this.newBoardName.trim()) {
        this.board = this.newBoardName;
      }
      this.newBoardName = '';
      this.showModal = false;
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