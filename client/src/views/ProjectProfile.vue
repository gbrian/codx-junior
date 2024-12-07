<script setup>
import { API } from '../api/api';
import moment from 'moment';
</script>

<template>
  <div class="profile-container flex flex-col items-center h-full">
    <div class="p-4 w-full">
      <div class="hero-section text-center p-4 bg-gray-800 text-white rounded-lg">
        <h1 class="text-3xl font-bold mb-2">Welcome to codx-junior</h1>
        <p class="text-lg">codx-junior is your AI assistant helping full stack developers to maintain their open source projects.</p>
      </div>
      <div v-if="!$projects.allProjects?.length" class="p-6">
        <div class="font-semibold mb-4">Get Started with codx-junior</div>
        <ol class="list-decimal list-inside flex flex-col gap-2 ml-4">
          <li>Clone your repo
            <div class="ml-6 text-xs">Copy paste the repo url and press "Create new"</div>
          </li>
          <li>Add your settings
            <div class="ml-6 text-xs">Review important settings like AI provider settings 😉</div>
          </li>
          <li>Initialize the project's Knowledge
            <div class="ml-6 text-xs">Go to knowled and review settings. Set "watching" to catch codx mentions "@"</div>
          </li>
          <li>Create your first task! 
            <div class="ml-6 text-xs">Chat with codx-junior to solve a problem!</div>
          </li>
        </ol>
        
        <div class="mt-2">Happy co-AI-ding!! 🤩</div>
        And don't forget to <span class="text-yellow-600"><i class="fa-solid fa-star"></i></span> us <a href="https://github.com/gbrian/codx-junior" target="_blank" class="text-blue-500 underline">github.com/gbrian/codx-junior</a>
      </div>
    </div>

    <div class="projects-list mt-8 w-full flex flex-col gap-2 p-4" v-if="$projects.allProjects?.length">
      <h2 class="text-xl font-bold mb-4">Recent activity</h2>
      <div class="">
        <div class="flex flex-col gap-1 text-xs">
          <div class="h-96 overflow-auto bg-base-200">
            <table class="table">
              <thead class="">
                <th>Project</th>
                <th>Task</th>
                <th class="hidden md:block">Type</th>
                <th>Last update</th>
              </thead>
              <tbody class="">
                <tr class="click" @click="loadTask(task)" 
                  v-for="task in lastModifiedProjects" :key="task.name + task.project.project_name">
                  <td><div class="font-bold">{{ task.project.project_name }}</div></td>
                  <td>{{  task.name  }}</td>
                  <td class="hidden md:block">{{ task.mode }}</td>
                  <td>{{ task.fromNow }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div class="projects-list mt-8 w-full flex flex-col gap-2 p-4"  v-if="$projects.allProjects?.length">
      <h2 class="text-xl font-bold mb-4">All projects</h2>
      <div class="rounded-md p-1 bg-base-200 h-96 overflow-auto">
        <table class="table">
          <thead class="">
            <tr class="">
              <th class="px-4 py-2">Name</th>
              <th class="px-4 py-2" v-if="!$ui.mobile">Path</th>
              <th class="px-4 py-2 text-center">
                <div class="tooltip tooltip-bottom" data-tip="Tasks">
                  <i class="fa-solid fa-list-check"></i>
                </div>
              </th>
              <th class="px-4 py-2 text-center">
                <div class="tooltip tooltip-bottom" data-tip="Docs indexed">
                  <i class="fa-solid fa-puzzle-piece"></i>
                </div>
              </th>
              <th class="px-4 py-2 text-center hidden md:block">
                <div class="tooltip tooltip-bottom" data-tip="Last Update">
                  <i class="fa-regular fa-clock"></i>
                </div>
              </th>
              <th class="px-4 py-2 text-center">
                <div class="tooltip tooltip-bottom" data-tip="Checking for mentions">
                    <i class="fa-solid fa-at"></i>
                  </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="project in $projects.allProjects" :key="project.codx_path" @click="setProject(project)"
              class="cursor-pointer hover:bg-base-100">
              <td class="px-4 py-2 flex items-center">
                <img :src="project.project_icon" alt="Project Icon" class="w-6 h-6 rounded-full mr-2" />
                <span class="text-xs font-bold">{{ project.project_name }}</span>
              </td>
              <td class="px-4 py-2" v-if="!$ui.mobile">
                <div class="text-nowrap text-xs overflow-hidden tooltip tooltip-bottom text-left" :title="project.project_path" :data-tip="project.project_path">
                  {{ project.project_path.split("/").reverse().slice(0, 3).reverse().join(" / ") }}
                </div>
              </td>
              <td class="px-4 py-2 text-center">{{ project._metrics.number_of_chats }}</td>
              <td class="px-4 py-2 text-center">{{ project._metrics.files?.length }}</td>
              <td class="px-4 py-2 text-center hidden md:block">{{ lastRefresh(project._metrics.last_update) }}</td>
              <td class="px-4 py-2 text-center">
                <span class="badge bagde-sm badge-error" v-if="project._metrics.error">
                  Err! Review settings
                </span>
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
    <div class="w-full pb-4">
      <div class="flex flex-col gap-2 alert bg-primary/30 p-2 rounded-md">
        <div class="text-xl">
          Create new project
        </div>
        <p class="text-sm">Copy the repository git url to create a new project</p>
        <div class="input input-bordered flex gap-1 items-center">
          <input type="text" class="grow" v-model="newProjectPath" placeholder="https://github.com/gbrian/codx-junior">
          <button class="btn btn-sm" @click="createNewProject">
            Create new
          </button>
        </div>
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
      const lastProjects = this.$projects.allProjects?.filter(p => p._metrics.chats_changed_last.length)
      return lastProjects?.reduce((acc, project) =>
          acc.concat(...project._metrics.chats_changed_last.map(c => ({ ...c, project, fromNow: moment(c.updated_at).fromNow() }))), [])
        .sort((a, b) => a.updated_at > b.updated_at ? -1 : 1) 
    }
  },
  methods: {
    async setProject(project) {
      this.$projects.setActiveProject(project)
    },
    async createNewProject () {
      await API.project.create(this.newProjectPath)
      const project = this.$projects.allProjects.find(p => p.project_path === this.newProjectPath)
      this.newProjectPath = null
      await this.$projects.init()
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
      if (this.$projects.activeProject?.codx_path !=
        task.project.codx_path
      ) {
        await this.$projects.setActiveProject(task.project)
      }
      this.$ui.loadTask(task)
    }
  }
}
</script>