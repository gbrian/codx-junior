<script setup>
import { API } from '../api/api'
import TabViewVue from '@/components/TabView.vue'
import ProjectDropdown from '@/components/ProjectDropdown.vue'
</script>

<template>
  <div class="codx-junior flex min-h-full">
    <div class="grow flex flex-col relative bg-base-100 gap-2 overflow-auto bg-base-300">
      <div class="p-2 flex gap-2 items-center relative justify-between">
        <ProjectDropdown v-if="!isHelpTabActive" />
        <div class="badge flex gap-2" v-if="!isHelpTabActive">
          <span class="text-warning"><i class="fa-solid fa-brain"></i></span>
              {{ $projects.aiModel }} / 
              <span class="text-info"><i class="fa-solid fa-file"></i></span>
              {{ $projects.embeddingsModel }}
          </div>
        <button class="btn btn-ghost mt-1 md:hidden" @click="showBar = true">
          <i class="fa-solid fa-bars"></i>
        </button>
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
    }
  },
  methods: {
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
      const { data: { codx_path } } = await API.project.create(this.getProjectPath())
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
      await API.project.delete()
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