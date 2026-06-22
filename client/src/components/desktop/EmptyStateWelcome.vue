<script setup>
import { ref } from 'vue'
</script>

<template>
  <div class="w-full h-full flex flex-col items-center justify-center bg-gradient-to-b from-base-200 to-base-100 p-8">
    <!-- Logo and Introduction Section -->
    <div class="text-center mb-12 max-w-2xl">
      <div class="mb-6">
        <img src="/only_icon.png" alt="CODX" class="w-24 h-24 mx-auto mb-4" />
      </div>
      <h1 class="text-4xl font-bold bg-gradient-to-r from-codx-primary to-codx-secondary bg-clip-text text-transparent mb-2">
        Welcome to CODX
      </h1>
      <p class="text-base-content/70 text-lg mb-4">
        Meet <span class="font-semibold text-codx-primary">codx-junior</span>, your AI project assistant
      </p>
      <p class="text-base-content/60 text-base leading-relaxed">
        I'm <span class="font-semibold">codx-junior</span> and I can help you with your projects:
      </p>
      
      <i class="fa-solid fa-folder-plus text-codx-primary"></i>
      <span class="mx-2">Creating and managing projects</span>
      <i class="fa-brands fa-trello text-info"></i>
      <span class="mx-2">Managing tasks and organizing work</span>
      <i class="fa-solid fa-people-group text-codx-secondary"></i>
      <span class="mx-2">Collaborating with your team</span>
      <i class="fa-solid fa-wand-magic-sparkles text-purple-500"></i>
      <span class="mx-2">Running vibe coding sessions</span>
    </div>

    <!-- Primary Action Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl w-full mb-12">
      <!-- Create or Import Project -->
      <button
        @click="openProjects"
        class="p-6 bg-base-100 border-2 border-codx-primary/20 hover:border-codx-primary hover:shadow-lg hover:shadow-codx-primary/20 transition-all duration-200 text-left group rounded-lg"
      >
        <div class="flex items-start gap-4">
          <i class="fa-solid fa-folder-plus text-2xl text-codx-primary mt-1 group-hover:scale-110 transition-transform"></i>
          <div>
            <h3 class="font-semibold text-base-content mb-1">Create or Import Project</h3>
            <p class="text-sm text-base-content/60">Start a new project or import an existing one</p>
          </div>
        </div>
      </button>

      <!-- Create Team -->
      <button
        @click="openTeams"
        class="p-6 bg-base-100 border-2 border-codx-secondary/20 hover:border-codx-secondary hover:shadow-lg hover:shadow-codx-secondary/20 transition-all duration-200 text-left group rounded-lg"
      >
        <div class="flex items-start gap-4">
          <i class="fa-solid fa-people-group text-2xl text-codx-secondary mt-1 group-hover:scale-110 transition-transform"></i>
          <div>
            <h3 class="font-semibold text-base-content mb-1">Create Your Team</h3>
            <p class="text-sm text-base-content/60">Collaborate with your team members</p>
          </div>
        </div>
      </button>

      <!-- Manage Tasks -->
      <button
        @click="openTasks"
        class="p-6 bg-base-100 border-2 border-info/20 hover:border-info hover:shadow-lg hover:shadow-info/20 transition-all duration-200 text-left group rounded-lg"
      >
        <div class="flex items-start gap-4">
          <i class="fa-brands fa-trello text-2xl text-info mt-1 group-hover:scale-110 transition-transform"></i>
          <div>
            <h3 class="font-semibold text-base-content mb-1">Manage Tasks</h3>
            <p class="text-sm text-base-content/60">Organize and track your project work</p>
          </div>
        </div>
      </button>

      <!-- Start Vibe Coding -->
      <button
        @click="openVibeCoding"
        class="p-6 bg-base-100 border-2 border-purple-500/20 hover:border-purple-500 hover:shadow-lg hover:shadow-purple-500/20 transition-all duration-200 text-left group rounded-lg"
      >
        <div class="flex items-start gap-4">
          <i class="fa-solid fa-wand-magic-sparkles text-2xl text-purple-500 mt-1 group-hover:scale-110 transition-transform"></i>
          <div>
            <h3 class="font-semibold text-base-content mb-1">Start Vibe Coding</h3>
            <p class="text-sm text-base-content/60">AI-powered coding session with codx-junior</p>
          </div>
        </div>
      </button>
    </div>

    <!-- Quick Tips / Tutorials Section -->
    <div class="max-w-3xl w-full">
      <h2 class="text-sm font-semibold text-base-content/70 mb-3 uppercase tracking-wide">
        <i class="fa-solid fa-graduation-cap text-info mr-2"></i>Tutorials & How-To Guides
      </h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <button 
          @click="openTutorial('getting-started')"
          class="flex items-start gap-3 p-3 bg-info/10 hover:bg-info/20 rounded-lg text-sm text-base-content/70 hover:text-base-content transition-colors text-left group"
        >
          <i class="fa-solid fa-play-circle text-info mt-0.5 flex-shrink-0 group-hover:scale-110 transition-transform"></i>
          <span>Getting Started with CODX</span>
        </button>
        
        <button 
          @click="openTutorial('vibe-coding')"
          class="flex items-start gap-3 p-3 bg-info/10 hover:bg-info/20 rounded-lg text-sm text-base-content/70 hover:text-base-content transition-colors text-left group"
        >
          <i class="fa-solid fa-wand-magic-sparkles text-info mt-0.5 flex-shrink-0 group-hover:scale-110 transition-transform"></i>
          <span>How to Use Vibe Coding Sessions</span>
        </button>

        <button 
          @click="openTutorial('collaboration')"
          class="flex items-start gap-3 p-3 bg-info/10 hover:bg-info/20 rounded-lg text-sm text-base-content/70 hover:text-base-content transition-colors text-left group"
        >
          <i class="fa-solid fa-people-group text-info mt-0.5 flex-shrink-0 group-hover:scale-110 transition-transform"></i>
          <span>Team Collaboration Best Practices</span>
        </button>

        <button 
          @click="openTutorial('task-management')"
          class="flex items-start gap-3 p-3 bg-info/10 hover:bg-info/20 rounded-lg text-sm text-base-content/70 hover:text-base-content transition-colors text-left group"
        >
          <i class="fa-brands fa-trello text-info mt-0.5 flex-shrink-0 group-hover:scale-110 transition-transform"></i>
          <span>Task Management and Organization</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'EmptyStateWelcome',
  data() {
    return {}
  },
  methods: {
    openProjects() {
      this.$storex.ui.openProjects()
    },
    openTeams() {
      this.$storex.ui.openTeams()
    },
    openTasks() {
      this.$storex.ui.openTasks()
    },
    openVibeCoding() {
      this.$storex.ui.openVibeCoding()
    },
    openTutorial(tutorialId) {
      this.$storex.ui.openTutorial(tutorialId)
    }
  }
}
</script>