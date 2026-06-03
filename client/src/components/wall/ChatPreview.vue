<script setup>
import moment from 'moment'
import ChatEntry from '../ChatEntry.vue'
import ProjectIcon from '../ProjectIcon.vue'
import Document from '../document/Document.vue';
</script>
<template>
  <div class="border border-slate-700 hover:border-slate-400 rounded-lg my-2 click group bg-base-300">
    <div class="flex gap-2 bg-slate-800 px-2 rounded-t-lg border-b border-slate-600">
      <div class="flex flex-col">
        <div class="flex gap-4 items-center">
          <ProjectIcon inline="true" :project="project" v-if="project" />
          <span class="underline">{{ chat.name }}</span>
        </div>
        <div class="px-2 flex gap-2 items-center" @click.stop="navigateBoard($project, chat.board)">
          <button classs="btn btn-sm btn-primary">
            <i class="fa-brands fa-trello"></i>
            {{ chat.board }} 
            <i class="fa-solid fa-table-columns"></i>
            {{ chat.column }} 
          </button>
        </div>
      </div>
      <div class="grow"></div>
      <span class="badge badge-outline mt-4">{{ moment(chat.updated_at).fromNow() }} </span>
    </div>      
    <div class="relative p-2">
      <ChatEntry
        class="rounded-b-lg overflow-auto opacity-60 h-60 group-hover:opacity-100" 
        :menu-less="true" 
        :message="chat.messages[0]" :chat="chat"
        v-if="chat.messages[0]"
        />
        <div v-else>
          <Document :content="chat.description" />
        </div>
      <div class="absolute top-0 left-0 right-0 bottom-0 z-20"></div>
    </div>
  </div>
</template>
<script>
export default {
  props: ['project', 'chat'],
  methods: {
    navigateBoard(project, board) {
      this.$router.$navigate.kanban.board({ project, board })
    }
  }
}
</script>
