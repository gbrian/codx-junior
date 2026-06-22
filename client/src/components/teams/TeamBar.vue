<script setup>
import TeamChannelsSidebar from '@/components/teams/TeamChannelsSidebar.vue'
import RecentChatsQuickAccess from '@/components/chats/RecentChatsQuickAccess.vue'
import UserInfo from '@/components/UserInfo.vue'
import ProjectDetailt from '../ProjectDetailt.vue'
</script>

<template>
  <div class="flex flex-col h-full shrink-0 transition-all duration-300" :class="isCollapsed ? 'w-20' : 'w-64'">
    
    <!-- Project Selector Header - Always visible -->
    <div class="flex justify-between px-4 py-4 border-b border-base-content/10 bg-base-300/50 shrink-0">
      <ProjectDetailt 
        @click.stop=""
        :options="{ folders: true, showIcon: true }"
        :iconify="isCollapsed"
        @select="$projects.setActiveProject($event)"
      />
      <button
        @click="toggleCollapse"
        class="btn btn-xs btn-ghost p-1 w-6 h-6 min-h-0 ml-auto"
        :title="isCollapsed ? 'Expand' : 'Collapse'"
      >
        <i :class="isCollapsed ? 'fa-solid fa-chevron-right' : 'fa-solid fa-chevron-left'"></i>
      </button>
    </div>

    <!-- Scrollable content area -->
    <div class="flex-1 overflow-y-auto scrollbar-none flex flex-col gap-2 bg-base-200 border-r border-base-content/10 transition-all duration-300" :class="isCollapsed ? 'items-center' : ''">
      
      <!-- Channel list - visible only when expanded and team selected -->
      <div v-if="!isCollapsed && activeTeam" class="w-full">
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

      <!-- Collapsed Team Avatar - Only when collapsed and team exists -->
      <div v-if="isCollapsed && activeTeam" class="flex items-center justify-center px-3 py-2 border-b border-base-content/10 bg-base-300/50 rounded cursor-pointer tooltip tooltip-right" :data-tip="activeTeam.name">
        <div class="avatar w-8 rounded-full">
          <img :src="activeTeam.icon || generateTeamAvatar(activeTeam.name)" :alt="activeTeam.name" />
        </div>
      </div>

      <!-- No Project State -->
      <div v-if="!activeTeam" class="flex-1 flex flex-col items-center justify-center gap-3 px-4 text-base-content/40">
        <i class="fa-solid fa-people-group text-4xl"></i>
        <span class="text-xs text-center">Select or create a team</span>
        <button 
          @click="$emit('create-team')"
          class="btn btn-sm btn-primary"
        >
          Create Team
        </button>
      </div>

      <!-- Recent Chats: Full or Icon Mode -->
      <div v-if="activeTeam" :class="isCollapsed ? 'p-2 w-full flex flex-col items-center gap-2' : 'px-2 pb-4 w-full'">
        <RecentChatsQuickAccess :collapsed="isCollapsed" />
      </div>
    </div>

    <!-- User status bar (fixed at bottom) -->
    <div class="flex items-center px-3 py-2 border-t border-base-content/10 bg-base-300/50 shrink-0 transition-all duration-300" :class="isCollapsed ? 'justify-center' : 'gap-2'">
      <div v-if="!isCollapsed" class="flex items-center justify-between w-full gap-2">
        <div class="flex items-center gap-2 flex-1">
          <div class="w-7 h-7 rounded-full bg-primary text-primary-content flex items-center justify-center text-xs font-bold shrink-0">
            {{ userInitial }}
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-xs font-semibold truncate">{{ $users.user?.username }}</div>
            <div class="text-xs text-success flex items-center gap-1">
              <span class="w-1.5 h-1.5 rounded-full bg-success inline-block"></span>
              Online
            </div>
          </div>
        </div>
        <UserInfo>
          <template #trigger="{ togglePanel, dailyLimitStatus }">
            <button
              class="btn btn-xs btn-ghost p-1 w-6 h-6 min-h-0"
              @click="togglePanel"
              :class="dailyLimitStatus === 'exceeded' ? 'text-error' : dailyLimitStatus === 'warning' ? 'text-warning' : 'text-info'"
            >
              <i class="fa-solid fa-circle-info"></i>
            </button>
          </template>
        </UserInfo>
      </div>

      <!-- Collapsed user avatar -->
      <div v-if="isCollapsed" class="w-7 h-7 rounded-full bg-primary text-primary-content flex items-center justify-center text-xs font-bold shrink-0">
        {{ userInitial }}
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
    }
  },
  emits: [
    'open-team-settings',
    'open-create-channel',
    'edit-category',
    'edit-channel',
    'add-member',
    'select-member',
    'select-team',
    'create-team'
  ],
  data() {
    return {
      isCollapsed: false
    }
  },
  computed: {
    teams() {
      return this.$storex.teams.teams
    },
    userInitial() {
      return this.$users.user?.username?.[0]?.toUpperCase() || '?'
    }
  },
  methods: {
    toggleCollapse() {
      this.isCollapsed = !this.isCollapsed
    },
    selectTeam(team) {
      this.$storex.ui.setActiveTeam(team)
      this.$emit('select-team', team)
    },
    openCreateChannel(categoryId = null) {
      this.$emit('open-create-channel', categoryId)
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