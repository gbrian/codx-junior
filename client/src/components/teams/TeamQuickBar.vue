<script setup>
import MainMenu from '@/components/main-menu/MainMenu.vue'
import QuickChatCreator from '@/components/chat/QuickChatCreator.vue'
</script>

<template>
  <div class="h-full relative">
    <div class="flex flex-col items-center gap-2 p-3 bg-[#1a1a1a] border-r border-white/5 shrink-0 overflow-y-auto overflow-x-hidden h-full">
      
      <!-- Quick Actions - Always visible and stacked -->
      <div class="flex flex-col items-center gap-2 w-full">
        <button
          class="w-10 h-10 rounded-xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-lg text-white/60 hover:bg-white/8 hover:text-white shrink-0"
          title="Home"
          @click="openHome"
        >
          <i class="fas fa-home"></i>
        </button>
        
        <QuickChatCreator />

        <button
          class="w-10 h-10 rounded-xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-lg text-white/60 hover:bg-white/8 hover:text-white shrink-0"
          title="Wiki"
          @click="openWiki"
        >
          <i class="fas fa-graduation-cap"></i>
        </button>

        <button
          class="w-10 h-10 rounded-xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-lg text-white/60 hover:bg-white/8 hover:text-white shrink-0"
          title="Tasks"
          @click="openTasks"
        >
          <i class="fas fa-tasks"></i>
        </button>

        <button
          class="w-10 h-10 rounded-xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-lg text-white/60 hover:bg-white/8 hover:text-white shrink-0"
          title="Media Library"
          @click="openFileExplorer"
        >
          <i class="fas fa-image"></i>
        </button>

        <button
          class="w-10 h-10 rounded-xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-lg text-white/60 hover:bg-white/8 hover:text-white shrink-0"
          title="More"
          @click="$emit('toggle-team-bar')"
        >
          <i class="fas fa-ellipsis"></i>
        </button>
      </div>

      <!-- Divider -->
      <div class="w-8 h-px bg-white/5 my-1"></div>
      
      <!-- Team icons -->
      <div class="flex flex-col items-center gap-2 w-full">
        <button
          v-for="team in teams"
          :key="team.id"
          class="w-10 h-10 rounded-xl flex items-center justify-center text-lg font-bold transition-all duration-200 overflow-hidden shrink-0"
          :class="activeTeam?.id === team.id
            ? 'ring-2 ring-primary rounded-lg'
            : 'hover:opacity-90'"
          :title="team.name"
          :style="{ backgroundColor: team.color || '#6366f1' }"
          @click="selectTeam(team)"
        >
          <img v-if="team.icon" :src="team.icon" class="w-full h-full object-cover" />
          <span v-else class="text-white font-bold">{{ team.name?.[0]?.toUpperCase() }}</span>
        </button>

        <div class="w-8 h-px bg-white/5 my-1"></div>

        <!-- Add team -->
        <button
          class="w-10 h-10 rounded-xl flex items-center justify-center text-success bg-white/8 hover:bg-white/15 hover:text-primary transition-all duration-200 shrink-0"
          title="Create Team"
          @click="$emit('create-team')"
        >
          <i class="fas fa-plus"></i>
        </button>
      </div>

      <div class="grow"></div>
      <MainMenu />
    </div>
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
    },
    isCollapsed: {
      type: Boolean,
      default: false
    },
    isTeamBarCollapsed: {
      type: Boolean,
      default: false
    }
  },
  emits: [
    'select-team',
    'create-team',
    'toggle-collapse',
    'expand-team-bar',
    'toggle-team-bar'
  ],
  data() {
    return {
    }
  },
  methods: {
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
    openFileExplorer() {
      this.$storex.ui.setActiveTab('file-explorer')
    },
    openVibeCoding() {
      this.$storex.ui.openVibeCoding()
    },
    selectTeam(team) {
      this.$emit('select-team', team)
    },
    toggleCollapse() {
      this.$emit('toggle-collapse')
    }
  }
}
</script>