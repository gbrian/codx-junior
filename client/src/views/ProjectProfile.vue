<script setup>
import { API } from '../api/api';
</script>

<template>
  <div class="profile-container flex flex-col items-center p-4 h-full">
    <div>
      <div class="hero-section text-center p-4 bg-gray-800 text-white rounded-lg">
        <h1 class="text-3xl font-bold mb-2">Welcome to codx-junior</h1>
        <p class="text-lg">codx-junior is your AI assistant helping full stack developers to maintain their open source projects.</p>
      </div>
    </div>

    <div class="projects-list mt-8 w-full flex flex-col gap-2">
      <h2 class="text-xl font-bold mb-4">Projects</h2>
      <div class="grid grid-cols-4 gap-3">
        <div v-for="project in allProjects" :key="project.gpteng_path" class="mb-2" @click="setProject(project)">
          <div class="flex items-center gap-4 p-2 border rounded-md click h-20 overflow-hidden text-ellipsis">
            <img :src="project.project_icon" alt="Project Icon" class="w-8 h-8 rounded-full" />
            <div>
              <h3 class="text-lg font-bold">{{ project.project_name }}</h3>
              <p>{{ project.project_description }}</p>
            </div>
          </div>
        </div>
      </div>
      <div class="text-xl">
        Create new project
      </div>
      <p class="text-sm">Copy the absolute project's path to create a new project</p>
      <div class="input input-bordered flex gap-1 items-center">
        <input type="text" class="grow" v-model="newProjectPath" placeholder="/project/path">
        <button class="btn btn-sm" @click="createNewProject">
          <i class="fa-solid fa-plus"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      settings: API.lastSettings || {},
      newProjectPath: null,
      allProjects: []
    };
  },
  mounted () {
    this.load()
  },
  computed: {
    projectName() {
      return this.settings.project_name;
    },
    projectIcon() {
      return this.settings.project_icon;
    },
    projectDescription() {
      return this.settings.project_description;
    }
  },
  methods: {
    async load () {
      const { data: projects } = await API.project.list()
      this.allProjects = projects
      if (!API.lastSettings && projects.length) {
        await API.init(projects[0].gpteng_path)
      } 
      this.settings =  API.lastSettings || {}
    },
    async setProject(project) {
      await API.init(project.gpteng_path)
      this.settings = API.lastSettings
    },
    async createNewProject () {
      await API.project.create(this.newProjectPath)
      await this.load()
      const project = this.allProjects.find(p => p.project_path === this.newProjectPath)
      this.newProjectPath = null
      this.$emit('settings')
    }
  }
};
</script>

<style scoped>
.profile-container {
  background: #1a202c; /* Dark background */
  color: white; /* White text */
  border-radius: 8px; /* Rounded corners */
  padding: 16px; /* Padding around the content */
}
.projects-list ul {
  list-style-type: none; /* Remove default list styling */
  padding: 0;
}
.projects-list li {
  margin-bottom: 16px; /* Space between list items */
}
.hero-section {
  background-color: #2d3748; /* Slightly lighter dark background */
  padding: 24px; /* More padding for hero section */
  border-radius: 8px; /* Rounded corners for hero section */
}
</style>