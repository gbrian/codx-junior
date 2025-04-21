<script setup>
</script>

<template>
  <div class="profile-container flex flex-col h-full">
    <h1 class="text-3xl font-bold mb-2">Welcome to codx-junior</h1>
    <div class="text-sm text-secondary font-bold">You'll Never Code Alone!</div>
    <div class="flex flex-col gap-4 mt-4">
      <div class="flex items-center gap-2 mb-2">
        <input type="text" class="input input-sm input-bordered" placeholder="Filter projects..." v-model="filterQuery" />
        <button class="btn btn-sm" @click="filterQuery = null">
          <i class="fa-solid fa-circle-xmark"></i>
        </button>
      </div>
      <div class="text-xl font-bold">Projects</div>
      <div class="grid grid-cols-3 gap-2">
        <div
          v-for="project in filteredProjects"
          :key="project.project_id"
          class="p-4 rounded-md flex flex-col gap-2 bg-base-200 click"
          @click="setActiveProject(project)"
        >
          <p class="text-xs flex gap-1 tooltip" :data-tip="project.project_path"
            ><i class="fa-solid fa-folder"></i>
            <span class="text-nowrap overflow-hidden text-ellipsis">{{ project.project_path }}</span>
          </p>
          <div class="font-bold flex gap-2 items-start">
            <img class="w-6 h-6 rounded-full bg-white" :src="project.project_icon" />
            {{ project.project_name }}
          </div>
          <div class="grow"></div>
        </div>
      </div>
      <div class="font-bold">Add project</div>
      <div class="flex flex-col gap-2 rounded-md">
        <div class="group input input-bordered flex gap-1 items-center">
          <i class="fa-solid fa-i-cursor group-hover:animate-pulse"></i>
          <input type="text" class="grow" v-model="newProjectPath" />
          <button class="btn btn-sm" @click="createNewProject">
            <i class="fa-solid fa-plus"></i>
          </button>
        </div>
        <p class="text-xs italic text-center">Project name, git url or path</p>
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
              <span class="text-warning underline click" @click="$ui.setActiveTab('global-settings')"
                >AI provider settings</span
              >
              and
              <span class="underline click" @click="$ui.setActiveTab('settings')">Project settings</span>
            </div>
          </li>
          <li>
            <i class="fa-solid fa-book"></i> <span class="font-bold"> Review knowledge settings and profiles (optional)</span>
            <div class="ml-6 text-xs">
              Knowledge allows codx-junior to learn from the code base
              <span class="text-secondary underline click" @click="$ui.setActiveTab('knowledge')"> check it here</span>
              and profiles improves codx-junior performance...
              <span class="text-info underline click" @click="$ui.setActiveTab('profiles')"> check it at profiles</span>
            </div>
          </li>
        </ul>
        <div class="text-xl font-semibold my-2">Whats's next?</div>
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
  </div>
</template>

<script>
export default {
  data() {
    return {
      newProjectPath: "",
      filterQuery: ""
    }
  },
  computed: {
    filteredProjects() {
      return this.$projects.allProjects.filter(project => {
        return !this.filterQuery || (
          project.project_name.toLowerCase().includes(this.filterQuery.toLowerCase()) ||
          project.project_path.toLowerCase().includes(this.filterQuery.toLowerCase())
        )
      })
    }
  },
  methods: {
    async createNewProject() {
      await this.$projects.createNewProject(this.newProjectPath)
      this.newProjectPath = null
      this.$ui.setActiveTab('tasks')
    },
    setActiveProject(project) {
      this.$projects.setActiveProject(project)
      this.$ui.setActiveTab('tasks')
    }
  }
}
</script>