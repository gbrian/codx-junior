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
        <div class="" v-for="project, ix in projects" :key="project.project_id">
          <div :tabindex="ix" class=""
            @click="toggleVisibleProject(project)">
            <div class="click flex gap-2 items-center hover:bg-base-100 rounded-md px-1">
              <i class="fa-solid fa-chevron-down" v-if="project.open"></i>
              <i class="fa-solid fa-chevron-up" v-else></i>
              <ProjectIconVue inline="true" width="w-6" :project="project" />
              {{  project.recentChats?.length }}
            </div>
            <div class="ml-6" v-if="project.open">
              <progress class="progress w-fll" v-if="project.loading"></progress>
              <div v-if="project.recentChats?.length == 0"> No results</div>
              <div v-for="chat in project.recentChats" :key="chat.id"
                @click.stop="openChat(project, chat)"
              >
                <ChatPreviewVue :chat="chat" />
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  data() {
    return {
      projects: null
    }
  },
  created() {
    this.buildHistory()
  },
  methods: {
    async buildHistory() {
      this.projects = await Promise.all(
                        [this.$project, ...this.$projects.childProjects]
                        .map(p => this.loadProjectChats({ ...p })))

      this.projects = this.projects.filter(p => p.recentChats?.length)
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
        
        project.recentChats = chats.sort((a,b) => a.updated_at > b.updated_at ? -1: 1)
          .slice(0, 10)
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