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
            TO DO
          </button>
          <button class="btn btn-outline flex gap-2 tooltip tooltip-bottom" :data-tip="'Assisted coding with @codx' + ': ...'"
            @click="$ui.setShowCoder(true)">
            <i class="fa-solid fa-code"></i>
            AI Coding
          </button>
          <button class="btn btn-outline flex gap-2 tooltip tooltip-bottom" data-tip="Preview your changes"
            @click="$ui.setActiveTab('profiles')">
            <i class="fa-solid fa-circle-user"></i>
            Profiles
          </button>
        </div>
      </div>
      <div class="text-xs">
        <div class="mt-2">Happy coding 🤩</div>
        And don't forget to <span class="text-yellow-600"><i class="fa-solid fa-star"></i></span> us <a href="https://github.com/gbrian/codx-junior" target="_blank" class="text-blue-500 underline">github.com/gbrian/codx-junior</a>
      </div>
    </div>
  </div>
</div>
</template>
<script>
export default {
  data () {
    return {
      newProjectPath: ""
    }
  },
  methods: {
    async createNewProject () {
      await this.$projects.createNewProject(this.newProjectPath)
      this.newProjectPath = null
      this.$ui.setActiveTab('tasks')
    }
  }
}
</script>