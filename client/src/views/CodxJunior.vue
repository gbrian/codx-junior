<script setup>
import { API } from '../api/api'
import TabViewVue from '@/components/TabView.vue'
import ProjectDropdown from '@/components/ProjectDropdown.vue'
import moment from 'moment'
</script>

<template>
  <div class="codx-junior flex min-h-full relative">
    <div class="absolute top-0 left-0 right-0 bottom-0 z-[100] m-2 rounded-lg bg-base-300/70 flex flex-col justify-center items-center" v-if="$projects.projectLoading">
      <div class="text-2xl">Loading...</div>
    </div>
    <div class="grow flex flex-col relative bg-base-100 gap-2 overflow-auto bg-base-300">
      <div class="p-2 flex gap-2 items-center relative justify-between">
        <ProjectDropdown v-if="!isHelpTabActive" />
        <button class="btn btn-ghost mt-1 md:hidden" @click="showBar = true">
          <i class="fa-solid fa-bars"></i>
        </button>
      </div>
      <div class="text-xs text-info group relative" v-if="lastEvent">
        {{ lastEvent }}
        <div class="bg-base-300/60 flex flex-col gap-2 hidden group-hover:block absolute top-4 w-96 h-20 z-50">
          <div v-for="event in lastEvents" :key="event.ts">
            {{ formatEvent(event)  }}
          </div>
        </div>
      </div>

      <div class="grow p-2 bg-base-100">
        <TabViewVue  :key="projectKey" />
      </div>
    </div>
    <div class="modal modal-open" role="dialog" v-if="showOpenProjectModal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">Open project</h3>
        <input type="text" class="input input-bordered w-full hidden"
          :placeholder="projectPlaceholder" v-model="newProject" />
        <div class="flex gap-2 items-center">
          Existing projects:
          <select class="select" v-model="newProject">
            <option v-for="project in allProjects" :value="project.codx_path" :key="project.project_name">
              {{ project.project_name }}
            </option>
          </select>
        </div>
        <div class="modal-action">
          <button class="btn" @click="onOpenProject(newProject)">Open</button>
          <button class="btn btn-secondary" @click="closeOpenProjectModal">Close</button>
        </div>
      </div>
    </div>    
    <div class="toast toast-end">
      <div class="bg-error text-white overflow-auto rounded-md max-w-96 max-h-60 text-xs"
        v-if="lastError" @click="clearLastError">
        <pre><code>ERROR: {{ lastError }}</code></pre>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      newProject: null,
      codxPath: null,
      showOpenProjectModal: false,
      lastError: null,
      showBar: false
    }
  },
  computed: {
    subProjects() {
      return Array.isArray(this.lastSettings?.sub_projects)
        ? this.lastSettings?.sub_projects
        : this.lastSettings?.sub_projects?.split(",").filter(p => p.trim().length)
    },
    projectName() {
      return this.lastSettings?.project_name
    },
    lastNotification() {
      return this.notifications.length > 0 
        ? this.notifications[this.notifications.length - 1].text 
        : null
    },
    hasNotifications() {
      return !!this.notifications.length
    },
    notifications() {
      return this.$session.notifications || []
    },
    projectKey() {
      return this.$project?.codx_path || 'no-project'
    },
    isHelpTabActive() {
      return this.$ui.activeTab === 'help'
    },
    projectPlaceholder() {
      return this.codxPath || "Project's absolute path"
    },
    lastEvent() {
      const lastEvent = this.$session.events[this.$session.events.length-1]
      if (lastEvent) {
        return this.formatEvent(lastEvent)
      }
      return null
    },
    lastEvents() {
      return this.$session.events?.slice(this.$session.events.length - 3)
    }
  },
  methods: {
    formatEvent(event) {
      const message = event.data.message?.content || ""
      return `[${moment(event.ts).format('HH:mm:ss')}] ${event.event} ${event.data.text || ''}\n${message}`
    },
    async onOpenProject(path) {
      await this.initProject(path)
    },
    async initProject(path) {
      await this.getAllProjects()
      this.openProject(path)
    },
    openProject(path) {
      this.init(path)
    },
    async createNewProject() {
      const { data: { codx_path } } = await API.projects.create(this.getProjectPath())
      this.openProject(codx_path)
    },
    async getAllProjects() {
      await this.$projects.loadAllProjects()
    },
    onShowOpenProjectModal() {
      this.getAllProjects()
      this.showOpenProjectModal = true
    },
    closeOpenProjectModal() {
      this.showOpenProjectModal = false
    },
    async deleteProject() {
      await API.projects.delete()
      this.setActiveTab('home')
    },
    openTask(task) {
      this.setActiveTab('tasks')
      this.$projects.setActiveChat(task)
    },
    removeNotification(notification) {
      this.$session.removeNotification(notification)
    },
    clearLastError() {
      this.$session.lastError = null
    }
  }
}
</script>