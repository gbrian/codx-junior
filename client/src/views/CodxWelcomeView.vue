<script setup>
import { GitIssueWizard } from '../wizards/gitIssue.js'
import Wall from '../components/wall/Wall.vue'
import ProjectOverview from '@/components/project/ProjectOverview.vue'
</script>

<template>
  <div class="flex flex-col h-full px-2">
    <ProjectOverview />
    <Wall class="" ></Wall>
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