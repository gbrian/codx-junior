<script setup>
import TeamChannelsSidebar from '@/components/teams/TeamChannelsSidebar.vue'
import RecentChatsQuickAccess from '@/components/chats/RecentChatsQuickAccess.vue'
import UserInfo from '@/components/UserInfo.vue'
</script>

<template>
  <div v-if="activeTeam" class="flex flex-col h-full shrink-0 transition-all duration-300" :class="isCollapsed ? 'w-20' : 'w-64'">
    <!-- Header with toggle button -->
    <div class="flex items-center justify-between px-3 py-2 border-b border-base-content/10 bg-base-300/50 shrink-0">
      <div v-if="!isCollapsed" class="text-sm font-bold text-base-content">
        {{ activeTeam.name }}
      </div>
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
      <!-- Channel list - visible only when expanded -->
      <div v-if="!isCollapsed" class="w-full">
        <TeamChannelsSidebar
          :active-team="activeTeam"
          @open-team-settings="$emit('open-team-settings')"
          @open-create-channel="$emit('open-create-channel', $event)"
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

      <!-- Recent Chats: Full or Icon Mode -->
      <div :class="isCollapsed ? 'p-2 w-full flex flex-col items-center gap-2' : 'px-2 pb-4 w-full'">
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
  data() {
    return {
      isCollapsed: false
    }
  },
  computed: {
    userInitial() {
      return this.$users.user?.username?.[0]?.toUpperCase() || '?'
    }
  },
  methods: {
    toggleCollapse() {
      this.isCollapsed = !this.isCollapsed
    }
  }
}
</script>