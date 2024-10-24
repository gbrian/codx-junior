<script setup>
import { API } from '../api/api';
import moment from 'moment';
</script>

<template>
  <div class="profile-container flex flex-col items-center h-full">
    <div class="p-4">
      <div class="hero-section text-center p-4 bg-gray-800 text-white rounded-lg">
        <h1 class="text-3xl font-bold mb-2">Welcome to codx-junior</h1>
        <p class="text-lg">codx-junior is your AI assistant helping full stack developers to maintain their open source projects.</p>
      </div>
    </div>

    <div class="projects-list mt-8 w-full flex flex-col gap-2 p-4">
      <h2 class="text-xl font-bold mb-4">Recent activity</h2>
      <div class="">
        <div class="flex flex-col gap-1 text-xs">
          <div class="">
            <table class="table">
              <thead>
                <th>Project</th>
                <th>Task</th>
                <th>Type</th>
                <th>Last update</th>
              </thead>
              <tbody class="">
                <tr class="click" @click="loadTask(task)" 
                  v-for="task in lastModifiedProjects" :key="task.name + task.project.project_name">
                  <td><div class="font-bold">{{ task.project.project_name }}</div></td>
                  <td>{{  task.name  }}</td>
                  <td>{{ task.mode }}</td>
                  <td>{{ task.fromNow }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div class="projects-list mt-8 w-full flex flex-col gap-2 p-4">
      <h2 class="text-xl font-bold mb-4">All projects</h2>
      <div class="rounded-md p-1 bg-base-200">
        <table class="table">
          <thead>
            <tr class="">
              <th class="px-4 py-2">Name</th>
              <th class="px-4 py-2">Path</th>
              <th class="px-4 py-2 text-center">
                <div class="tooltip" data-tip="Tasks">
                  <i class="fa-solid fa-list-check"></i>
                </div>
              </th>
              <th class="px-4 py-2 text-center">
                <div class="tooltip" data-tip="Docs indexed">
                  <i class="fa-solid fa-puzzle-piece"></i>
                </div>
              </th>
              <th class="px-4 py-2 text-center">
                <div class="tooltip" data-tip="Last Update">
                  <i class="fa-regular fa-clock"></i>
                </div>
              </th>
              <th class="px-4 py-2 text-center">
                <div class="tooltip" data-tip="Checking for mentions">
                    <i class="fa-solid fa-at"></i>
                  </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="project in $project.allProjects" :key="project.codx_path" @click="setProject(project)"
              class="cursor-pointer hover:bg-base-100">
              <td class="px-4 py-2 flex items-center">
                <img :src="project.project_icon" alt="Project Icon" class="w-6 h-6 rounded-full mr-2" />
                <span class="text-xs font-bold">{{ project.project_name }}</span>
              </td>
              <td class="px-4 py-2">
                <div class="text-nowrap text-xs overflow-hidden tooltip text-left" :title="project.project_path" :data-tip="project.project_path">
                  {{ project.project_path.split("/").reverse().slice(0, 3).reverse().join(" / ") }}
                </div>
              </td>
              <td class="px-4 py-2 text-center">{{ project.metrics.number_of_chats }}</td>
              <td class="px-4 py-2 text-center">{{ project.metrics.files.length }}</td>
              <td class="px-4 py-2 text-center">{{ lastRefresh(project.metrics.last_update) }}</td>
              <td class="px-4 py-2 text-center">
                <span v-if="project.watching">
                  <i class="fa-solid fa-check"></i>
                </span>
              </td>
            </tr>
          </tbody>
        </table>
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
  created () {
    this.$project.loadAllProjects()
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
    lastModifiedProjects () {
      const lastProjects = this.$project.allProjects?.filter(p => p.metrics.chats_changed_last_24h.length)
      return lastProjects?.reduce((acc, project) =>
          acc.concat(...project.metrics.chats_changed_last_24h.map(c => ({ ...c, project, fromNow: moment(c.updated_at).fromNow() }))), [])
        .sort((a, b) => a.updated_at > b.updated_at ? -1 : 1) 
    }
  },
  methods: {
    async setProject(project) {
      this.$project.setActiveProject(project)
    },
    async createNewProject () {
      await API.project.create(this.newProjectPath)
      const project = this.$project.allProjects.find(p => p.project_path === this.newProjectPath)
      this.newProjectPath = null
      await this.$project.init()
      this.setProject(project)
    },
    lastRefresh(last_update) {
      if (last_update) {
        const ts = parseInt(last_update, 10) * 1000
        return moment(new Date(ts)).fromNow()
      }
      return null
    },
    async loadTask(task) {
      if (this.$project.activeProject?.codx_path !=
        task.project.codx_path
      ) {
        await this.$project.setActiveProject(task.project)
      }
      this.$emit('open-task', task)
    }
  }
}
</script>