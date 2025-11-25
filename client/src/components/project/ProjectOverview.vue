<script setup>
import ProjectCard from './ProjectCard.vue'
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex justify-between">
      <div class="text-xl font-bold">
        <span v-if="filterQuery">Find projects: '{{ filterQuery }}'</span>
        <span v-else>Top projects</span>
      </div>
      <div class="flex items-center gap-2 mb-2">
        <input type="text" class="input input-sm input-bordered" placeholder="Filter projects..." v-model="filterQuery" />
        <button class="btn btn-sm" @click="filterQuery = null">
          <i class="fa-solid fa-circle-xmark"></i>
        </button>
        <button class="btn btn-sm" @click="$projects.loadAllProjects(true)">
          <i class="fa-solid fa-arrows-rotate"></i>
        </button>
      </div>
    </div>
    <div class="grid grid-cols-2 md:grid-cols-2 gap-2">
      <ProjectCard
        v-for="project in filteredProjects"
        :key="project.project_id"
        :project="project"
        @click="setActiveProject(project)"
      />
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      filterQuery: null
    }
  },
  computed: {
    filteredProjects() {
      const projects = this.$projects.allProjects.sort((a, b) => 
        Object.keys(a.metrics?.heatmap || {}).length > Object.keys(b.metrics?.heatmap || {}).length ? -1 : 1 
      )
      return this.filterQuery ? projects.filter(project =>
        project.project_name.toLowerCase().includes(this.filterQuery.toLowerCase()) ||
        project.project_path.toLowerCase().includes(this.filterQuery.toLowerCase())
      ) : projects.slice(0, 6)
    }
  },
  methods: {
    setActiveProject(project) {
      this.$projects.setActiveProject(project)
      this.$ui.setActiveTab("tasks")
    }
  }
}
</script>