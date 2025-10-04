<script setup>
import ChatEntry from '../ChatEntry.vue'
import ProjectIcon from '../ProjectIcon.vue';
</script>

<template>
  <div class="w-full">
    <div class="text-2xl">Recent activity</div>
    <div class="border border-slate-800 hover:border-slate-600 shadow-md rounded-lg my-2 click"
      v-for="chat in lastMessages" :key="chat.doc_id">
      <div class="flex gap-2 items-center bg-base-100 px-2 rounded-t-lg"
        @click="setActiveChat(chat)"
      >
        <ProjectIcon inline="true" :project="chat.project" />
        <div class="divider"></div>
        {{ chat.name }}
      </div>
      <ChatEntry :menu-less="true" :message="chat.messages[0]" :chat="chat" />
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {}
  },
  computed: {
    lastMessages() {
      const { allProjects } = this.$projects 
      return allProjects
                .map(project => 
                  (project.metrics?.wall || []).map(chat => ({ ...chat, project })))
                .reduce((a, b) => a.concat(b), [])
                .sort((a, b) => a.messages[0].updated_at > b.messages[0].updated_at ? -1:1)
                .map(chat => {
                  chat.messages[0].collapse = true
                  return chat
                })
    }
  },
  methods: {
    async setActiveChat(chat) {
      if (chat.project.project_id !== this.$project.project_id) {
        await this.$projects.setActiveProject(chat.project)
      }
      this.$projects.setActiveChat(chat)
      this.$ui.setActiveTab('tasks')
    }
  }
}
</script>
