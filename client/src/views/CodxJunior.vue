<script setup>
import { API } from '../api/api'
import KnowledgeViewVue from './KnowledgeView.vue';
import ProfileViewVue from './ProfileView.vue';
import ProjectSettingsVue from "./ProjectSettings.vue";
import KanbanVue from '../components/kanban/Kanban.vue'
import WikiViewVue from './WikiView.vue';
import GlobalSettingsVue from './GlobalSettings.vue';
import ProjectProfileVue from './ProjectProfile.vue';
import NavigationBar from '../components/NavigationBar.vue'

</script>

<template>
  <div class="flex relative">
    <progress :class="['absolute top-0 left-0 right-0 z-50 progress w-full', $session.apiCalls ? 'opacity-50': 'opacity-0']"></progress>      
    <NavigationBar class="shrink-0"
      :tabIx="tabIx"
      @tabIx="tabIx"
      @set-active="setActiveTab"
      @toggle-coder="$emit('toggle-coder')"
    />
    <div class="grow flex flex-col relative bg-base-100 px-2 pt-2 overflow-auto">
      <KanbanVue class="overflow-auto" v-if="tabIx === 'tasks'" />
      <KnowledgeViewVue class="" v-if="tabIx === 'knowledge'" />
      <WikiViewVue class="" v-if="tabIx == 'wiki'"></WikiViewVue>

      <ProjectSettingsVue class="absolute top-0 left-0 w-full" 
        @delete="deleteProject"
        v-if="tabIx === 'settings'" />
      <GlobalSettingsVue class="absolute top-0 left-0 w-full " v-if="tabIx === 'global-settings'" />
      <ProfileViewVue class="absolute top-0 left-0 w-full" v-if="tabIx === 'profiles'" />
      <iframe v-if="tabIx === 4" src="/notebooks" class="absolute top-0 left-0 w-full h-full"></iframe>
      <ProjectProfileVue class=" absolute top-0 left-0 w-full" v-if="tabIx == 'home'" @settings="setActiveTab('settings')"></ProjectProfileVue>
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
      tabIx: 'home',
      newProject: null,
      codxPath: null,
      showOpenProjectModal: false,
      tabActive: 'text-info bg-base-100',
      tabInactive: 'text-warning bg-base-300 opacity-50 hover:opacity-100',
      lastError: null
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
    }
  },
  watch: {
    tabIx (newValue) {
      if (newValue === 'home') {
        this.getAllProjects()
      }
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
      this.openProject(this.$project.allProjects.find(p => p.project_name === projectName).codx_path)
    },
    openProject (path) {
      this.init(path)
    },
    async createNewProject () {
      const { data: { codx_path } } = await API.project.create(this.getProjectPath())
      this.openProject(codx_path)
    },
    async getAllProjects () {
      await this.$project.init()
    },
    async onShowOpenProjectModal () {
      this.getAllProjects()
      this.showOpenProjectModal = true
    },
    async deleteProject () {
      await API.project.delete()
      this.setActiveTab('home')
    },
    setActiveTab(tabIx) {
      console.log("Set active", tabIx)
      this.tabIx = tabIx
    }
  }
}
</script>