<script setup>
import moment from 'moment'
import ChatPreviewVue from '../wall/ChatPreview.vue'
import ProjectIconVue from '../ProjectIcon.vue'
</script>
<template>
  <div class="flex flex-col">
    <div>
      History
    </div>
    <div class="grow">
      <div class="h-full overflow-auto">
        <div v-for="chat in allChats" :key="chat.id"
          @click.stop="openChat(chat.project, chat)"
        >
          <ChatPreviewVue :project="chat.project" :chat="chat" />
        </div>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  props: ['projects'],
  data() {
    return {
      allProjects: null
    }
  },
  created() {
    this.buildHistory()
  },
  computed: {
    allChats() {
      return this.allProjects?.reduce((acc, p) => acc.concat(p.recentChats), [])
              .sort((a,b) => a.updated_at > b.updated_at ? -1: 1)
    }
  },
  methods: {
    async buildHistory() {
      this.allProjects = await Promise.all(
        this.projects.map(p => this.loadProjectChats({ ...p })))

      this.allProjects = this.allProjects.filter(p => p.recentChats?.length)
                                  .map((p, ix) => ({ ...p, open: ix == 0}))
    },
    async loadProjectChats(project) {
      if (project.recentChats !== undefined) {
        return project
      }
      try {
        project.loading = true
        const filters = {
          from_date: moment().add(-2, 'months').format("YYYY-MM-DD")
        }
        const chats = await project.$api.chats.list(filters)
        
        project.recentChats = chats.map(c => ({ ...c, project}))
      } finally {
        project.loading = false
      }
      return project
    },
    toggleVisibleProject(project) {
      project.open = !project.open
    },
    openChat({ project_id }, { id }) {
      this.$projects.setActiveChat({ id, project_id })
    }
  }
}
</script>