<script setup>
import ChatPreview from './ChatPreview.vue';
</script>

<template>
  <div class="w-full h-full relative">
    <div class="absolute top-0 left-0 right-0 bottom-0 overflow-auto">
      <div class="text-2xl">
        Recent activity <span v-if="project">: {{ project.project_name }}</span>
      </div>
      <div class="alert" v-if="lastMessages.length === 0">
        No recent activity
      </div>
      <div class="grid grid-cols-1 @5xl:grid-cols-2 grid-flow-rows gap-2">
        <div class="my-2 click group"
          v-for="chat in lastMessages" :key="chat.doc_id"
          @click="setActiveChat(chat)">
            <ChatPreview
              :project="chat.project"
              :chat="chat"
              />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['project', 'board'],
  data() {
    return {}
  },
  computed: {
    projects() {
      const { allProjects } = this.$projects 
      if (this.project) {
        const { project_path } = this.project
        const childProjects = allProjects
          .filter(p => p.abs_project_path !== project_path && p.abs_project_path.startsWith(project_path))
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
      if (chat.project.project_id !== this.$project?.project_id) {
        await this.$projects.setActiveProject(chat.project)
      }
      this.$chats.setActiveChat(chat)
      this.$ui.setActiveTab('tasks')
    }
  }
}
</script>
