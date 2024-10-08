<script setup>
import { API } from '../api/api'
import ChatViewVue from "./ChatView.vue";
import LiveEditVue from "./LiveEdit.vue";
import KnowledgeViewVue from './KnowledgeView.vue';
import ProfileViewVue from './ProfileView.vue';
import ProjectSettingsVue from "./ProjectSettings.vue";
import KanbanVue from '../components/kanban/Kanban.vue'
import WikiViewVue from './WikiView.vue';
import GlobalSettingsVue from './GlobalSettings.vue';
import ProjectProfileVue from './ProjectProfile.vue';
</script>

<template>
  <div class="flex flex-col bg-base-300 dark relative" data-theme="dark">
    <progress :class="['progress progress-success w-full', liveRequests ? '': 'opacity-0']"></progress>
    <div role="tablist" class="tabs tabs-lifted bg-base-100 rounded-md">
      <a role="tab" :class="['tab', tabIx === 'home' ? tabActive: tabInactive]"
        @click="tabIx = 'home'"
      >
        <div class="btn btn-xs" @click="$emit('toggle-coder')">
          <i class="fa-solid fa-code"></i>
        </div>    
        <div class="flex items-center gap-2" v-if="lastSettings">
          <div class="rounded-full font-bold flex gap-2 flex gap-2 items-center">
            <div class="w-4 h-4 bg-cover bg-center rounded-full bg-primay"
                :style="`background-image:url('${lastSettings.project_icon}')`"></div>
            <div class="">
              {{ projectName }}
            </div> 
          </div>

          <div class="dropdown" @click.stop="">
            <div tabindex="0" role="button" class="btn btn-xs btn-ghost" @click.stop="">
              <i class="fa-solid fa-angle-down"></i>
            </div>
            <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
              <li v-for="project in allProjects" :key="project.project_name">
                <a @click="openProject(project.codx_path)">
                  <div class="rounded-full font-bold flex gap-2 flex gap-2 items-center">
                    <div class="w-4 h-4 bg-cover bg-center rounded-full bg-primay"
                        :style="`background-image:url('${project.project_icon}')`"></div>
                    <div class="">
                      {{ project.project_name }}
                    </div> 
                  </div>
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div v-else>
          codx-junior: welcome
        </div>
      </a>
      <a role="tab" :class="['tab flex items-center gap-2', tabIx === 'tasks' ? tabActive: tabInactive]"
        @click="tabIx = 'tasks'" v-if="lastSettings"
      >
        <div class="font-medium flex gap-2 items-center">
          <i class="fa-solid fa-clipboard-list"></i>
          Tasks
        </div>
      </a>
      <a role="tab" :class="['tab flex items-center gap-2', tabIx === 'knowledge' ? tabActive: tabInactive]"
        @click="tabIx = 'knowledge'" v-if="lastSettings"
      >
        <i class="fa-solid fa-book"></i>
        Knowledge
      </a>
      <a role="tab" :class="['tab flex items-center gap-2', tabIx === 'wiki' ? tabActive: tabInactive]"
        @click="tabIx = 'wiki'" v-if="lastSettings"
        >
          <i class="fa-brands fa-wikipedia-w"></i>
          Documentation
      </a>
      <a role="tab" :class="['tab flex items-center gap-2', tabIx === 'settings' ? tabActive: tabInactive]"
          @click="tabIx = 'settings'" v-if="lastSettings"
        >
        <i class="fa-solid fa-gear"></i>
      </a>
    </div>
    <div role="tablist" class="tabs tabs-lifted bg-base-100 rounded-md mt-2" v-if="['profiles', 'settings'].includes(tabIx)">
      <a role="tab" :class="['tab flex items-center gap-2', tabIx === 'profiles' ? tabActive: tabInactive]"
      @click="tabIx = 'profiles'"
      >
      <i class="fa-solid fa-id-card-clip"></i>
        Profiles
      </a>
      <a role="tab" :class="['tab flex items-center gap-2', tabIx === 'settings' ? tabActive: tabInactive]"
        @click="tabIx = 'settings'"
      >
        <i class="fa-solid fa-sliders"></i>
        Setting
      </a>
      <a role="tab" :class="['tab flex items-center gap-2', tabIx === 'global-settings' ? tabActive: tabInactive]"
        @click="tabIx = 'global-settings'"
      >
        <i class="fa-solid fa-gear"></i>
        Global
      </a>
    </div>
    <div class="grow relative overflow-auto bg-base-100">
      <KanbanVue class="p-2" v-if="tabIx === 'tasks'" />
      <ChatViewVue class="p-2" v-if="tabIx === '___tasks'" />
      <LiveEditVue class="p-2" v-if="tabIx === 'live'" />
      <KnowledgeViewVue class="p-2 abolsute top-0 left-0 w-full" v-if="tabIx === 'knowledge'" />
      <WikiViewVue class="p-2" v-if="tabIx == 'wiki'"></WikiViewVue>

      <ProjectSettingsVue class="abolsute top-0 left-0 w-full" 
        @delete="deleteProject"
        v-if="tabIx === 'settings'" />
      <GlobalSettingsVue class="abolsute top-0 left-0 w-full p-2" v-if="tabIx === 'global-settings'" />
      <ProfileViewVue class="abolsute top-0 left-0 w-full" v-if="tabIx === 'profiles'" />
      <iframe v-if="tabIx === 4" src="/notebooks" class="absolute top-0 left-0 w-full h-full"></iframe>
      <ProjectProfileVue class="p-2 abolsute top-0 left-0 w-full" v-if="tabIx == 'home'" @settings="tabIx = 'settings'"></ProjectProfileVue>
    </div>
    <div class="modal modal-open" role="dialog" v-if="showOpenProjectModal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">Open project</h3>
        <input type="text" class="input input-bordered w-full hidden"
          :placeholder="codxPath || 'Project\'s absolute path'" v-model="newProject" />
        <div class="flex gap-2 items-center">
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
      <div class="bg-error text-white overflow-auto rounded-md p-2 max-w-96 max-h-60 text-xs"
        v-if="lastError" @click="lastError = null">
        <pre><code>ERROR: {{ lastError }}</code></pre>
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
      liveRequests: null,
      lastSettings: {},
      tabActive: 'text-info bg-base-100',
      tabInactive: 'text-warning bg-base-300 opacity-50 hover:opacity-100',
      lastError: null,
      allProjects: null
    }
  },
  async created () {
    API.axiosRequest.interceptors.response.use(
      (response) => response,
      (error) => {
        this.lastError = error.response.data
        console.error("API ERROR:", this.lastError);
      });
    await this.init()
    setInterval(() => {
      this.liveRequests = API.liveRequests
      this.lastSettings = API.lastSettings
    }, 200)
    await this.getAllProjects(); // Fetch all projects
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
      await API.init(path || this.codxPath)
    },
    getProjectPath () {
      return API.lastSettings?.codx_path
    },
    onOpenProject (path) {
      this.openProject(path)
    },
    async openSubProject (projectName) {
      await this.getAllProjects()
      this.openProject(this.allProjects.find(p => p.project_name === projectName).codx_path)
    },
    openProject (path) {
      this.init(path)
    },
    async createNewProject () {
      const { data: { codx_path } } = await API.project.create(this.getProjectPath())
      this.openProject(codx_path)
    },
    async getAllProjects () {
      await API.project.list()
      this.allProjects = API.allProjects
    },
    async onShowOpenProjectModal () {
      this.getAllProjects()
      this.showOpenProjectModal = true
    },
    async deleteProject () {
      await API.project.delete()
      this.tabIx = 'home'
    }
  }
}
</script>