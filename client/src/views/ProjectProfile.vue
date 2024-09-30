<script setup>
import { API } from '../api/api';
</script>

<template>
  <div class="profile-container flex flex-col items-center p-4 h-full">
    <div v-if="settings.project_name">
      <img :src="projectIcon" alt="Project Icon" class="rounded-full w-36 h-36" />
      <h1 class="text-2xl font-bold mt-4">{{ projectName }}</h1>
      <p class="text-lg mt-2">{{ projectDescription }}</p>
      <button class="btn btn-primary mt-4" @click="$emit('settings')">
        Edit Project Settings
      </button>
    </div>
    <div v-else>
      
    </div>
    
    <div class="projects-list mt-8 w-full flex flex-col gap-2">
      <h2 class="text-xl font-bold mb-4">Projects</h2>
      <div class="grid grid-cols-4 gap-3">
        <div v-for="project in allProjects" :key="project.gpteng_path" class="mb-2" @click="setProject(project)">
          <div class="flex items-center gap-4 p-2 border rounded-md click">
            <img :src="project.project_icon" alt="Project Icon" class="w-12 h-12 rounded-full" />
            <div>
              <h3 class="text-lg font-bold">{{ project.project_name }}</h3>
              <p>{{ project.project_description }}</p>
            </div>
          </div>
        </div>
      </div>
      <div class="input input-bordered flex gap-1 items-center">
        <input type="text" class="grow" v-model="newProjectPath" placeholder="/project/path">
        <button class="btn btn-sm" @click="createNewProject">
          New
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
      newProjectPath: null
    };
  },
  mounted () {
    this.load()
  },
  computed: {
    allProjects () {
      return this.settings.projects
    },
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
      if (!API.lastSettings && projects.length) {
        await API.init(projects[0].gpteng_path)
      } 
      this.settings = API.lastSettings || {}
    },
    async setProject(project) {
      await API.init(project.gpteng_path)
      this.settings = API.lastSettings
    },
    async createNewProject () {
      await API.projects.new(this.newProjectPath)
      this.newProjectPath = null
      this.load()
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
</style>
