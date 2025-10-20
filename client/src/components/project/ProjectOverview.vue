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
            <span class="text-warning underline click" @click="$ui.setActiveTab('global-settings')">AI provider settings</span>
            and
            <span class="underline click" @click="$ui.setActiveTab('settings')">Project settings</span>
          </div>
        </li>
        <li>
          <i class="fa-solid fa-book"></i> <span class="font-bold"> Review knowledge settings and profiles (optional)</span>
          <div class="ml-6 text-xs">
            Knowledge allows codx-junior to learn from the code base
            <span class="text-secondary underline click" @click="$ui.setActiveTab('knowledge')"> check it here</span>
            and profiles improve codx-junior performance...
            <span class="text-info underline click" @click="$ui.setActiveTab('profiles')"> check it at profiles</span>
          </div>
        </li>
      </ul>
      <div class="text-xl font-semibold my-2">What's next?</div>
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