<script setup>
import TeamChannelsSidebar from '@/components/teams/TeamChannelsSidebar.vue'
import RecentChatsQuickAccess from '@/components/chats/RecentChatsQuickAccess.vue'
import UserInfo from '@/components/UserInfo.vue'
import ProjectDetailt from '../ProjectDetailt.vue'
import MainMenu from '@/components/main-menu/MainMenu.vue'
</script>

<template>
  <div class="flex flex-col h-full shrink-0 transition-all duration-300" :class="isCollapsed ? 'w-20' : 'w-64'">
    
    <!-- Header: Project Selector + Collapse Toggle -->
    <div class="flex justify-between gap-2 px-4 py-4 border-b border-base-content/10 bg-base-300/50 shrink-0">
      <ProjectDetailt 
        @click.stop=""
        :options="{ folders: true, showIcon: true }"
        :iconify="isCollapsed"
        @select="$storex.projects.setActiveProject($event)"
      />
      <button
        @click="toggleCollapse"
        class="btn btn-xs btn-ghost p-1 w-6 h-6 min-h-0 ml-auto"
        :title="isCollapsed ? 'Expand' : 'Collapse'"
      >
        <i :class="isCollapsed ? 'fa-solid fa-chevron-right' : 'fa-solid fa-chevron-left'"></i>
      </button>
    </div>

    <!-- Main content: Collapsed or Expanded view -->
    <div class="flex-1 overflow-y-auto scrollbar-none flex flex-col gap-2 bg-base-200 border-r border-base-content/10 transition-all duration-300" :class="isCollapsed ? 'items-center' : ''">
      
      <!-- ──── EXPANDED VIEW ──────────────────────────────────────────────── -->
      <template v-if="!isCollapsed">
        <!-- Channel list - visible only when expanded and team selected -->
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
          <i class="fa-solid fa-people-group text-4xl"></i>
          <span class="text-xs text-center">Select or create a team</span>
          <button 
            @click="$emit('create-team')"
            class="btn btn-sm btn-primary"
          >
            Create Team
          </button>
        </div>

        <!-- Quick actions - visible in expanded mode -->
        <div class="px-2 w-full flex flex-col gap-2">
          <div class="text-xs font-semibold text-base-content/60 px-2">Quick Actions</div>
          <div class="grid grid-cols-3 gap-2">
            <button class="btn btn-xs btn-ghost" @click="openHome" title="Home">
              <i class="fa-solid fa-home"></i>
            </button>
            <button class="btn btn-xs btn-ghost" @click="openQuickChat" title="New Chat">
              <i class="fa-solid fa-comments"></i>
            </button>
            <button class="btn btn-xs btn-ghost" @click="openProjects" title="Projects">
              <i class="fa-solid fa-folder-plus"></i>
            </button>
            <button class="btn btn-xs btn-ghost" @click="openWiki" title="Wiki">
              <i class="fa-solid fa-graduation-cap"></i>
            </button>
            <button class="btn btn-xs btn-ghost" @click="openTasks" title="Tasks">
              <i class="fa-brands fa-trello"></i>
            </button>
            <button class="btn btn-xs btn-ghost" @click="openMediaLibrary" title="Media">
              <i class="fa-solid fa-image"></i>
            </button>
            <button v-if="isExpertMode" class="btn btn-xs btn-ghost" @click="openVibeCoding" title="Vibe Coding">
              <i class="fa-solid fa-wand-magic-sparkles"></i>
            </button>
          </div>
        </div>

        <!-- Recent Chats -->
        <div class="px-2 pb-4 w-full">
          <RecentChatsQuickAccess :collapsed="false" />
        </div>

        <!-- Main Menu -->
        <div class="px-2 pb-2 w-full">
          <MainMenu />
        </div>
      </template>

      <!-- ──── COLLAPSED VIEW ──────────────────────────────────────────────── -->
      <template v-if="isCollapsed">
        <!-- Quick action buttons -->
        <div class="w-full flex flex-col items-center gap-2 px-2 py-3">
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

          <div class="tooltip tooltip-right cursor-pointer shrink-0" data-tip="Media Library" @click="openMediaLibrary">
            <div class="w-10 h-10 rounded-2xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-xl bg-base-300 text-base-content hover:bg-base-content/10">
              <i class="fa-solid fa-image"></i>
            </div>
          </div>

          <div v-if="isExpertMode" class="tooltip tooltip-right cursor-pointer shrink-0" data-tip="Vibe Coding" @click="openVibeCoding">
            <div class="w-10 h-10 rounded-2xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-xl bg-base-300 text-base-content hover:bg-base-content/10">
              <i class="fa-solid fa-wand-magic-sparkles"></i>
            </div>
          </div>
        </div>

        <!-- Team selector dropdown -->
        <div class="w-full px-2 py-2 border-t border-base-content/10 border-b border-base-content/10">
          <div class="dropdown dropdown-bottom w-full">
            <button class="btn btn-sm btn-ghost w-full" tabindex="0">
              <div v-if="activeTeam" class="w-6 h-6 rounded-full overflow-hidden flex-shrink-0">
                <img v-if="activeTeam.icon" :src="activeTeam.icon" :alt="activeTeam.name" class="w-full h-full object-cover" />
                <div v-else class="w-full h-full flex items-center justify-center text-xs font-bold" :style="{ backgroundColor: activeTeam.color || '#6366f1' }">
                  {{ activeTeam.name?.[0]?.toUpperCase() }}
                </div>
              </div>
              <i v-else class="fa-solid fa-people-group text-lg text-base-content/40"></i>
            </button>
            <div tabindex="0" class="dropdown-content z-50 menu p-2 shadow bg-base-300 rounded-box w-48">
              <li v-for="team in teams" :key="team.id">
                <a @click="selectTeam(team)" :class="activeTeam?.id === team.id ? 'active' : ''">
                  <div class="w-5 h-5 rounded-full overflow-hidden flex-shrink-0">
                    <img v-if="team.icon" :src="team.icon" :alt="team.name" class="w-full h-full object-cover" />
                    <div v-else class="w-full h-full flex items-center justify-center text-xs font-bold text-white" :style="{ backgroundColor: team.color || '#6366f1' }">
                      {{ team.name?.[0]?.toUpperCase() }}
                    </div>
                  </div>
                  <span>{{ team.name }}</span>
                </a>
              </li>
              <li><hr class="my-1" /></li>
              <li><a @click="$emit('create-team')"><i class="fa-solid fa-plus"></i> Create Team</a></li>
            </div>
          </div>
        </div>

        <!-- Create channel button when team selected -->
        <div v-if="activeTeam" class="w-full px-2 py-2">
          <button
            @click="openCreateChannelDefault"
            class="btn btn-xs btn-ghost w-full tooltip tooltip-right"
            data-tip="Create Channel"
          >
            <i class="fa-solid fa-plus"></i>
          </button>
        </div>

        <!-- Recent Chats in collapsed mode -->
        <div class="w-full px-2">
          <RecentChatsQuickAccess :collapsed="true" />
        </div>

        <!-- Menu at bottom -->
        <div class="mt-auto px-2 pb-2 w-full">
          <MainMenu />
        </div>
      </template>
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
  created() {
    this.isCollapsed = this.$storex.ui.teamBarCollapsed
  },
  computed: {
    teams() {
      return this.$storex.teams.teams
    },
    userInitial() {
      return this.$users.user?.username?.[0]?.toUpperCase() || '?'
    },
    isExpertMode() {
      return this.$storex.ui.viewMode === 'expert'
    }
  },
  watch: {
    isCollapsed(newVal) {
      this.$storex.ui.setTeamBarCollapsed(newVal)
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
    openCreateChannelDefault() {
      const defaultCategoryId = this.activeTeam?.categories?.[0]?.id || null
      this.openCreateChannel(defaultCategoryId)
    },
    openHome() {
      this.$storex.ui.openHome()
    },
    openQuickChat() {
      this.$service.chat.newQuickChat()
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
    }
  }
}
</script>