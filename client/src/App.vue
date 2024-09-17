<script setup>
import { API } from './api/api'
import HomeViewVue from "./views/HomeView.vue";
import ProjectViewVue from "./views/ProjectView.vue";
import ChatViewVue from "./views/ChatView.vue";
import LiveEditVue from "./views/LiveEdit.vue";
import KnowledgeViewVue from './views/KnowledgeView.vue';
import ProfileViewVue from './views/ProfileView.vue';
import ProjectSettingsVue from "./views/ProjectSettings.vue";
import KanbanVue from './components/kanban/Kanban.vue'
import WikiViewVue from './views/WikiView.vue';
</script>

<template>
  <div class="w-full h-screen max-w-screen flex flex-col bg-base-300 dark relative" data-theme="dark">
    <progress :class="['progress progress-success w-full', liveRequests ? '': 'opacity-0']"></progress>
    <div role="tablist" class="tabs tabs-lifted bg-base-100 rounded-md">
      <a role="tab" :class="['tab flex items-center gap-2', tabIx === 'home' ? tabActive: tabInactive]"
        @click="tabIx = 'home'"
        v-if="validProject"
      >
        <div class="rounded-full font-bold flex gap-2 flex gap-2 items-center">
          <div class="w-4 h-4 bg-cover bg-center rounded-full bg-primay"
              :style="`background-image:url('${lastSettings.project_icon}')`"></div>
          <div class="">
            {{ projectName }}
          </div> 
        </div>
        <div class="dropdown">
          <div tabindex="0" role="button" class="">
            <i class="fa-solid fa-angle-down"></i>
          </div>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
            <li v-for="project in allProjects" :key="project.project_name">
              <a @click="openProject(project.gpteng_path)">
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
      </a>
      <a role="tab" :class="['tab flex items-center gap-2']" v-else>
          <img src="https://codx-dev.meetnav.com/only_icon.png" class="h-7" >
          Welcome
      </a>
      <a role="tab" :class="['tab flex items-center gap-2', tabIx === 'wiki' ? tabActive: tabInactive]"
        @click="tabIx = 'wiki'" v-if="validProject"
        >
          <i class="fa-brands fa-wikipedia-w"></i>
          wiki

        </a>

      <a role="tab" :class="['tab flex items-center gap-2', tabIx === 'tasks' ? tabActive: tabInactive]"
        @click="tabIx = 'tasks'" v-if="validProject"
      >
        <div class="font-medium flex gap-2 items-center">
          <i class="fa-solid fa-clipboard-list"></i>
          Tasks
        </div>
      </a>
      <a role="tab" :class="['tab flex items-center gap-2', tabIx === 'knowledge' ? tabActive: tabInactive]"
        @click="tabIx = 'knowledge'" v-if="validProject"
      >
        <i class="fa-solid fa-book"></i>
        Knowledge
      </a>
      <a role="tab" :class="['tab flex items-center gap-2', tabIx === 'settings' ? tabActive: tabInactive]"
          @click="tabIx = 'settings'" v-if="validProject"
        >
        <i class="fa-solid fa-gear"></i>
      </a>
    </div>
    <div class="grow relative overflow-auto bg-base-100 p-2" v-if="validProject">
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
      </div>
      <KanbanVue v-if="tabIx === 'kanban'" />
      <ChatViewVue v-if="tabIx === 'tasks'" />
      <LiveEditVue v-if="tabIx === 'live'" />
      <KnowledgeViewVue class="p-2 abolsute top-0 left-0 w-full" v-if="tabIx === 'knowledge'" />
      <WikiViewVue class="p-2" v-if="tabIx == 'wiki'"></WikiViewVue>

      <ProjectSettingsVue class="abolsute top-0 left-0 w-full" v-if="tabIx === 'settings'" />
      <ProfileViewVue class="abolsute top-0 left-0 w-full" v-if="tabIx === 'profiles'" />
      <iframe v-if="tabIx === 4" src="/notebooks" class="absolute top-0 left-0 w-full h-full"></iframe>
      <ProjectViewVue class="p-2" v-if="tabIx == 'home'"></ProjectViewVue>
    </div>
    <div class="modal modal-open" role="dialog" v-if="showOpenProjectModal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">Open project</h3>
        <input type="text" class="input input-bordered w-full hidden"
          :placeholder="gptengPath || 'Project\'s absolute path'" v-model="newProject" />
        <div class="flex gap-2 items-center">
          Existing projects:
          <select class="select" v-model="newProject">
            <option v-for="project in allProjects" :value="project.gpteng_path" :key="project.project_name">
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
      tabIx: 'tasks',
      newProject: null,
      gptengPath: null,
      showOpenProjectModal: false,
      liveRequests: null,
      lastSettings: null,
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
        this.lastError = error.response.data.join("\n")
        console.error("API ERROR:", this.lastError);
      });
    await this.init()
    setInterval(() => {
      this.liveRequests = API.liveRequests
      this.lastSettings = API.lastSettings
    }, 200)
    this.getAllProjects()
  },
  computed: {
    validProject () {
      return this.lastSettings?.gpteng_path &&
        this.lastSettings?.project_path
    },
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
    async init () {
      this.gptengPath = this.getProjectPath()
      try {
        await API.settings.read()
      } catch {}
      if (!API.lastSettings ||
          API.lastSettings.gpteng_path !== this.gptengPath ||
          !API.lastSettings?.openai_api_key 
      ) {
        this.tabIx = 2
      }
    },
    getProjectPath () {
      return API.lastSettings?.gpteng_path
    },
    onOpenProject (path) {
      this.openProject(path)
    },
    async openSubProject (projectName) {
      await this.getAllProjects()
      this.openProject(this.allProjects.find(p => p.project_name === projectName).gpteng_path)
    },
    openProject (path) {
      API.init(path)
      this.init()
    },
    async createNewProject () {
      const { data: { gpteng_path } } = await API.project.create(this.getProjectPath())
      this.openProject(gpteng_path)
    },
    async getAllProjects () {
      const { data } = await API.project.list()
      this.allProjects = data
    },
    async onShowOpenProjectModal () {
      this.getAllProjects()
      this.showOpenProjectModal = true
    }
  }
}
</script>