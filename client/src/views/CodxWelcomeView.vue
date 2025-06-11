<script setup>
import IssuePreview from '../components/IssuePreview.vue'
import { GitIssueWizard } from '../wizards/gitIssue.js'
</script>

<template>
  <div class="profile-container flex flex-col h-full py-2">
    <ul class="menu menu-horizontal flex">
      <li @click="selection = 'home'">
        <a>
          <i class="fa-solid fa-house"></i>
          Home
        </a>
      </li>
      <li @click="showProjects">
        <a>
        <i class="fa-solid fa-cubes"></i>
          Projects
          <span class="badge badge-sm">{{ $projects.allProjects.length }}</span>
        </a>
      </li>
      <li @click="$ui.setActiveTab('docs')">
        <a>
        <i class="fa-solid fa-circle-info"></i>
          Docs
        </a>
      </li>
      <div class="grow"></div>
      <li>
        <a href="https://github.com/gbrian/codx-junior" target="_blank">
          <i class="fa-brands fa-github"></i>
          codx-junior
        </a>
      </li>
    </ul>

    <div class="py-10 flex flex-col" v-if="selection === 'home'">
      <div class="px-20 flex flex-col">
        <h1 class="text-center text-3xl font-bold flex gap-2 justify-center items-center">
          Hi there!
        </h1>
        <p class="pb-6 text-center text-2xl">
          codx-junior is here to maintain your open source projects
        </p>

        <div class="text-3xl py-2">Meet the team</div>
        <div class="flex justify-between items-start">
          <div class="chat chat-start">
            <div class="chat-image avatar">
              <div class="w-10 rounded-full">
                <img class="h-8" src="https://cdn-icons-png.flaticon.com/512/3940/3940410.png" />
              </div>
            </div>
            <div class="chat-bubble">
              Hi, this is <span class="font-bold">@wiki</span>.<br/>
              I'll write updated and clear documentation for you.
            </div>
            <div class="chat-footer opacity-50">Keep your docs always up-to-date with @biblio and auto-wiki</div>
          </div>

          <div class="chat chat-end">
            <div class="chat-image avatar">
              <div class="w-10 rounded-full">
                <img class="h-8" src="https://cdn-icons-png.flaticon.com/512/2607/2607079.png" />
              </div>
            </div>
            <div class="chat-bubble">
              Hello, this is <span class="font-bold">@analyst</span>.<br/>
              I'll keep your Kanban tasks tiddy, create subtasks, and assign users to them.
            </div>
            <div class="chat-footer opacity-50">Keep your docs always up-to-date with @biblio and auto-wiki</div>
          </div>
        </div>
        <div class="flex justify-center items-start mt-2">
          <div class="chat chat-start">
            <div class="chat-image avatar">
              <div class="w-10 rounded-full">
                <img class="h-8" src="data:image/png;base64,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" />
              </div>
            </div>
            <div class="chat-bubble">
              <span class="font-bold">@software_developer</span> here!
              <br/>
              I'll can write high quality code non-stop
            </div>
            <div class="chat-footer opacity-50">Keep your docs always up-to-date with @biblio and auto-wiki</div>
          </div>
        </div>
      </div>




      <div class="mt-10 px-32 flex flex-col gap-2 justify-center align-center">
          <div class="chat chat-start">
            <div class="chat-image avatar">
              <div class="w-10 rounded-full">
                <img class="h-8" src="/only_icon.png" />
              </div>
            </div>
            <div class="chat-bubble w-full">
              And this is <span class="font-bold codx-primary">@codx-junior</span>,
              <br/>
              Let's start working together!
              <div class="my-2 flex flex-col gap-2 rounded-md">
                <div class="group input input-bordered flex gap-1 items-center"
                  :class="newProjectPath && 'border-warning'"
                >
                  <i class="fa-solid fa-link group-hover:animate-pulse"></i>
                  <input type="text" class="grow"
                    placeholder="Paste a git issue link to start!" 
                    v-model="newProjectPath" />
                  <button class="btn btn-sm"
                    :class="newProjectPath && 'btn-warning border-warning border'"
                    :disabled="newProjectPath?.length < 10" @click="createNewProject(newProjectPath)">
                    Go
                  </button>
                </div>
              </div>  
              <div class="chat-footer opacity-50">
                Paste a git issue link to start!
              </div>
            </div>
          </div>

        
      </div>

      <div class="mt-8 px-10 flex flex-col justify-center">
        <div class="text-center text-xl py-2 click" @click="showIssues = !showIssues">
          Or take one from the os community list 
          <span v-if="showIssues">👇</span>
          <span v-else>👉</span>
        </div>
        <div class="bg-base-200 p-4 rounded-md" v-if="showIssues">
          <div class="text-center text-xs py-2">
            codx-junior won't be possible without all those great oss we use 
            join codx-junior and let's show them some ❤️ fixing some of their issues! 
            <span>🍉</span>
          </div>
          <div class="grid grid-cols-4 gap-2 py-2">

            <div class="badge badge-info badge-outline badge-sm click" @click="openLink('https://github.com/vuejs/vue')">vue:3.2.47</div>

            <div class="badge badge-info badge-outline badge-sm click" @click="openLink('https://github.com/tailwindlabs/tailwindcss')">tailwindcss:3.2.0</div>

            <div class="badge badge-info badge-outline badge-sm click" @click="openLink('https://github.com/axios/axios')">axios:1.3.5</div>

            <div class="badge badge-info badge-outline badge-sm click" @click="openLink('https://github.com/vitejs/vite')">vite:4.0.0</div>

            <div class="badge badge-warning badge-outline badge-sm click" @click="openLink('https://github.com/pallets/flask')">flask:2.3.5</div>

            <div class="badge badge-warning badge-outline badge-sm click" @click="openLink('https://github.com/tiangolo/fastapi')">fastapi:0.95.0</div>

            <div class="badge badge-warning badge-outline badge-sm click" @click="openLink('https://github.com/pytest-dev/pytest')">pytest:6.2.5</div>

            <div class="badge badge-warning badge-outline badge-sm click" @click="openLink('https://github.com/encode/uvicorn')">uvicorn:0.18.3</div>

            <div class="badge badge-warning badge-outline badge-sm click" @click="openLink('https://github.com/milvus-io/pymilvus')">pymilvus:2.1.0</div>

            <div class="badge badge-warning badge-outline badge-sm click" @click="openLink('https://github.com/openai/openai-python')">openai:0.12.0</div>
          </div>
          <div class="flex flex-col gap-4">
            <div class="text-xl">
              Latest issues:
            </div>
            <IssuePreview 
              class="click"
              :class="issue.selected && 'border'" 
              :issue="issue" v-for="issue in issues" :key="issue.hl_title"
              @click.ctrl.stop="openLink(issue.link)"
              @open="openLink(issue.link)"
              @try-me="selectIssue(issue)"
              @click="highlightIssue(issue)"
            />
          </div>
        </div>
      </div>
    </div>    
    

    <div class="flex flex-col gap-4 mt-4" v-if="selection === 'projects'">
      <div class="flex justify-between">
        <div class="text-xl font-bold">Projects</div>
        <div class="flex items-center gap-2 mb-2">
          <input type="text" class="input input-sm input-bordered" placeholder="Filter projects..." v-model="filterQuery" />
          <button class="btn btn-sm" @click="filterQuery = null">
            <i class="fa-solid fa-circle-xmark"></i>
          </button>
        </div>
      </div>
      <div class="grid grid-cols-3 gap-2">
        <div
          v-for="project in filteredProjects"
          :key="project.project_id"
          class="p-4 rounded-md flex flex-col gap-2 bg-base-200 click"
          @click="setActiveProject(project)"
        >
          <p class="text-xs flex gap-1 tooltip" :data-tip="project.project_path"
            ><i class="fa-solid fa-folder"></i>
            <span class="text-nowrap overflow-hidden text-ellipsis">{{ project.project_path }}</span>
          </p>
          <div class="font-bold flex gap-2 items-start">
            <img class="w-6 h-6 rounded-full bg-white" :src="project.project_icon" />
            {{ project.project_name }}
          </div>
          <div class="grow"></div>
        </div>
      </div>
      <div class="">
        <div class="text-xl font-semibold mb-4">Get Started with codx-junior</div>
        <ul class="text-xs flex flex-col gap-2 ml-4">
          <li>
            <i class="fa-brands fa-square-git"></i><span class="font-bold"> Clone your repo</span>
            <div class="ml-6 text-xs">Copy paste the repo url and press "Clone"</div>
          </li>
          <li>
            <i class="fa-solid fa-gear"></i><span class="font-bold"> Set your settings</span>
            <div class="ml-6 text-xs">
              Review important settings like
              <span class="text-warning underline click" @click="$ui.setActiveTab('global-settings')"
                >AI provider settings</span
              >
              and
              <span class="underline click" @click="$ui.setActiveTab('settings')">Project settings</span>
            </div>
          </li>
          <li>
            <i class="fa-solid fa-book"></i> <span class="font-bold"> Review knowledge settings and profiles (optional)</span>
            <div class="ml-6 text-xs">
              Knowledge allows codx-junior to learn from the code base
              <span class="text-secondary underline click" @click="$ui.setActiveTab('knowledge')"> check it here</span>
              and profiles improves codx-junior performance...
              <span class="text-info underline click" @click="$ui.setActiveTab('profiles')"> check it at profiles</span>
            </div>
          </li>
        </ul>
        <div class="text-xl font-semibold my-2">Whats's next?</div>
        <div class="flex gap-2">
          <button
            class="btn btn-outline flex gap-2 tooltip tooltip-bottom"
            data-tip="Solve issues chatting with codx!"
            @click="$ui.setActiveTab('tasks')"
          >
            <i class="fa-solid fa-list-check"></i>
            Tasks
          </button>
          <button
            class="btn btn-outline flex gap-2 tooltip tooltip-bottom"
            :data-tip="'Assisted coding with @codx' + ': ...'"
            @click="$ui.setShowCoder(true)"
          >
            <i class="fa-solid fa-code"></i>
            AI Coding
          </button>
          <button
            class="btn btn-outline flex gap-2 tooltip tooltip-bottom"
            data-tip="Preview your changes"
            @click="$ui.setActiveTab('profiles')"
          >
            <i class="fa-solid fa-circle-user"></i>
            Profiles
          </button>
        </div>
      </div>
      <div class="text-xs">
        <div class="mt-2">Happy coding 🤩</div>
        And don't forget to <span class="text-yellow-600"><i class="fa-solid fa-star"></i></span> us
        <a href="https://github.com/gbrian/codx-junior" target="_blank" class="text-blue-500 underline">github.com/gbrian/codx-junior</a>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      selection: 'home',
      newProjectPath: "",
      filterQuery: "",
      issues: [],
      showIssues: false
    }
  },
  async created () {
    this.issues = await this.$storex.api.projects.helpWantedIssues()
    this.issues = this.issues.filter(i => i.hl_text)
                    .map(issue => ({ ...issue, link: `https://github.com/${issue.repo.repository.owner_login}/${issue.repo.repository.name}/issues/${issue.number}`}))
                    .sort((a, b) => a.created > b.created ? -1 : 1)
  },
  computed: {
    filteredProjects() {
      return this.$projects.allProjects.filter(project => {
        return !this.filterQuery || (
          project.project_name.toLowerCase().includes(this.filterQuery.toLowerCase()) ||
          project.project_path.toLowerCase().includes(this.filterQuery.toLowerCase())
        )
      })
    }
  },
  methods: {
    async createNewProject(newProjectPath) {
      if (!newProjectPath) {
        return
      }
      await this.$service.project.cloneProject(newProjectPath)
      if (newProjectPath.includes("github.com") &&
        newProjectPath.includes("/issues/")) {
        this.$projects.addWizard(new GitIssueWizard(this.$service, newProjectPath))
      } else {
        this.$ui.setActiveTab('tasks')
      }
      this.newProjectPath = null
    },
    setActiveProject(project) {
      this.$projects.setActiveProject(project)
      this.$ui.setActiveTab("tasks")
    },
    openLink(link) {
      window.open(link, '_blank')
    },
    selectIssue(issue) {
      this.createNewProject(issue.link)
    },
    highlightIssue(issue) {
      this.issues.forEach(i => { i.selected = false })
      issue.selected = true
    },
    async showProjects() {
      await this.$projects.loadAllProjects()
      this.selection = 'projects'
    }
  }
}
</script>