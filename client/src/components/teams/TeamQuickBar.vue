<script setup>
import MainMenu from '@/components/main-menu/MainMenu.vue'
</script>

<template>
  <div class="flex flex-col items-center gap-2 px-2 py-3 bg-base-200 border-r border-base-content/10 shrink-0 overflow-y-auto overflow-x-hidden">
    
    <div class="tooltip tooltip-right cursor-pointer shrink-0" data-tip="Home" @click="openHome">
      <div class="w-10 h-10 rounded-2xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-xl bg-base-300 text-base-content hover:bg-base-content/10">
        <i class="fa-solid fa-home"></i>
      </div>
    </div>

    <div class="tooltip tooltip-right cursor-pointer shrink-0" data-tip="New Chat" @click="openQuickChat">
      <div class="w-10 h-10 rounded-2xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-xl bg-base-300 text-base-content hover:bg-base-content/10">
        <i class="fa-solid fa-comments"></i>
      </div>
    </div>

    <div class="tooltip tooltip-right cursor-pointer shrink-0" data-tip="New Project" @click="openProjects">
      <div class="w-10 h-10 rounded-2xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-xl bg-base-300 text-base-content hover:bg-base-content/10">
        <i class="fa-solid fa-folder-plus"></i>
      </div>
    </div>

    <div class="tooltip tooltip-right cursor-pointer shrink-0" data-tip="Wiki" @click="openWiki">
      <div class="w-10 h-10 rounded-2xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-xl bg-base-300 text-base-content hover:bg-base-content/10">
        <i class="fa-solid fa-graduation-cap"></i>
      </div>
    </div>

    <div class="tooltip tooltip-right cursor-pointer shrink-0" data-tip="Tasks" @click="openTasks">
      <div class="w-10 h-10 rounded-2xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-xl bg-base-300 text-base-content hover:bg-base-content/10">
        <i class="fa-brands fa-trello"></i>
      </div>
    </div>

    <div
      class="tooltip tooltip-right cursor-pointer shrink-0"
      data-tip="Media Library"
      @click="openMediaLibrary"
    >
      <div class="w-10 h-10 rounded-2xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-xl bg-base-300 text-base-content hover:bg-base-content/10">
        <i class="fa-solid fa-image"></i>
      </div>
    </div>

    <!-- Vibe Coding button — visible in expert view mode -->
    <div
      class="tooltip tooltip-right cursor-pointer shrink-0"
      data-tip="Vibe Coding"
      @click="openVibeCoding"
      v-if="isExpertMode"
    >
      <div class="w-10 h-10 rounded-2xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-xl bg-base-300 text-base-content hover:bg-base-content/10">
        <i class="fa-solid fa-wand-magic-sparkles"></i>
      </div>
    </div>

    <!-- Team icons -->
    <div class="divider my-0 w-8 mx-auto"></div>
    
    <div
      v-for="team in teams"
      :key="team.id"
      class="tooltip tooltip-right cursor-pointer shrink-0"
      :data-tip="team.name"
      @click="selectTeam(team)"
    >
      <div
        class="w-10 h-10 rounded-2xl flex items-center justify-center text-lg font-bold transition-all duration-200 hover:rounded-xl overflow-hidden"
        :class="activeTeam?.id === team.id
          ? 'ring-2 ring-primary rounded-xl'
          : 'hover:opacity-90'"
        :style="{ backgroundColor: team.color || '#6366f1' }"
      >
        <img v-if="team.icon" :src="team.icon" class="w-full h-full object-cover" />
        <span v-else class="text-white font-bold">{{ team.name?.[0]?.toUpperCase() }}</span>
      </div>
    </div>

    <div class="divider my-0 w-8 mx-auto"></div>

    <!-- Add team -->
    <div
      class="tooltip tooltip-right cursor-pointer shrink-0"
      data-tip="Create Team"
      @click="$emit('create-team')"
    >
      <div class="w-10 h-10 rounded-2xl flex items-center justify-center text-success bg-base-300 hover:bg-success/20 hover:rounded-xl transition-all duration-200">
        <i class="fa-solid fa-plus"></i>
      </div>
    </div>

    <div class="grow"></div>
    <MainMenu />
  </div>
</template>

<script>
export default {
  props: {
    teams: {
      type: Array,
      required: true
    },
    activeTeam: {
      type: Object,
      default: null
    }
  },
  emits: [
    'select-team',
    'create-team'
  ],
  data() {
    return {}
  },
  computed: {
    isExpertMode() {
      return this.$storex.ui.viewMode === 'expert'
    }
  },
  methods: {
    openQuickChat() {
      this.$storex.ui.openQuickChat()
    },
    openHome() {
      this.$storex.ui.openHome()
    },
    openProjects() {
      this.$storex.ui.openProjects()
    },
    openWiki() {
      this.$storex.ui.openWiki()
    },
    openTasks() {
      this.$storex.ui.openTasks()
    },
    openMediaLibrary() {
      this.$storex.ui.openMediaLibrary()
    },
    openVibeCoding() {
      this.$storex.ui.openVibeCoding()
    },
    selectTeam(team) {
      this.$emit('select-team', team)
    }
  }
}
</script>