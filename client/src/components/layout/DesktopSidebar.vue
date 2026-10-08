<script setup>
import AppsSection from './AppsSection.vue'
import WorkspacesSection from './WorkspacesSection.vue'
import Notifications from '../Notifications.vue'
import WindowsMenu from '../main-menu/WindowsMenu.vue'
import RecentsSection from './RecentsSection.vue'
</script>

<template>
  <!-- Mobile Overlay & Sidebar Container -->
  <div v-if="isMobile" class="pointer-events-none">
    <!-- Mobile Overlay -->
    <div
      v-if="!isCollapsed"
      class="fixed inset-0 z-40 backdrop-blur-sm animate-fade-in pointer-events-auto"
      @click="handleClose"
    ></div>

    <!-- Mobile Sidebar -->
    <aside
      ref="sidebarEl"
      class="fixed left-0 top-0 bottom-0 z-50 w-64 flex flex-col h-full shrink-0 border-r border-base-content/5 pointer-events-auto"
      :style="{
        transform: isCollapsed ? 'translateX(-100%)' : 'translateX(0)',
        transition: 'transform 0.3s ease-out'
      }"
    >
      <!-- Header Section -->
      <div class="px-3 py-4 shrink-0 border-b border-base-content/5">
        <div class="flex items-center justify-between gap-2">
          <button
            class="click w-6 h-6 rounded border border-base-content/20 flex items-center justify-center hover:bg-white/5 transition-colors"
            @click="handleClose"
            title="Close sidebar"
          >
            <i class="fa-solid fa-angle-left text-base-content/40 text-xs"></i>
          </button>
          <span class="text-lg font-semibold">
            <span class="text-codx-secondary">codx-</span>
            <span class="text-codx-secondary">junior</span>
          </span>
        </div>
      </div>

      <!-- Scrollable Content Area -->
      <div class="flex-1 overflow-y-auto flex flex-col">
        <!-- Apps Section -->
        <AppsSection
          :is-collapsed="false"
          :more-expanded="moreExpanded"
          @update:moreExpanded="moreExpanded = $event"
          @close="handleClose"
          @toggle-collapse="toggleCollapse"
        />
        
        <!-- Workspaces Section -->
        <WorkspacesSection
          :workspace-apps="workspaceApps"
          :is-collapsed="false"
          :current-workspace-id="currentWorkspaceId"
          @close="handleClose"
        />

      </div>

      <!-- Footer -->
      <div class="shrink-0 border-t border-base-content/5 px-2 py-3">
        <WindowsMenu @close="handleClose">
          <div class="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors cursor-pointer w-full">
            <div class="avatar tooltip shrink-0" :data-tip="$user.username">
              <div class="w-8 rounded-full overflow-hidden">
                <img :src="$user.avatar">
              </div>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-sm truncate">{{ userName }}</div>
              <div class="text-xs text-base-content/40 truncate">{{ userSubtitle }}</div>
            </div>
            <i class="fas fa-chevron-down text-xs text-base-content/30 shrink-0"></i>
          </div>
        </WindowsMenu>
      </div>
    </aside>
  </div>

  <!-- Desktop Sidebar -->
  <aside
    v-else
    ref="sidebarEl"
    class="flex flex-col h-full shrink-0 border-r border-base-content/5 transition-all duration-200"
    :class="[isCollapsed ? 'w-20' : 'w-64']"
  >
    <!-- Header Section -->
    <div class="px-3 py-4 shrink-0 border-b border-base-content/5">
      <div class="flex items-center justify-between gap-2">
        <div v-if="!isCollapsed" class="flex items-center shrink-0 gap-2 flex-1">
          <button
            class="click w-6 h-6 rounded border border-base-content/20 flex items-center justify-center hover:bg-white/5 transition-colors"
            @click="toggleCollapse"
            title="Toggle sidebar"
          >
            <i class="fa-solid fa-angle-left text-base-content/40 text-xs"></i>
          </button>
          <span class="text-lg font-semibold">
            <span class="text-codx-secondary">codx-</span>
            <span class="text-codx-secondary">junior</span>
          </span>
        </div>
        <div v-else class="flex justify-center w-full">
          <button
            class="click w-6 h-6 flex items-center justify-center hover:bg-white/5 transition-colors"
            title="Expand sidebar"
            @click="toggleCollapse()"
          >
            <img class="w-full" src="/only_icon.png" />
          </button>
        </div>

        <div v-if="!isCollapsed" class="flex items-center gap-2">
          <Notifications />
        </div>        
      </div>
    </div>

    <!-- Scrollable Content Area -->
    <div class="flex-1 overflow-y-auto flex flex-col">
      <!-- Apps Section -->
      <AppsSection
        :is-collapsed="isCollapsed"
        :more-expanded="moreExpanded"
        @update:moreExpanded="moreExpanded = $event"
        @close="handleClose"
        @toggle-collapse="toggleCollapse"
      />
      
      <!-- Workspaces Section -->
      <WorkspacesSection
        :workspace-apps="workspaceApps"
        :is-collapsed="isCollapsed"
        :current-workspace-id="currentWorkspaceId"
        @close="handleClose"
      />

      <RecentsSection
        @select-chat="handleSelectChat"
      />

    </div>

    <!-- Footer -->
    <div class="shrink-0 border-t border-base-content/5 px-2 py-3">
      <!-- Expanded Footer - opens the unified Windows-like menu -->
      <WindowsMenu v-if="!isCollapsed" @close="handleClose">
        <div class="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors cursor-pointer w-full">
          <div class="avatar tooltip shrink-0" :data-tip="$user.username">
            <div class="w-8 rounded-full overflow-hidden">
              <img :src="$user.avatar">
            </div>
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-sm truncate">{{ userName }}</div>
            <div class="text-xs"
              :class="connected ? 'text-success/60': 'text-error'"
            >{{ connected ? 'online': 'offline' }}</div>
          </div>
          <i class="fas fa-chevron-down text-xs text-base-content/40 shrink-0"></i>
        </div>
      </WindowsMenu>

      <!-- Collapsed Footer - Icon Only -->
      <div v-else class="flex items-center justify-center py-2">
        <WindowsMenu @close="handleClose">
          <div class="p-1 rounded-full hover:bg-white/5 transition-colors cursor-pointer">
            <div class="avatar tooltip tooltip-right" :data-tip="$user.username">
              <div class="w-8 rounded-full overflow-hidden">
                <img :src="$user.avatar">
              </div>
            </div>
          </div>
        </WindowsMenu>
      </div>
    </div>
  </aside>
</template>

<script>
export default {
  props: {
    isMobile: { type: Boolean, default: false },
    isMobileExpanded: { type: Boolean, default: false }
  },
  emits: ['settings', 'close'],
  data() {
    return {
      dailyLimitStatus: 'normal',
      moreExpanded: false
    }
  },
  computed: {
    isCollapsed() {
      return this.$storex.ui.sidebarCollapsed
    },
    workspaceApps() {
      return this.$projects.projectApps || []
    },
    currentUser() {
      return this.$storex?.users?.user || this.$user
    },
    hasWorkspaceApps() {
      return this.workspaceApps && this.workspaceApps.length > 0
    },
    isProjectAdmin() {
      return this.$users?.isProjectAdmin || false
    },
    currentWorkspaceId() {
      return this.$storex.$router.$navigation.getWorkspaceId()
    },
    isDesktopMode() {
      return this.$storex.$router.$navigation.isDesktopMode
    },
    userName() { 
      return this.$users.user?.username 
    },
    userSubtitle() {
      const email = this.$users.user?.email
      return email && email.length > 20 ? email.substring(0, 20) + '...' : email
    },
    connected() {
      return this.$session.connected
    }
  },
  watch: {
    isMobileExpanded(val) {
      if (this.isMobile) {
        this.$storex.ui.setSidebarCollapsed(!val)
      }
    }
  },
  methods: {
    toggleCollapse() {
      this.$storex.ui.setSidebarCollapsed(!this.isCollapsed)
    },
    handleClose() {
      if (this.isMobile) {
        this.$storex.ui.setSidebarCollapsed(true)
      }
      this.$emit('close')
    },
    handleSelectChat(chat) {
      this.$chats.setActiveChat(chat)
      if (this.isMobile) {
        this.handleClose()
      }
    }
  }
}
</script>

<style scoped>
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.animate-fade-in {
  animation: fadeIn 0.2s ease-out forwards;
}
</style>