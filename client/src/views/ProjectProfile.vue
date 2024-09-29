<template>
  <div class="profile-container flex flex-col items-center p-4">
    <img :src="projectIcon" alt="Project Icon" class="rounded-full w-36 h-36" />
    <h1 class="text-2xl font-bold mt-4">{{ projectName }}</h1>
    <p class="text-lg mt-2">{{ projectDescription }}</p>
    <button @click="editProjectSettings" class="btn btn-primary mt-4">
      Edit Project Settings
    </button>
    
    <div class="projects-list mt-8 w-full">
      <h2 class="text-xl font-bold mb-4">Projects</h2>
      <ul>
        <li v-for="project in allProjects" :key="project.gpteng_path" class="mb-2">
          <div class="flex items-center gap-4 p-2 border rounded-md">
            <img :src="project.project_icon" alt="Project Icon" class="w-12 h-12 rounded-full" />
            <div>
              <h3 class="text-lg font-bold">{{ project.project_name }}</h3>
              <p>{{ project.project_description }}</p>
            </div>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
import { API } from '../api/api';

export default {
  data() {
    return {
      allProjects: [] // Initialize empty array
    };
  },
  async mounted() {
    await this.getAllProjects(); // Fetch all projects
  },
  methods: {
    async getAllProjects() {
      const { data } = await API.project.list();
      this.allProjects = data; // Update the projects list
    },
    editProjectSettings() {
      // Logic to edit project settings
    }
  },
  computed: {
    projectName() {
      return API.lastSettings.project_name;
    },
    projectIcon() {
      return API.lastSettings.project_icon;
    },
    projectDescription() {
      return API.lastSettings.project_description;
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