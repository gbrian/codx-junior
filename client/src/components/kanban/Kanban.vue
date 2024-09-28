<script setup>
import draggable from "vuedraggable"
import TaskCard from "./TaskCard.vue"
import { API } from '../../api/api'
import ChatViewVue from '../../views/ChatView.vue'
</script>
<template>
  <ChatViewVue :openChat="chat" v-if="chat" @chats="onChatEditDone" ></ChatViewVue>
  <div class="flex flex-col gap-2 h-full" v-else>
    <div class="dropdown">
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
    <div class="flex justify-center grow overflow-auto">
      <div class="flex min-h-screen min-w-full overflow-x-scroll">
        
        <draggable 
            v-model="columns"
            group="columns" 
            @change="onColumnsChanged()" 
            item-key="title"
            class="flex overflow-auto"
          >
          <template #item="{element}">
            <div class="bg-neutral rounded-lg px-3 py-3 column-width rounded mr-4 overflow-auto">
              <p class="text-neutral-content font-semibold font-sans tracking-wide text-sm flex justify-between items-center">
                <div class="flex input input-bordered input-sm" v-if="element.editTitle">
                  <input type="text" v-model="element.newTitle"
                    @keydown.esc="element.editTitle = false"
                    @keydown.enter="onColumnTitleChanged(element)"
                  >
                </div>
                <div class="click" @click="onEditColumnTitle(element)" v-else>{{element.title}}</div>
                <button class="btn btn-sm" @click="newChat (element.title)">
                  <i class="fa-solid fa-plus"></i>
                </button>
              </p>
              <draggable 
                v-model="element.tasks" 
                group="tasks" 
                @change="onColumnTasksChanged(column)" 
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
      chat: null,
      chats: [],
      columns: [],
      board: unassigned
    };
  },
  created () {
    this.buildKanba()
  },
  computed: {
    boards () {
      return [...new Set(this.chats?.map(c => c.board))]             
    }
  },
  methods: {
    newChat (column) {
      this.chat = {
        name: "New chat",
        board: this.board,
        column,
        column_index: 0
      }
    },
    async buildKanba () {
      this.chats = await API.chats.list()
      this.chats = this.chats
                    .map(c => ({
                      ...c,
                      board: c.board || unassigned,
                      column: c.column || unassigned
                    }))
      const columns = [...new Set(this.chats?.map(c => c.column))]
      this.columns = [...columns.map(col => ({
          title: col,
          tasks: this.chats.filter(c => c.column === col)
            .sort((a, b) => a.chat_index < b.chat_index ? -1 : 1)
        })),
        {
          title: "New column",
          tasks: [{
            name: "New chat",
            board: this.board,
            column: "New column",
            column_index: 10000,
            chat_index: 0
          }]
        }
      ].sort((a, b) => a.tasks[0]?.column_index < b.tasks[0]?.column_index ? -1 : 1)
    },
    onColumnTasksChanged(column) {
      const column_index = this.columns.findIndex(c => c.title === column.title)
      column.tasks.forEach((task, ix) => {
        task.column = column.title,
        task.column_index = column_index
        task.chat_index = ix
        task.id && API.chats.save(task, true)
      })
      this.buildKanba()
    },
    onEditColumnTitle(column) {
      column.newTitle = column.title
      column.editTitle = true
    },
    onColumnTitleChanged(column) {
      column.title = column.newTitle
      column.editTitle = false
      this.onColumnTasksChanged(column)
    },
    onColumnsChanged() {},
    async openChat(element) {
      this.chat = await API.chats.loadChat(element.name)
    },
    onChatEditDone () {
      this.chat = null
      this.buildKanba()
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
