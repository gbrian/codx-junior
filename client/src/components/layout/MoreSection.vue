<script setup>
</script>

<template>
  <div v-if="moreExpanded && !isCollapsed && !isMobileExpanded" class="px-2 py-2 shrink-0 border-b border-white/5">
    <div class="flex flex-col gap-1 pl-6">
      <button
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:bg-white/8 hover:text-white transition-colors text-left w-full"
        @click="handleNavigateToHome"
        title="Home"
      >
        <i class="fa-solid fa-home w-4 text-center shrink-0"></i>
        <span>Home</span>
      </button>

      <button
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:bg-white/8 hover:text-white transition-colors text-left w-full"
        @click="handleShowNewProject"
        title="New project"
      >
        <i class="fa-solid fa-plus w-4 text-center shrink-0"></i>
        <span>New project</span>
      </button>

      <button
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:bg-white/8 hover:text-white transition-colors text-left w-full"
        @click="handleNavigateToTeam"
        title="Team"
      >
        <i class="fa-solid fa-people-group w-4 text-center shrink-0"></i>
        <span>Team</span>
      </button>

      <button
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:bg-white/8 hover:text-white transition-colors text-left w-full"
        @click="handleNavigateToViews"
        title="Views"
      >
        <i class="fa-solid fa-eye w-4 text-center shrink-0"></i>
        <span>Views</span>
      </button>

      <button
        v-if="isProjectAdmin"
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:bg-white/8 hover:text-white transition-colors text-left w-full"
        @click="handleNavigateToProfiles"
        title="Profiles"
      >
        <i class="fa-solid fa-id-badge w-4 text-center shrink-0"></i>
        <span>Profiles</span>
      </button>

      <button
        v-if="isProjectAdmin"
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:bg-white/8 hover:text-white transition-colors text-left w-full"
        @click="handleNavigateToKnowledge"
        title="Knowledge"
      >
        <i class="fa-solid fa-magnifying-glass w-4 text-center shrink-0"></i>
        <span>Knowledge</span>
      </button>

      <button
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:bg-white/8 hover:text-white transition-colors text-left w-full"
        @click="handleNavigateToAnalytics"
        title="Analytics"
      >
        <i class="fa-solid fa-chart-area w-4 text-center shrink-0"></i>
        <span>Analytics</span>
      </button>

      <div class="my-1 h-px bg-white/5"></div>

      <button
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-error hover:bg-error/10 hover:text-error transition-colors text-left w-full"
        @click="handleLogout"
        title="Log out"
      >
        <i class="fa-solid fa-right-from-bracket w-4 text-center shrink-0"></i>
        <span>Log out</span>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    moreExpanded: { type: Boolean, default: false },
    isCollapsed: { type: Boolean, default: false },
    isMobileExpanded: { type: Boolean, default: false },
    isProjectAdmin: { type: Boolean, default: false }
  },
  emits: ['close'],
  methods: {
    handleNavigateToHome() {
      this.$storex.$router.$navigation.apps.openHome()
      this.$emit('close')
    },
    handleShowNewProject() {
      this.$ui.showNewProject(true)
      this.$emit('close')
    },
    handleNavigateToTeam() {
      this.$storex.$router.$navigation.apps.openTeam()
      this.$emit('close')
    },
    handleNavigateToViews() {
      this.$storex.$router.$navigation.apps.openViews()
      this.$emit('close')
    },
    handleNavigateToProfiles() {
      this.$storex.$router.$navigation.apps.openProfiles()
      this.$emit('close')
    },
    handleNavigateToKnowledge() {
      this.$storex.$router.$navigation.apps.openKnowledge()
      this.$emit('close')
    },
    handleNavigateToAnalytics() {
      this.$storex.$router.$navigation.apps.openAnalytics()
      this.$emit('close')
    },
    handleLogout() {
      this.$users.logout()
    }
  }
}
</script>