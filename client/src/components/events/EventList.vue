<script setup>
import moment from 'moment';
</script>
<template>
  <div class="flex flex-col gap-4 h-96 overflow-auto">
    <div v-for="event in $storex.session.events" :key="event.ts" class="card border border-gray-200 shadow-md bg-base-300">
      <div class="card-body">
        <span class="text-gray-500 text-xs">[{{ moment(event.ts).fromNow() }}]</span>
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-2">
            <i :class="getIcon(event.type)" class="fa-lg"></i>
            <span class="text-lg font-semibold">{{ getProjectName(event.codx_path) }}</span>
          </div>
          <i class="fas fa-times cursor-pointer" @click="setEventAsRead(event)"></i>
        </div>
        <div class="flex flex-col">
          <span class="text-gray-800">{{ event.message }}</span>
          <span class="text-sm" v-if="event.chat">{{ getChatName(event.chat.id) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
    }
  },
  methods: {
    getIcon(type) {
      switch (type) {
        case 'chat': return 'fas fa-comments'
        case 'wiki': return 'fas fa-book'
        default: return 'fas fa-info-circle'
      }
    },
    setEventAsRead(event) {
      this.$session.setEventAsRead(event)
    },
    getProjectName(codx_path) {
      let project = this.$storex.projects.allProjects.find(proj => proj.codx_path === codx_path)
      return project ? project.project_name : 'Unknown Project'
    },
    getChatName(chatId) {
      let chat = this.$storex.projects.allChats.find(ch => ch.id === chatId)
      return chat ? chat.name : 'Unknown Chat'
    }
  }
}
</script>