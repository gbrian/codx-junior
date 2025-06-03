<script setup>
import IssuePreview from '../components/IssuePreview.vue'
import { GitIssueWizard } from '../wizards/gitIssue.js'
</script>

<template>
  <div class="profile-container flex flex-col h-full py-2">
    <ul class="menu menu-horizontal">
      <li @click="selection = 'home'">
        <a>
          <i class="fa-solid fa-house"></i>
          Home
        </a>
      </li>
      <li @click="selection = 'projects'">
        <a>
          Projects
          <span class="badge badge-sm">{{ $projects.allProjects.length }}</span>
        </a>
      </li>
    </ul>

    <div class="py-10 flex flex-col" v-if="selection === 'home'">
      <div class="px-20 flex flex-col">
        <h1 class="text-center text-3xl font-bold flex gap-2 justify-center items-center">
          <img class="h-14" src="/only_icon.png" />
          Welcome
        </h1>
        <p class="py-6 text-center">
          I'm codx-junior and I'm here to help you maintining 
          your open source projects.
        </p>
        <div class="flex gap-2 items-center mb-2">
          <div class="badge font-bold badge-primary hover:badge-ghost click">
            Try me!
          </div>
           Give me an issue and I'll help you fixing it!
        </div>
        <div class="flex flex-col gap-2 rounded-md">
          <div class="group input input-bordered flex gap-1 items-center">
            <i class="fa-solid fa-link group-hover:animate-pulse"></i>
            <input type="text" class="grow"
              placeholder="Paste a git issue link to start!" 
              v-model="newProjectPath" />
            <button class="btn btn-sm" :disabled="newProjectPath?.length < 10" @click="createNewProject">
              Go
            </button>
          </div>
          <p class="text-xs italic text-center">
            Paste a git issue link to start!
          </p>
        </div>    
      </div>
      <div class="px-10 flex flex-col justify-center">
        <div class="text-center text-2xl py-2">Trending issues from oss community you may help with!</div>
        <div class="flex flex-col gap-4">
          <IssuePreview 
            class="click" 
            :issue="issue" v-for="issue in issues" :key="issue.hl_title"
            @click.ctrl.stop="openLink(issue.link)"
            @click="newProjectPath = issue.link"
          />
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
    }
  },
  async created () {
    this.issues = await this.$storex.api.projects.helpWantedIssues()
    this.issues = this.issues.filter(i => i.hl_text)
                    .map(issue => ({ ...issue, link: `https://github.com/${issue.repo.repository.owner_login}/${issue.repo.repository.name}/issues/${issue.number}`}))
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
    async createNewProject() {
      if (!this.newProjectPath) {
        return
      }
      if (this.newProjectPath.includes("github.com") &&
        this.newProjectPath.includes("/issues/")) {
        this.$projects.addWizard(new GitIssueWizard(this.$service, this.newProjectPath))
      } else {
        await this.$projects.createNewProject(this.newProjectPath)
        this.newProjectPath = null
        this.$ui.setActiveTab('tasks')
      }
    },
    setActiveProject(project) {
      this.$projects.setActiveProject(project)
      this.$ui.setActiveTab("tasks")
    },
    openLink(link) {
      window.open(link, '_blank')
    }
  }
}
</script>