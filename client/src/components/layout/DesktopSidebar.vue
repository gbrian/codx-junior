<script setup>
import RecentsSection from './RecentsSection.vue'
import AppsSection from './AppsSection.vue'
import WorkspacesSection from './WorkspacesSection.vue'
import UserInfo from '../UserInfo.vue'
import Notifications from '../Notifications.vue'
import ViewModeToggle from './ViewModeToggle.vue'
import MainMenu from '../main-menu/MainMenu.vue'
</script>

<template>
  <!-- Mobile Overlay & Sidebar Container -->
  <div v-if="isMobile" class="pointer-events-none">
    <!-- Mobile Overlay -->
    <div
      v-if="!isCollapsed"
      class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm animate-fade-in pointer-events-auto"
      @click="handleClose"
    ></div>

    <!-- Mobile Sidebar -->
    <aside
      ref="sidebarEl"
      class="fixed left-0 top-0 bottom-0 z-50 w-64 flex flex-col h-full shrink-0 bg-[#1a1a1a] border-r border-white/5 pointer-events-auto"
      :style="{
        transform: isCollapsed ? 'translateX(-100%)' : 'translateX(0)',
        transition: 'transform 0.3s ease-out'
      }"
    >
      <!-- Header Section -->
      <div class="px-3 py-4 shrink-0 border-b border-white/5">
        <div class="flex items-center justify-between gap-2">
          <button
            class="click w-6 h-6 rounded border border-white/20 flex items-center justify-center hover:bg-white/5 transition-colors"
            @click="handleClose"
            title="Close sidebar"
          >
            <i class="fa-solid fa-angle-left text-white/40 text-xs"></i>
          </button>
          <span class="text-lg font-semibold">
            <span class="text-codx-primary">codx-</span>
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

        <!-- Recents Section -->
        <RecentsSection
          :chats="recentChats"
          :is-collapsed="false"
          :is-loading="isLoadingChats"
          :active-chat-id="activeChattId"
          :is-mobile="true"
          @select-chat="handleSelectChat"
          @scroll-end="loadMoreChats"
        />
      </div>

      <!-- Footer -->
      <div class="shrink-0 border-t border-white/5 px-2 py-3">
        <div class="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors cursor-pointer">
          <div class="grow flex items-center gap-3 flex-1">
            <MainMenu
              :is-project-admin="isProjectAdmin"
              @close="handleClose"
            >
              <UserInfo>
                <template #trigger="{ togglePanel }">
                  <button
                    class="btn btn-xs btn-ghost p-1 w-6 h-6 min-h-0"
                    @click="togglePanel"
                    :class="dailyLimitStatus === 'exceeded' ? 'text-error' : dailyLimitStatus === 'warning' ? 'text-warning' : 'text-info'"
                  >
                    <div class="avatar tooltip" :data-tip="$user.username">
                      <div class="w-8">
                        <img :src="$user.avatar">
                      </div>
                    </div>
                  </button>
                </template>
              </UserInfo>
              <div class="flex justify-between">
                <div class="flex-1 min-w-0">
                  <div class="text-sm text-white truncate">{{ userName }}</div>
                  <div class="text-xs text-white/40">{{ userSubtitle }}</div>
                </div>
                <button class="p-1 text-white/30 hover:text-white/80 transition-colors">
                  <i class="fas fa-chevron-down text-xs"></i>
                </button>
              </div>
            </MainMenu>
          </div>
        </div>
      </div>
    </aside>
  </div>

  <!-- Desktop Sidebar -->
  <aside
    v-else
    ref="sidebarEl"
    class="flex flex-col h-full shrink-0 bg-[#1a1a1a] border-r border-white/5 transition-all duration-200"
    :class="[isCollapsed ? 'w-20' : 'w-64']"
  >
    <!-- Header Section -->
    <div class="px-3 py-4 shrink-0 border-b border-white/5">
      <div class="flex items-center justify-between gap-2">
        <div v-if="!isCollapsed" class="flex items-center shrink-0 gap-2 flex-1">
          <button
            class="click w-6 h-6 rounded border border-white/20 flex items-center justify-center hover:bg-white/5 transition-colors"
            @click="toggleCollapse"
            title="Toggle sidebar"
          >
            <i class="fa-solid fa-angle-left text-white/40 text-xs"></i>
          </button>
          <span class="text-lg font-semibold">
            <span class="text-codx-primary">codx-</span>
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

      <!-- Recents Section -->
      <RecentsSection
        :chats="recentChats"
        :is-collapsed="isCollapsed"
        :is-loading="isLoadingChats"
        :active-chat-id="activeChattId"
        :is-mobile="false"
        @select-chat="handleSelectChat"
        @scroll-end="loadMoreChats"
      />
    </div>

    <!-- Footer -->
    <div class="shrink-0 border-t border-white/5 px-2 py-3">
      <div class="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors cursor-pointer">
        <div class="grow flex items-center gap-3 flex-1">
          <MainMenu
            :is-project-admin="isProjectAdmin"
            @close="handleClose"
          >
            <UserInfo>
              <template #trigger="{ togglePanel }">
                <button
                  class="btn btn-xs btn-ghost p-1 w-6 h-6 min-h-0"
                  @click="togglePanel"
                  :class="dailyLimitStatus === 'exceeded' ? 'text-error' : dailyLimitStatus === 'warning' ? 'text-warning' : 'text-info'"
                >
                  <div class="avatar tooltip" :data-tip="$user.username">
                    <div class="w-8">
                      <img :src="$user.avatar">
                    </div>
                  </div>
                </button>
              </template>
            </UserInfo>
            <div v-if="!isCollapsed" class="flex justify-between">
              <div class="flex-1 min-w-0">
                <div class="text-sm text-white truncate">{{ userName }}</div>
                <div class="text-xs text-white/40">{{ userSubtitle }}</div>
              </div>
              <button class="p-1 text-white/30 hover:text-white/80 transition-colors">
                <i class="fas fa-chevron-down text-xs"></i>
              </button>
            </div>
          </MainMenu>
        </div>
        <!-- View Mode Toggle -->
        <ViewModeToggle v-if="!isCollapsed" />
      </div>
    </div>
  </aside>
</template>

<script>
export default {
  props: {
    userName: { type: String, default: 'User' },
    userSubtitle: { type: String, default: 'Pro' },
    isMobile: { type: Boolean, default: false },
    isMobileExpanded: { type: Boolean, default: false }
  },
  emits: ['settings', 'close'],
  data() {
    return {
      isCollapsed: true,
      userCollapsed: false,
      resizeObserver: null,
      recentChats: [],
      isLoadingChats: false,
      currentPage: 1,
      initialPageSize: 20,
      subsequentPageSize: 10,
      hasMoreChats: true,
      activeChattId: null,
      isInitialLoad: true,
      dailyLimitStatus: 'normal',
      selectedWorkspaceApp: null,
      moreExpanded: false
    }
  },
  computed: {
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
    }
  },
  watch: {
    isMobileExpanded(val) {
      if (this.isMobile) {
        this.isCollapsed = !val
      }
    }
  },
  mounted() {
    if (!this.isMobile) {
      this.isCollapsed = false
      this.$nextTick(() => this.setupResizeObserver())
    } else {
      this.isCollapsed = !this.isMobileExpanded
    }
    this.loadRecentChats()
  },
  beforeUnmount() {
    this.resizeObserver?.disconnect()
  },
  methods: {
    setupResizeObserver() {
      const el = this.$refs.sidebarEl
      if (!el) return
      const parent = el.parentElement
      if (!parent) return
      this.resizeObserver = new ResizeObserver(([entry]) => {
        const width = entry.contentRect.width
        if (!this.userCollapsed) {
          this.isCollapsed = width < 600
        }
      })
      this.resizeObserver.observe(parent)
    },
    toggleCollapse() {
      this.userCollapsed = !this.userCollapsed
      this.isCollapsed = this.userCollapsed
    },
    handleClose() {
      if (this.isMobile) {
        this.isCollapsed = true
      }
      this.$emit('close')
    },
    async loadRecentChats(append = false) {
      try {
        this.isLoadingChats = true
        const currentUserId = this.currentUser?.id
        const pageSize = this.isInitialLoad ? this.initialPageSize : this.subsequentPageSize

        const response = await this.$project.$api.chats.getRecentChats({
          filters: { user_id: currentUserId },
          page: this.currentPage,
          pageSize: pageSize
        })

        if (response.error) {
          console.error('Error loading recent chats:', response.error)
          this.isLoadingChats = false
          return
        }

        if (append) {
          this.recentChats.push(...response.chats)
        } else {
          this.recentChats = response.chats
        }

        this.hasMoreChats = response.has_next
        this.activeChattId = this.$storex?.chats?.activeChat?.id || null
        this.isLoadingChats = false
        this.isInitialLoad = false
      } catch (error) {
        console.error('Error loading recent chats:', error)
        this.isLoadingChats = false
      }
    },
    loadMoreChats() {
      if (this.hasMoreChats && !this.isLoadingChats) {
        this.currentPage += 1
        this.loadRecentChats(true)
      }
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