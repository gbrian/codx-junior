<script setup>
import moment from 'moment'
import ChatPreviewVue from '../wall/ChatPreview.vue'
</script>
<template>
  <div class="flex flex-col h-full">
    <div class="flex items-center gap-2 px-3 py-2 border-b border-base-300">
      <i class="fa-solid fa-clock-rotate-left text-base-content/60"></i>
      <span class="font-semibold text-sm">History</span>
      <span class="badge badge-sm badge-neutral ml-auto">{{ allChats?.length || 0 }}</span>
    </div>
    <div class="grow overflow-auto">
      <div v-if="loading" class="flex flex-col gap-2 p-2">
        <div v-for="i in 5" :key="i" class="h-16 rounded-lg bg-base-200 animate-pulse"></div>
      </div>
      <div v-else-if="!allChats?.length" class="flex flex-col items-center justify-center h-32 text-base-content/40 text-sm gap-2">
        <i class="fa-solid fa-inbox text-2xl"></i>
        <span>No recent activity</span>
      </div>
      <div v-else class="flex flex-col gap-1 p-1">
        <div
          v-for="chat in allChats"
          :key="chat.id"
          class="cursor-pointer rounded-lg hover:bg-base-200 transition-colors"
          @click.stop="openChat(chat)"
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
      allProjects: null,
      loading: false
    }
  },
  created() {
    this.buildHistory()
  },
  watch: {
    projects: {
      deep: true,
      handler(newVal, oldVal) {
        const newIds = (newVal || []).map(p => p.project_id).sort().join()
        const oldIds = (oldVal || []).map(p => p.project_id).sort().join()
        if (newIds !== oldIds) {
          this.buildHistory()
        }
      }
    }
  },
  computed: {
    allChats() {
      if (!this.allProjects) return []
      return this.allProjects
        .reduce((acc, p) => acc.concat(p.recentChats || []), [])
        .sort((a, b) => (a.updated_at > b.updated_at ? -1 : 1))
    }
  },
  methods: {
    async buildHistory() {
      if (!this.projects?.length) return
      this.loading = true
      try {
        const loaded = await Promise.all(
          this.projects.map(p => this.loadProjectChats({ ...p }))
        )
        this.allProjects = loaded.filter(p => p.recentChats?.length)
      } finally {
        this.loading = false
      }
    },
    async loadProjectChats(project) {
      try {
        project.loading = true
        const filters = {
          from_date: moment().add(-2, 'months').format('YYYY-MM-DD')
        }
        const chats = await project.$api.chats.list(filters)
        project.recentChats = chats
          .map(c => ({ ...c, project }))
          .sort((a, b) => (a.updated_at > b.updated_at ? -1 : 1))
      } catch (err) {
        console.error(`Error loading chats for project ${project.project_name}:`, err)
        project.recentChats = []
      } finally {
        project.loading = false
      }
      return project
    },
    openChat(chat) {
      const { project_id } = chat.project || {}
      const { id } = chat
      this.$chats.setActiveChat({ id, project_id })
    }
  }
}
</script>