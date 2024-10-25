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
        <div class="flex gap-1">
          Kanban <span class="hidden md:block">board</span>
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
      <div class="dropdown" v-if="false">
        <div tabindex="0" class="click text-2xl flex gap-2 items-center">
          {{ board || defBoard }}
          <i class="fa-solid fa-sort-down"></i>
        </div>
        <ul tabindex="0" class="dropdown-content menu bg-base-200 rounded-md w-60 z-50">
          <li v-for="tasksBoard in boards" :key="tasksBoard">
            <a>{{ tasksBoard }}</a>
          </li>
        </ul>
      </div>
        <div class="flex grow min-w-full overflow-x-scroll">
          
          <draggable 
              v-model="columns"
              group="columns" 
              @change="onColumnsChanged()" 
              item-key="title"
              class="flex overflow-auto"
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
const unassigned = "<none>"
export default {
  data() {
    return {
      board: unassigned,
      filter: null,
      columns: []
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
      return [...new Set(this.chats?.map(c => c.board))]             
    },
    chats () {
      return this.$projects.chats.map(c => ({
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
    }
  },
  methods: {
    createNewChat () {
      return {
        id: 0,
        name: "New chat",
        mode: 'chat',
        board: this.board,
        column: "New column",
        column_index: 10000,
        chat_index: 0
      }
    },
    newChat (column) {
      this.$projects.newChat(column)
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
        await this.$projects.setActiveChat(element.name)
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
