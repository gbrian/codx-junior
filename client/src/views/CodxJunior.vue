<script setup>
import { API } from '../api/api'
import NavigationBar from '../components/NavigationBar.vue'
import TabNavigationVue from '../components/TabNavigation.vue'
import TabViewVue from '@/components/TabView.vue'
import ProjectDropdown from '@/components/ProjectDropdown.vue'
</script>

<template>
  <div class="codx-junior flex min-h-full">
    <div class="grow flex flex-col relative bg-base-100 gap-2 px-2 pt-2 overflow-auto">
      <div class="flex gap-2 items-center relative justify-between">
        
        <ProjectDropdown v-if="!compactView && $ui.activeTab !== 'help'" />
        <button class="btn btn-ghost mt-1 md:hidden" @click="showBar = true">
          <i class="fa-solid fa-bars"></i>
        </button>

        <div class="dropdown dropdown-end">
          <div tabindex="0" role="button" class="btn btn-circle btn-sm m-1"
            :class="$session.notifications?.length && 'btn-warning'"
          >
            <i class="fa-solid fa-bell"></i>
          </div>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
            <li class="mb-2"
              @click="$session.removeNotification(n)"
              v-for="n in $session.notifications" :key="n.id">
              <a class="bg-secondary text-secondary-content">{{ n.text }}</a>
            </li>
          </ul>
        </div>
      </div>
      <TabNavigationVue v-if="false && !compactView" />
      <TabViewVue :key="$project?.codx_path || 'no-project'" />
    </div>
    <div class="modal modal-open" role="dialog" v-if="showOpenProjectModal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">Open project</h3>
        <input type="text" class="input input-bordered w-full hidden"
          :placeholder="codxPath || 'Project\'s absolute path'" v-model="newProject" />
        <div class="flex ga items-center">
          Existing projects:
          <select class="select" v-model="newProject">
            <option v-for="project in allProjects" :value="project.codx_path" :key="project.project_name">
              {{ project.project_name }}
            </option>
          </select>
        </div>
        <div class="modal-action">
          <label for="my_modal_6" class="btn" @click="onOpenProject(newProject)">
            Open
          </label>
          <label class="modal-backdrop" for="my_modal_6">Close</label>
        </div>
      </div>
    </div>
    <div class="toast toast-end">
      <div class="bg-error text-white overflow-auto rounded-md  max-w-96 max-h-60 text-xs"
        v-if="lastError" @click="$session.lastError = null">
        <pre><code>ERROR: {{ $session.lastError }}</code></pre>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  data () {
    return {
      newProject: null,
      codxPath: null,
      showOpenProjectModal: false,
      tabActive: 'text-info bg-base-100',
      tabInactive: 'text-warning bg-base-300 opacity-50 hover:opacity-100',
      lastError: null,
      showBar: false
    }
  },
  async created () {
  },
  computed: {
    subProjects () {
      if (!Array.isArray(this.lastSettings?.sub_projects)) {
        return this.lastSettings?.sub_projects?.split(",")
                  .filter(p => p.trim().length)
      }
      return this.lastSettings?.sub_projects
    },
    projectName () {
      return this.lastSettings?.project_name
    },
    compactView () {
      return !!this.$storex.projects.activeChat && this.$ui.tabIx == "tasks"
    }
  },
  methods: {
    async init (path) {
    },
    getProjectPath () {
      return API.lastSettings?.codx_path
    },
    onOpenProject (path) {
      this.openProject(path)
    },
    async openSubProject (projectName) {
      await this.getAllProjects()
      this.openProject(this.$projects.allProjects.find(p => p.project_name === projectName).codx_path)
    },
    openProject (path) {
      this.init(path)
    },
    async createNewProject () {
      const { data: { codx_path } } = await API.project.create(this.getProjectPath())
      this.openProject(codx_path)
    },
    async getAllProjects () {
      await this.$projects.loadAllProjects()
    },
    async onShowOpenProjectModal () {
      this.getAllProjects()
      this.showOpenProjectModal = true
    },
    async deleteProject () {
      await API.project.delete()
      this.setActiveTab('home')
    },
    openTask(task) {
      this.setActiveTab('tasks')
      this.$projects.setActiveChat(task)
    }
  }
}
</script>