<script setup>
import { v4 as uuidv4 } from 'uuid'
</script>

<template>
  <div class="w-full">
    <!-- Single team header button -->
    <button 
      class="w-full flex gap-2 items-center px-3 py-3 border-b border-base-content/10 hover:bg-base-300/50 transition-colors"
      :popovertarget="`team-selector-${uid}`"
      :style="`anchor-name:--team-selector-${uid}`"
    >
      <div class="avatar" v-if="activeTeam">
        <div class="w-6 h-6 rounded">
          <img :src="activeTeam.icon || generateTeamAvatar(activeTeam.name)" />
        </div>
      </div>
      <span class="font-bold text-sm truncate flex-1 text-left">{{ activeTeam?.name }}</span>
      <i class="fa-solid fa-chevron-down text-xs text-base-content/50 shrink-0"></i>
    </button>

    <!-- Team Selector Popover -->
    <div 
      class="w-56 border border-base-content/20 rounded-lg bg-base-100 shadow-lg"
      popover
      :id="`team-selector-${uid}`"
      :style="`position-anchor:--team-selector-${uid}`"
    >
      <ul class="menu p-1">
        <!-- Teams List -->
        <li v-for="team in teams" :key="team.id">
          <a @click.prevent.stop="selectTeam(team)" class="flex items-center justify-between">
            <div class="flex items-center gap-2 flex-1 min-w-0">
              <img class="w-5 h-5 rounded shrink-0" :src="team.icon || generateTeamAvatar(team.name)" />
              <span class="truncate text-sm">{{ team.name }}</span>
            </div>
            <!-- Settings icon only on active team -->
            <button
              v-if="activeTeam?.id === team.id"
              class="btn btn-ghost btn-xs p-0 w-5 h-5 min-h-0 shrink-0"
              @click.prevent.stop="openSettings"
              title="Team settings"
            >
              <i class="fa-solid fa-gear text-xs"></i>
            </button>
          </a>
        </li>

        <li v-if="teams.length > 0"><hr class="my-1 border-base-content/10" /></li>

        <!-- Create New Team -->
        <li>
          <a @click.prevent.stop="createTeam" class="text-info">
            <i class="fa-solid fa-plus"></i>
            Create New Team
          </a>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    activeTeam: {
      type: Object,
      default: null
    },
    teams: {
      type: Array,
      default: () => []
    }
  },
  emits: ['select', 'create', 'open-settings'],
  data() {
    return {
      uid: uuidv4()
    }
  },
  methods: {
    selectTeam(team) {
      this.$emit('select', team)
    },
    createTeam() {
      this.$emit('create')
    },
    openSettings() {
      this.$emit('open-settings')
    },
    generateTeamAvatar(name) {
      const canvas = document.createElement('canvas')
      canvas.width = canvas.height = 32
      const ctx = canvas.getContext('2d')
      ctx.fillStyle = '#667eea'
      ctx.fillRect(0, 0, 32, 32)
      ctx.fillStyle = '#fff'
      ctx.font = 'bold 16px Arial'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(name.charAt(0).toUpperCase(), 16, 16)
      return canvas.toDataURL()
    }
  }
}
</script>