<script setup>
import IssuePreview from '../components/IssuePreview.vue'
import ProjectCard from '../components/project/ProjectCard.vue'

import { GitIssueWizard } from '../wizards/gitIssue.js'
import Wall from '../components/wall/Wall.vue'
import ProjectOverview from '@/components/project/ProjectOverview.vue'
import NewProject from '@/components/project/NewProject.vue'
</script>

<template>
  <div class="flex flex-col h-full">
    <ul class="menu menu-horizontal flex items-center m-0 p-0 mb-2">
      <li @click="selection = 'home'" v-if="$users.isProjectAdmin">
        <a>
          <span class="hidden md:block">
            <i class="fa-solid fa-house"></i>
          </span>
          Home
        </a>
      </li>
      <li @click="showProjects">
        <a>
          <span class="hidden md:block">
            <i class="fa-solid fa-cubes"></i>
          </span>
          Projects
          <span class="badge badge-sm">{{ $projects.allProjects.length }}</span>
        </a>
      </li>
      <li @click="addNewProject">
        <a class="btn btn-xs btn-outline btn-primary">
          <span class="hidden md:block">
            <i class="fa-solid fa-plus"></i>
          </span>
          New Project
        </a>
      </li>
      <div class="grow"></div>
      <li>
        <a href="https://github.com/gbrian/codx-junior" target="_blank">
          <i class="fa-brands fa-github"></i>
          <span class="hidden md:block">codx-junior</span>
        </a>
      </li>
    </ul>
    <div class="grow overflow-auto">
      <Wall class="" v-if="selection === 'home'"></Wall>
      
      <NewProject class="md:p-6" v-if="selection === 'new_project'"/>
      <ProjectOverview v-if="selection === 'projects'" />

    </div>  
  </div>
</template>

<script>
export default {
  data() {
    return {
      selection: 'home',
      filterQuery: "",
      issues: [],
      showIssues: false
    }
  },
  async created () {
    if (!this.$users.isProjectAdmin) {
      this.selection = 'projects'
    }
    this.issues = await this.$storex.api.projects.helpWantedIssues()
    this.issues = this.issues.filter(i => i.hl_text)
                    .map(issue => ({ ...issue, link: `https://github.com/${issue.repo.repository.owner_login}/${issue.repo.repository.name}/issues/${issue.number}`}))
                    .sort((a, b) => a.created > b.created ? -1 : 1)
  },
  computed: {
    filteredProjects() {
      const projects = this.$projects.allProjects
        .sort((a, b) => Object.keys(a.metrics?.heatmap || {}).length >
                        Object.keys(b.metrics?.heatmap || {}).length ? -1 : 1 
        )
      return this.filterQuery ? projects.filter(project =>
          project.project_name.toLowerCase().includes(this.filterQuery.toLowerCase()) ||
          project.project_path.toLowerCase().includes(this.filterQuery.toLowerCase())) :
          projects.slice(0, 6)
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
      this.selection = 'projects'
    },
    addNewProject() {
      this.selection = 'new_project'
    }
  }
}
</script>