<script setup>
import { API } from '../api/api';
</script>

<template>
  <div class="profile-container flex flex-col items-center h-full">
    <div class="px-4 py-2 w-full flex flex-col" v-if="$project.activeProject">
      <h3 class="text-4xl font-bold">{{ $project.activeProject.project_name }}</h3>
      <div class="text-xs">
        {{ $project.activeProject.project_path }}
      </div>
    </div>

    <div class="p-4">
      <div class="hero-section text-center p-4 bg-gray-800 text-white rounded-lg">
        <h1 class="text-3xl font-bold mb-2">Welcome to codx-junior</h1>
        <p class="text-lg">codx-junior is your AI assistant helping full stack developers to maintain their open source projects.</p>
      </div>
    </div>


    <div class="projects-list mt-8 w-full flex flex-col gap-2 p-4">
      <h2 class="text-xl font-bold mb-4">More projects</h2>
      <div class="grid grid-cols-2 gap-3">
        <div v-for="project in otherProjects" :key="project.codx_path"
          :class="['mb-2']"
          @click="setProject(project)">
          <div class="flex flex-col gap-2 p-4 border rounded-md click overflow-hidden text-ellipsis">
            <div class="flex gap-2">
              <img :src="project.project_icon" alt="Project Icon" class="w-10 h-10 rounded-full" />
              <div>
                <h3 class="text-lg font-bold">{{ project.project_name }}</h3>
                <p>{{ project.project_description }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="grow"></div>
    <div class="w-full flex flex-col gap-2 bg-base-300 p-4">
      <div class="text-xl">
        Create new project
      </div>
      <p class="text-sm">Copy the repository git url to create a new project</p>
      <div class="input input-bordered flex gap-1 items-center">
        <input type="text" class="grow" v-model="newProjectPath" placeholder="https://github.com/gbrian/codx-junior">
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
      newProjectPath: null
    };
  },
  mounted () {
    this.load()
  },
  computed: {
    projectName() {
      return this.$project.project_name;
    },
    projectIcon() {
      return this.$project.project_icon;
    },
    projectDescription() {
      return this.$project.project_description;
    },
    otherProjects () {
      return this.$project.allProjects.filter(project => this.$project.activeProject?.codx_path != project.codx_path)
    }
  },
  methods: {
    async load () {
    },
    async setProject(project) {
      this.$project.setActiveProject(project)
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
