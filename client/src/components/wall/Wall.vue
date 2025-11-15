<script setup>
import ChatEntry from '../ChatEntry.vue'
import ProjectIcon from '../ProjectIcon.vue';
</script>

<template>
  <div class="w-full">
    <div class="text-2xl">
      Recent activity <span v-if="project">: {{ project.project_name }}</span>
    </div>
    <div class="alert" v-if="lastMessages.length === 0">
      No recent activity
    </div>
    <div class="grid grid-cols-3 grid-flow-rows gap-2">
      <div class="border border-slate-800 hover:border-slate-600 rounded-lg my-2 click group"
        v-for="chat in lastMessages" :key="chat.doc_id"
        @click="setActiveChat(chat)">
        <div class="flex gap-2 items-center bg-slate-800 px-2 rounded-t-lg border-b border-slate-600">
          <ProjectIcon inline="true" :project="chat.project" />
          <div class="divider"></div>
          {{ chat.name }}
        </div>      
        <div class="relative">
          <ChatEntry
            class="rounded-b-lg overflow-auto opacity-60 h-60 group-hover:opacity-100" 
            :menu-less="true" 
            :message="chat.messages[0]" :chat="chat"
            />
          <div class="absolute top-0 left-0 right-0 bottom-0 z-20"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['project'],
  data() {
    return {}
  },
  computed: {
    projects() {
      const { allProjects } = this.$projects 
      if (this.project) {
        const { project_path } = this.project
        const childProjects = allProjects
          .filter(p => p.project_path !== project_path && p.project_path.startsWith(project_path))
        return [this.project, ...childProjects]
      }
      return allProjects
    },
    lastMessages() {
      return this.projects
                .map(project => 
                  (project.metrics?.wall || []).map(chat => ({ ...chat, project })))
                .reduce((a, b) => a.concat(b), [])
                .sort((a, b) => a.messages[0].updated_at > b.messages[0].updated_at ? -1:1)
                .map(chat => {
                  chat.messages[0].collapsed = false
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
