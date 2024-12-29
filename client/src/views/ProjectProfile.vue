<script setup>
import { API } from '../api/api';
import moment from 'moment';
import { ref } from 'vue';

const isDropdownOpen = ref(false);

function toggleDropdown() {
  isDropdownOpen.value = !isDropdownOpen.value;
}
</script>

<template>
  <div class="profile-container flex flex-col items-center h-full">
    <div class="w-2/3 m-auto">
      <div class="hero-section text-center text-white rounded-lg">
        <h1 class="text-3xl font-bold mb-2">Welcome to codx-junior</h1>
        <div>
          Stuck in a coding jam? Let codx-junior be your trusty guide.
        </div>
        <div class="text-xl text-secondary font-bold">You'll Never Code Alone!</div>
      </div>

      <div class="flex flex-col gap-6 mt-4">
        <div class="flex flex-col gap-2 rounded-md">
          <div class="group input input-bordered flex gap-1 items-center">
            <i class="fa-solid fa-i-cursor group-hover:animate-pulse"></i>
            <input type="text" class="grow" v-model="newProjectPath">
            <button class="btn btn-sm" @click="createNewProject">
              Clone
            </button>
          </div>
          <p class="text-xs italic text-center">Paste a git repository url</p>
        </div>

        <div class="">
          <div class="text-xl font-semibold mb-4">Get Started with codx-junior</div>
          <ul class="text-xs flex flex-col gap-2 ml-4">
            <li><i class="fa-brands fa-square-git"></i><span class="font-bold"> Clone your repo</span>
              <div class="ml-6 text-xs">Copy paste the repo url and press "Clone"</div>
            </li>
            <li><i class="fa-solid fa-gear"></i><span class="font-bold"> Set your settings</span>
              <div class="ml-6 text-xs">Review important settings like 
                <span class=" text-warning underline click" @click="$ui.setActiveTab('global-settings')">AI provider settings</span> and 
                <span class="underline click" @click="$ui.setActiveTab('settings')">Project settings</span>
              </div>
            </li>
            <li><i class="fa-solid fa-book"></i> <span class="font-bold"> Review knowledge settings and profiles (optional)</span> 
              <div class="ml-6 text-xs">Knowledge allows codx-junior to learn from the code base 
                <span class=" text-secondary underline click" @click="$ui.setActiveTab('knowledge')"> check it here</span> and profiles improves codx-junior performance...
                <span class=" text-info underline click" @click="$ui.setActiveTab('profiles')"> check it at profiles</span>
              </div>
            </li>
          </ul>
          <div class="text-xl font-semibold my-2">Whats's next?</div>
          <div class="flex gap-2">
            <button class="btn btn-outline flex gap-2 tooltip tooltip-bottom" data-tip="Solve issues chatting with codx!" 
              @click="$ui.setActiveTab('tasks')">
              <i class="fa-solid fa-list-check"></i>
              My TO DO
            </button>
            <button class="btn btn-outline flex gap-2 tooltip tooltip-bottom" :data-tip="'Assisted coding with @codx' + ': ...'"
              @click="$ui.setShowCoder(true)">
              <i class="fa-solid fa-code"></i>
              Code with me
            </button>
            <button class="btn btn-outline flex gap-2 tooltip tooltip-bottom" data-tip="Preview your changes"
              @click="$ui.setActiveTab('profiles')">
              <i class="fa-solid fa-circle-user"></i>
              Project profiles
            </button>
          </div>
        </div>
        <div>
          <div class="mt-2">Happy coding!! 🤩</div>
          And don't forget to <span class="text-yellow-600"><i class="fa-solid fa-star"></i></span> us <a href="https://github.com/gbrian/codx-junior" target="_blank" class="text-blue-500 underline">github.com/gbrian/codx-junior</a>
        </div>
      </div>
    </div>

    <div class="projects-list mt-2 w-full flex flex-col gap-2 p-4" v-if="false">
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

    <div class="projects-list mt-2 w-full flex flex-col gap-2 p-4"  v-if="false">
      <h2 class="text-xl font-bold mb-4">All projects</h2>
      <div class="rounded-md p-1 bg-base-200 h-96 overflow-auto">
        <table class="table">
          <thead class="">
            <tr class="">
              <th class="px-4 py-2">Name</th>
              <th class="px-4 py-2" v-if="!$ui.mobile">Path</th>
              <th class="px-4 py-2 text-center">
                <div class="tooltip tooltip-bottom" data-tip="Wiki">
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
              <td class="px-4 py-2 text-center">
                <span v-if="!!project.project_wiki">
                  <i class="fa-solid fa-check"></i>
                </span>
              </td>
              <td class="px-4 py-2 text-center">{{ project._metrics?.files?.length }}</td>
              <td class="px-4 py-2 text-center hidden md:block">{{ lastRefresh(project._metrics?.last_update) }}</td>
              <td class="px-4 py-2 text-center">
                <span class="badge bagde-sm badge-error" v-if="project._metrics?.error">
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
    this.$projects.loadAllProjects()
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
      const lastProjects = this.$projects.allProjects?.filter(p => p._metrics?.chats_changed_last.length)
      return lastProjects?.reduce((acc, project) =>
          acc.concat(...project._metrics?.chats_changed_last.map(c => ({ ...c, project, fromNow: moment(c.updated_at).fromNow() }))), [])
        .sort((a, b) => a.updated_at > b.updated_at ? -1 : 1) 
    }
  },
  methods: {
    async setProject(project) {
      this.$projects.setActiveProject(project)
    },
    async createNewProject () {
      await this.$projects.createNewProject(this.newProjectPath)
      this.newProjectPath = null
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