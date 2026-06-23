<script setup>
import TeamChannelsSidebar from '@/components/teams/TeamChannelsSidebar.vue'
import RecentChatsQuickAccess from '@/components/chats/RecentChatsQuickAccess.vue'
</script>

<template>
  <div class="flex flex-col h-full shrink-0 transition-all duration-300" :class="isCollapsed ? 'w-0 overflow-hidden' : 'w-64'">
    
    <!-- Header with collapse button -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-base-content/10 bg-base-200">
      <h2 class="font-bold text-sm">Teams</h2>
      <button
        @click="toggleCollapse"
        class="btn btn-ghost btn-xs p-1 h-6 w-6 min-h-6"
        :title="isCollapsed ? 'Expand' : 'Collapse'"
      >
        <svg v-if="!isCollapsed" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
    
    <!-- Main content: Only expanded view now -->
    <div class="flex-1 overflow-y-auto scrollbar-none flex flex-col gap-2 bg-base-200 border-r border-base-content/10">
      
      <!-- Channel list -->
      <div v-if="activeTeam" class="w-full">
        <TeamChannelsSidebar
          :active-team="activeTeam"
          :teams="teams"
          @select-team="selectTeam"
          @open-team-settings="$emit('open-team-settings')"
          @open-create-channel="openCreateChannel"
          @edit-category="$emit('edit-category', $event)"
          @edit-channel="$emit('edit-channel', $event)"
          @add-member="$emit('add-member')"
          @select-member="$emit('select-member', $event)"
        />

        <!-- Section Divider -->
        <div class="px-4 opacity-20">
          <hr class="border-base-content/20" />
        </div>
      </div>

      <!-- No Team State -->
      <div v-if="!activeTeam" class="py-2 flex-1 flex flex-col items-center justify-center gap-3 px-4 text-base-content/40">
        <button 
          @click="$emit('create-team')"
          class="btn btn-sm btn-primary w-full"
        >
          Create Team
        </button>
      </div>

      <!-- Recent Chats -->
      <div class="px-2 pb-4 w-full">
        <RecentChatsQuickAccess :collapsed="false" />
      </div>

    </div>
  </div>
</template>

<script>
export default {
  name: 'TeamBar',
  props: {
    activeTeam: {
      type: Object,
      default: null
    },
    isCollapsed: {
      type: Boolean,
      default: false
    }
  },
  emits: [
    'toggle-collapse',
    'open-team-settings',
    'open-create-channel',
    'edit-category',
    'edit-channel',
    'add-member',
    'select-member',
    'select-team',
    'create-team'
  ],
  computed: {
    teams() {
      return this.$storex.teams.teams
    }
  },
  methods: {
    selectTeam(team) {
      this.$storex.ui.setActiveTeam(team)
      this.$emit('select-team', team)
    },
    openCreateChannel(categoryId = null) {
      this.$emit('open-create-channel', categoryId)
    },
    toggleCollapse() {
      this.$storex.ui.setTeamBarCollapsed(!this.isCollapsed)
      this.$emit('toggle-collapse')
    }
  }
}
</script>